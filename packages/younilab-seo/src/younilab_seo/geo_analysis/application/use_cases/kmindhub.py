from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    KMindHubWorkspaceMappingCommand,
    KMindHubWorkspaceMappingRecord,
    KMindHubWorkspaceProvisionCommand,
)
from younilab_seo.geo_analysis.application.interfaces import (
    KMindHubWorkspaceClient,
)
from younilab_seo.geo_analysis.application.interfaces.kmindhub_mapping import (
    KMindHubWorkspaceMappingPersistence,
)


class KMindHubWorkspaceMappingNotFound(LookupError):
    """租戶尚未設定可用 KMindHub workspace mapping。"""


class KMindHubWorkspaceMappingAlreadyExists(RuntimeError):
    """租戶已經綁定 KMindHub workspace，provision 不應再建立遠端 workspace。"""


@dataclass(frozen=True)
class ManageKMindHubWorkspaceMapping:
    """管理 tenant 對 KMindHub workspace 的手動 mapping 與 runtime 解析。"""

    repository: KMindHubWorkspaceMappingPersistence
    client: KMindHubWorkspaceClient

    async def get_mapping(
        self,
        tenant_id: UUID,
    ) -> KMindHubWorkspaceMappingRecord | None:
        return await self.repository.get_kmindhub_workspace_mapping(tenant_id)

    async def bind_workspace(
        self,
        tenant_id: UUID,
        command: KMindHubWorkspaceMappingCommand,
    ) -> KMindHubWorkspaceMappingRecord:
        normalized = _validated_mapping_command(command, provisioning_mode="manual")
        return await self.repository.upsert_kmindhub_workspace_mapping(
            tenant_id,
            normalized,
        )

    async def provision_workspace(
        self,
        tenant_id: UUID,
        command: KMindHubWorkspaceProvisionCommand,
    ) -> KMindHubWorkspaceMappingRecord:
        display_name = _normalize_required_text(command.display_name, "displayName")
        current = await self.repository.get_kmindhub_workspace_mapping(tenant_id)
        if current is not None:
            raise KMindHubWorkspaceMappingAlreadyExists(
                "KMindHub workspace mapping already exists"
            )
        workspace_id = await self.client.create_workspace(display_name)
        return await self.repository.upsert_kmindhub_workspace_mapping(
            tenant_id,
            KMindHubWorkspaceMappingCommand(
                workspace_id=workspace_id,
                display_name=display_name,
                provisioning_mode="manual_provisioned",
                status="active",
            ),
        )

    async def resolve_workspace_id(self, tenant_id: UUID) -> UUID:
        mapping = await self.repository.get_kmindhub_workspace_mapping(tenant_id)
        if mapping is None or mapping.status != "active":
            raise KMindHubWorkspaceMappingNotFound(
                "KMindHub workspace mapping is not configured"
            )
        return mapping.workspace_id

    async def workspace_headers(self, tenant_id: UUID) -> dict[str, str]:
        workspace_id = await self.resolve_workspace_id(tenant_id)
        return self.client.workspace_headers(workspace_id)


def _validated_mapping_command(
    command: KMindHubWorkspaceMappingCommand,
    *,
    provisioning_mode: str,
) -> KMindHubWorkspaceMappingCommand:
    display_name = _normalize_required_text(command.display_name, "displayName")
    status = _normalize_required_text(command.status, "status")
    if status not in {"active", "disabled"}:
        raise ValueError("status must be active or disabled")
    if provisioning_mode not in {"manual", "manual_provisioned"}:
        raise ValueError("provisioningMode must be manual or manual_provisioned")
    return KMindHubWorkspaceMappingCommand(
        workspace_id=command.workspace_id,
        display_name=display_name,
        provisioning_mode=provisioning_mode,
        status=status,
    )


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized
