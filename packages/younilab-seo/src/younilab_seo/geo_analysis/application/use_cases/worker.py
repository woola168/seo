from dataclasses import dataclass

from younilab_seo.geo_analysis.application.contracts import (
    ExternalRunCallback,
    QueryRunJobMessage,
    SaveTrackingRunResultCommand,
    TrackingRunResponse,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    GeoQueryRunJobRepository,
    TrackingRunClient,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob, QueryRunJobStatusError


class QueryRunJobMessageRejected(ValueError):
    """已消費 message 無法套用且不應重試時使用的錯誤。"""


@dataclass(frozen=True)
class ProcessQueryRunJobMessage:
    """將已發布的 query job 交給 geo-tracking 執行並保存 runner 狀態。"""

    repository: GeoQueryRunJobRepository
    tracking_client: TrackingRunClient
    clock: Clock
    supported_provider: str

    async def execute(self, message: QueryRunJobMessage) -> GeoQueryRunJob:
        """處理單一 provider queue message，並以 job 所屬 tenant 作為防線。"""

        worker_run_id = f"worker-{message.job_id}"
        job_tenant_id = await self.repository.get_job_tenant_id(message.job_id)
        if job_tenant_id is None:
            raise QueryRunJobMessageRejected(f"job {message.job_id} not found")
        if job_tenant_id != message.tenant_id:
            return await self._save_or_reject(
                SaveTrackingRunResultCommand(
                    message=message,
                    status="failed",
                    error_code="tenant_mismatch",
                    error_message="queue message tenant does not match job project tenant",
                    request_payload={
                        "reason": "tenant_mismatch",
                        "queueMessage": message.model_dump(
                            mode="json",
                            by_alias=True,
                        ),
                    },
                ),
            )
        if message.platform != self.supported_provider:
            return await self._save_or_reject(
                SaveTrackingRunResultCommand(
                    message=message,
                    status="failed",
                    error_code="unsupported_provider",
                    error_message=(
                        f"worker supports {self.supported_provider}, "
                        f"got {message.platform}"
                    ),
                    request_payload={
                        "reason": "unsupported_provider",
                        "queueMessage": message.model_dump(
                            mode="json",
                            by_alias=True,
                        ),
                    },
                ),
            )
        request_payload = self.tracking_client.build_request_payload(message)
        try:
            await self.repository.apply_external_callback(
                callback=ExternalRunCallback(
                    job_id=message.job_id,
                    external_run_id=worker_run_id,
                    status="running",
                ),
                occurred_at=self.clock.now(),
            )
        except QueryRunJobStatusError as exc:
            raise QueryRunJobMessageRejected(
                f"job {message.job_id} rejected message: {exc}"
            ) from exc
        try:
            response = await self.tracking_client.run(message)
        except Exception as exc:
            return await self._save_or_reject(
                SaveTrackingRunResultCommand(
                    message=message,
                    status="failed",
                    error_code="tracking_request_failed",
                    error_message=str(exc),
                    request_payload=request_payload,
                ),
            )
        return await self._save_response(message, response, request_payload)

    async def _save_response(
        self,
        message: QueryRunJobMessage,
        response: TrackingRunResponse,
        request_payload: dict,
    ) -> GeoQueryRunJob:
        """將 tracking response 轉成 job 終態與 raw result 保存命令。"""

        failed = next(
            (result for result in response.results if result.status != "completed"),
            None,
        )
        if not response.results:
            status = "failed"
            error_code = "tracking_result_missing"
            error_message = "tracking response did not include run results"
        elif failed is not None:
            status = "failed"
            error_code = failed.error or "tracking_run_failed"
            error_message = failed.error or "tracking run failed"
        else:
            status = "succeeded"
            error_code = None
            error_message = None
        return await self._save_or_reject(
            SaveTrackingRunResultCommand(
                message=message,
                response=response,
                status=status,
                error_code=error_code,
                error_message=error_message,
                request_payload=request_payload,
            ),
        )

    async def _save_or_reject(
        self,
        command: SaveTrackingRunResultCommand,
    ) -> GeoQueryRunJob:
        """保存 worker 結果，若 job 狀態已不接受回寫則轉為 poison message rejection。"""

        try:
            return await self.repository.save_tracking_run_result(
                command=command,
                occurred_at=self.clock.now(),
            )
        except QueryRunJobStatusError as exc:
            raise QueryRunJobMessageRejected(
                f"job {command.message.job_id} rejected message: {exc}"
            ) from exc
