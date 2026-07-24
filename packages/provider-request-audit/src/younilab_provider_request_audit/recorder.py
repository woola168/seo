from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Literal, Protocol, TypeVar
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ProviderRequestContext:
    platform_code: str
    provider_code: str
    provider_operation: str
    use_case: str
    source_service: str
    model: str | None = None
    provider_region: str | None = None
    uses_grounding: bool = False
    tenant_id: UUID | None = None
    project_id: UUID | None = None
    job_id: UUID | None = None
    query_id: UUID | None = None
    run_request_id: UUID | None = None


@dataclass(frozen=True)
class ProviderRequestStarted:
    id: UUID
    operation_id: UUID
    request_number: int
    request_kind: str
    context: ProviderRequestContext
    started_at: datetime
    expects_usage: bool = False


@dataclass(frozen=True)
class ProviderRequestUsage:
    """Provider-neutral token usage and additional billable meter quantities."""

    input_token_count: int | None = None
    output_token_count: int | None = None
    total_token_count: int | None = None
    cached_input_token_count: int | None = None
    reasoning_token_count: int | None = None
    tool_input_token_count: int | None = None
    traffic_type: str | None = None
    usage_metadata: dict[str, Any] | None = None
    meter_usage: dict[str, int] | None = None

    def __post_init__(self) -> None:
        counts = (
            self.input_token_count,
            self.output_token_count,
            self.total_token_count,
            self.cached_input_token_count,
            self.reasoning_token_count,
            self.tool_input_token_count,
        )
        if any(count is not None and count < 0 for count in counts):
            raise ValueError("provider request token counts must be non-negative")
        if self.meter_usage is not None and any(
            not isinstance(value, int) or value < 0
            for value in self.meter_usage.values()
        ):
            raise ValueError("provider request meter usage must contain non-negative integers")


@dataclass(frozen=True)
class ProviderRequestFailure:
    http_status: int | None
    error_code: str | None
    error_type: str


class ProviderRequestRecorder(Protocol):
    async def start(self, request: ProviderRequestStarted) -> None: ...

    async def succeed(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        http_status: int | None = None,
        usage: ProviderRequestUsage | None = None,
        usage_capture_status: Literal[
            "recorded", "unavailable", "not_applicable"
        ] = "not_applicable",
    ) -> None: ...

    async def fail(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        failure: ProviderRequestFailure,
    ) -> None: ...

    async def close(self) -> None: ...


class UnconfiguredProviderRequestRecorder:
    async def start(self, request: ProviderRequestStarted) -> None:
        raise RuntimeError("provider request recorder is not configured")

    async def succeed(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        http_status: int | None = None,
        usage: ProviderRequestUsage | None = None,
        usage_capture_status: Literal[
            "recorded", "unavailable", "not_applicable"
        ] = "not_applicable",
    ) -> None:
        raise RuntimeError("provider request recorder is not configured")

    async def fail(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        failure: ProviderRequestFailure,
    ) -> None:
        raise RuntimeError("provider request recorder is not configured")

    async def close(self) -> None:
        return None


class MemoryProviderRequestRecorder:
    def __init__(self) -> None:
        self.requests: dict[UUID, ProviderRequestStarted] = {}
        self.outcomes: dict[UUID, str] = {}
        self.failures: dict[UUID, ProviderRequestFailure] = {}
        self.usages: dict[UUID, ProviderRequestUsage] = {}
        self.usage_capture_statuses: dict[UUID, str] = {}

    async def start(self, request: ProviderRequestStarted) -> None:
        if request.id in self.requests:
            raise RuntimeError(f"provider request {request.id} already exists")
        self.requests[request.id] = request
        self.outcomes[request.id] = "started"
        self.usage_capture_statuses[request.id] = (
            "pending" if request.expects_usage else "not_applicable"
        )

    async def succeed(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        http_status: int | None = None,
        usage: ProviderRequestUsage | None = None,
        usage_capture_status: Literal[
            "recorded", "unavailable", "not_applicable"
        ] = "not_applicable",
    ) -> None:
        self._ensure_started(request_id)
        self.outcomes[request_id] = "succeeded"
        self.usage_capture_statuses[request_id] = usage_capture_status
        if usage is not None:
            self.usages[request_id] = usage

    async def fail(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        failure: ProviderRequestFailure,
    ) -> None:
        self._ensure_started(request_id)
        self.outcomes[request_id] = "failed"
        self.failures[request_id] = failure
        if self.usage_capture_statuses[request_id] == "pending":
            self.usage_capture_statuses[request_id] = "unavailable"

    async def close(self) -> None:
        return None

    def _ensure_started(self, request_id: UUID) -> None:
        if self.outcomes.get(request_id) != "started":
            raise RuntimeError(f"provider request {request_id} was not in started state")


T = TypeVar("T")
FailureClassifier = Callable[[Exception], ProviderRequestFailure]
HttpStatusReader = Callable[[T], int | None]
UsageReader = Callable[[T], ProviderRequestUsage | None]


class ProviderRequestExecutor:
    def __init__(
        self,
        recorder: ProviderRequestRecorder,
        context: ProviderRequestContext,
        *,
        operation_id: UUID | None = None,
    ) -> None:
        self._recorder = recorder
        self._context = context
        self._operation_id = operation_id or uuid4()
        self._request_number = 0

    async def execute(
        self,
        request: Callable[[], Awaitable[T]],
        *,
        request_kind: str,
        classify_failure: FailureClassifier | None = None,
        read_http_status: HttpStatusReader[T] | None = None,
        read_usage: UsageReader[T] | None = None,
    ) -> T:
        self._request_number += 1
        request_id = uuid4()
        started_at = datetime.now(UTC)
        started = ProviderRequestStarted(
            id=request_id,
            operation_id=self._operation_id,
            request_number=self._request_number,
            request_kind=request_kind,
            context=self._context,
            started_at=started_at,
            expects_usage=read_usage is not None,
        )
        await self._recorder.start(started)
        started_clock = monotonic()
        try:
            result = await request()
        except Exception as exc:
            completed_at = datetime.now(UTC)
            await self._recorder.fail(
                request_id,
                completed_at=completed_at,
                duration_ms=_duration_ms(started_clock),
                failure=(classify_failure or classify_provider_failure)(exc),
            )
            raise
        usage: ProviderRequestUsage | None = None
        usage_capture_status: Literal[
            "recorded", "unavailable", "not_applicable"
        ] = "not_applicable"
        if read_usage is not None:
            usage_capture_status = "unavailable"
            try:
                usage = read_usage(result)
                if usage is not None and not isinstance(usage, ProviderRequestUsage):
                    raise TypeError("usage reader returned an unsupported value")
            except Exception:
                usage = None
            if usage is not None:
                usage_capture_status = "recorded"
        await self._recorder.succeed(
            request_id,
            completed_at=datetime.now(UTC),
            duration_ms=_duration_ms(started_clock),
            http_status=read_http_status(result) if read_http_status else None,
            usage=usage,
            usage_capture_status=usage_capture_status,
        )
        return result


def classify_provider_failure(error: Exception) -> ProviderRequestFailure:
    raw_code = getattr(error, "code", None)
    raw_status = getattr(error, "status", None) or getattr(error, "status_code", None)
    http_status = (
        raw_status
        if isinstance(raw_status, int)
        else raw_code if isinstance(raw_code, int) else None
    )
    error_code = raw_code if isinstance(raw_code, str) else None
    return ProviderRequestFailure(
        http_status=http_status,
        error_code=error_code,
        error_type=error.__class__.__name__,
    )


def _duration_ms(started_clock: float) -> int:
    return max(0, round((monotonic() - started_clock) * 1000))
