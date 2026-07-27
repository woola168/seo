import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    QueryRunJobMessage,
    SaveTrackingRunResultCommand,
    TrackingRunResponse,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    TrackingRunClient,
)
from younilab_seo.geo_analysis.application.interfaces.run_lifecycle import (
    RunExecutionPersistence,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob, QueryRunJobStatusError

logger = logging.getLogger(__name__)


class RunResultPipelineStep(Protocol):
    """Post-tracking step that enriches a saved run result for reporting."""

    async def execute(self, tenant_id: UUID, run_result_id: UUID) -> object: ...


class QueryRunJobMessageRejected(ValueError):
    """已消費 message 無法套用且不應重試時使用的錯誤。"""


class QueryRunJobResultPersistenceFailed(RuntimeError):
    """Provider 執行後的結果無法保存，consumer 必須停止後續處理。"""


@dataclass(frozen=True)
class ProcessQueryRunJobMessage:
    """將已發布的 query job 交給 geo-tracking 執行並保存 runner 狀態。"""

    repository: RunExecutionPersistence
    tracking_client: TrackingRunClient
    clock: Clock
    supported_provider: str
    analyze_run_result: RunResultPipelineStep | None = None
    normalize_run_result_citations: RunResultPipelineStep | None = None

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
                    error_message=(
                        "queue message tenant does not match job project tenant"
                    ),
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
        claimed = await self.repository.claim_job_for_execution(
            job_id=message.job_id,
            tenant_id=message.tenant_id,
            external_run_id=worker_run_id,
            occurred_at=self.clock.now(),
        )
        if not claimed:
            raise QueryRunJobMessageRejected(
                f"job {message.job_id} was already claimed or is not dispatchable"
            )
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
                provider_started=True,
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
        job = await self._save_or_reject(
            SaveTrackingRunResultCommand(
                message=message,
                response=response,
                status=status,
                error_code=error_code,
                error_message=error_message,
                request_payload=request_payload,
            ),
            provider_started=True,
        )
        if (
            status == "succeeded"
            and self.analyze_run_result is not None
            and self.normalize_run_result_citations is not None
        ):
            results = await self.repository.list_job_run_results(
                message.tenant_id,
                message.job_id,
            )
            for result in results:
                try:
                    await self.analyze_run_result.execute(
                        message.tenant_id,
                        result.id,
                    )
                except Exception:
                    logger.exception(
                        "GEO semantic analysis failed after tracking success",
                        extra={
                            "tenant_id": str(message.tenant_id),
                            "job_id": str(message.job_id),
                            "run_result_id": str(result.id),
                        },
                    )
                    continue
                try:
                    await self.normalize_run_result_citations.execute(
                        message.tenant_id,
                        result.id,
                    )
                except Exception:
                    logger.exception(
                        "GEO citation normalization failed after tracking success",
                        extra={
                            "tenant_id": str(message.tenant_id),
                            "job_id": str(message.job_id),
                            "run_result_id": str(result.id),
                        },
                    )
                    continue
        return job

    async def _save_or_reject(
        self,
        command: SaveTrackingRunResultCommand,
        *,
        provider_started: bool = False,
    ) -> GeoQueryRunJob:
        """保存 worker 結果，並依 provider 是否已執行決定失敗語意。"""

        try:
            return await self.repository.save_tracking_run_result(
                command=command,
                occurred_at=self.clock.now(),
            )
        except QueryRunJobStatusError as exc:
            if provider_started:
                self._log_result_persistence_failure(command, exc)
                raise QueryRunJobResultPersistenceFailed(
                    f"job {command.message.job_id} result could not be persisted"
                ) from exc
            raise QueryRunJobMessageRejected(
                f"job {command.message.job_id} rejected message: {exc}"
            ) from exc
        except Exception as exc:
            if not provider_started:
                raise
            self._log_result_persistence_failure(command, exc)
            raise QueryRunJobResultPersistenceFailed(
                f"job {command.message.job_id} stopped after provider execution: "
                f"tracking result persistence failed: {exc.__class__.__name__}"
            ) from exc

    @staticmethod
    def _log_result_persistence_failure(
        command: SaveTrackingRunResultCommand,
        error: Exception,
    ) -> None:
        logger.exception(
            (
                "GEO tracking result persistence failed after provider execution: "
                "jobId=%s tenantId=%s provider=%s status=%s errorCode=%s "
                "exceptionType=%s"
            ),
            command.message.job_id,
            command.message.tenant_id,
            command.message.platform,
            command.status,
            command.error_code,
            error.__class__.__name__,
            extra={
                "job_id": str(command.message.job_id),
                "tenant_id": str(command.message.tenant_id),
                "provider": command.message.platform,
                "status": command.status,
                "error_code": command.error_code,
                "exception_type": error.__class__.__name__,
            },
        )
