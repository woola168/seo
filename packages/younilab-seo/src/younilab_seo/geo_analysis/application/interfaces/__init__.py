from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    AnalyzeGeoRunResultCommand,
    EvidenceTextRepairCommand,
    EvidenceTextRepairResult,
    GeoRunResultAnalysis,
    KMindHubExtractionCommitResult,
    KMindHubExtractionPreviewResult,
    KMindHubExtractionTaskDefinition,
    PublishResult,
    QueryGenerationCommand,
    QueryResearchCommand,
    QueryRunJobMessage,
    TrackingRunResponse,
)


class Clock(Protocol):
    """use case 使用的時間來源，讓測試可以固定時間。"""

    def now(self) -> datetime:
        raise NotImplementedError


class IdGenerator(Protocol):
    """application boundary 建立 orchestration record id 的來源。"""

    def new_id(self) -> UUID:
        raise NotImplementedError


class MessagePublisher(Protocol):
    """將 GEO query run job 發布到 message broker 的 port。"""

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        raise NotImplementedError


class TrackingRunClient(Protocol):
    """透過已設定的 runner service 執行已發布的 GEO query。"""

    def build_request_payload(self, message: QueryRunJobMessage) -> dict:
        raise NotImplementedError

    async def run(self, message: QueryRunJobMessage) -> TrackingRunResponse:
        raise NotImplementedError


class CitationUrlResolver(Protocol):
    """Resolves provider citation redirect URLs to their canonical destination."""

    async def resolve(self, url: str) -> str | None:
        raise NotImplementedError


class QueryPlanningClient(Protocol):
    """Query Research / Generation provider 的 application port。"""

    async def research(self, command: QueryResearchCommand) -> dict:
        raise NotImplementedError

    async def generate(self, command: QueryGenerationCommand) -> dict:
        raise NotImplementedError


class GeoRunResultAnalyzer(Protocol):
    """Semantic analysis runtime 的替換接縫。"""

    async def analyze(
        self,
        command: AnalyzeGeoRunResultCommand,
    ) -> GeoRunResultAnalysis:
        raise NotImplementedError


class EvidenceTextRepairer(Protocol):
    """將 invalid evidence 對回 raw response 中的原文片段。"""

    async def repair(
        self,
        command: EvidenceTextRepairCommand,
    ) -> EvidenceTextRepairResult:
        raise NotImplementedError


class EvidenceTextRepairUnavailable(RuntimeError):
    """SEO evidence repair adapter 無法完成 focused repair。"""

    pass


class KMindHubWorkspaceClient(Protocol):
    """建立 KMindHub workspace 並提供 runtime workspace header 的 port。"""

    async def create_workspace(self, display_name: str) -> UUID:
        raise NotImplementedError

    def workspace_headers(self, workspace_id: UUID) -> dict[str, str]:
        raise NotImplementedError

    async def create_extraction_task(
        self,
        *,
        workspace_id: UUID,
        definition: KMindHubExtractionTaskDefinition,
    ) -> UUID:
        raise NotImplementedError

    async def preview_text_extraction(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        text: str,
    ) -> KMindHubExtractionPreviewResult:
        raise NotImplementedError

    async def commit_extraction_items(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        items: list[dict],
    ) -> KMindHubExtractionCommitResult:
        raise NotImplementedError


class KMindHubWorkspaceResolver(Protocol):
    """用 tenant 解析後續 KMindHub runtime call 必須使用的 active workspace。"""

    async def resolve_workspace_id(self, tenant_id: UUID) -> UUID:
        raise NotImplementedError

    async def workspace_headers(self, tenant_id: UUID) -> dict[str, str]:
        raise NotImplementedError


class KMindHubWorkspaceProvisionUnavailable(RuntimeError):
    """KMindHub workspace provision API 暫時無法使用。"""

    pass


class KMindHubExtractionUnavailable(RuntimeError):
    """KMindHub extraction API 無法完成 task、preview 或 commit 呼叫。"""

    pass


class KMindHubExtractionValidationError(ValueError):
    """KMindHub preview 結果不符合 GEO 報表資料規則。"""

    def __init__(
        self,
        message: str,
        *,
        request_payload: dict | None = None,
        response_payload: dict | None = None,
        validation_failures: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.request_payload = request_payload
        self.response_payload = response_payload
        self.validation_failures = list(validation_failures or [])


class AuthenticationRequired(PermissionError):
    """The caller must provide a valid access token before GEO authorization."""

    pass


class ResourceCatalogVerificationDenied(PermissionError):
    """Resource Catalog 拒絕目前 token 驗證 reference ownership。"""

    pass


class ResourceCatalogVerificationUnavailable(RuntimeError):
    """Resource Catalog 無法完成 reference ownership 驗證。"""

    pass


@dataclass(frozen=True)
class AuthorizedPrincipal:
    """Access Control 回傳給 GEO application layer 的授權上下文。"""

    tenant_id: UUID
    permissions: frozenset[str]
    has_global_resource_access: bool
    customer_ids: frozenset[UUID]
    task_ids: frozenset[UUID]


@dataclass(frozen=True)
class ResourceTaskReference:
    """Resource Catalog 回傳的 SEO task reference 與其 customer 歸屬。"""

    id: UUID
    customer_id: UUID


class PermissionAuthorizer(Protocol):
    """從 access token 解析 GEO API 所需權限與租戶資料的 port。"""

    async def require(
        self,
        access_token: str,
        permission: str,
    ) -> AuthorizedPrincipal:
        raise NotImplementedError


class ResourceCatalogReferenceVerifier(Protocol):
    """驗證 GEO project 綁定的 customer/task 是否屬於目前授權範圍。"""

    async def customer_exists(
        self,
        *,
        access_token: str,
        customer_id: UUID,
    ) -> bool:
        raise NotImplementedError

    async def get_task(
        self,
        *,
        access_token: str,
        task_id: UUID,
    ) -> ResourceTaskReference | None:
        raise NotImplementedError


class ResourceCatalogCustomerReader(Protocol):
    """讀取 Resource Catalog customer 顯示名稱供 GEO read model 使用。"""

    async def list_customer_names(
        self,
        *,
        access_token: str,
        customer_ids: frozenset[UUID],
    ) -> dict[UUID, str]:
        raise NotImplementedError
