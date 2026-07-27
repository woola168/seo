import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from younilab_seo.geo_analysis.application import (
    KMindHubWorkspaceMappingCommand,
    KMindHubWorkspaceMappingPersistence,
    KMindHubWorkspaceMappingRecord,
    KMindHubWorkspaceProvisionCommand,
    ManageKMindHubWorkspaceMapping,
)
from younilab_seo.geo_analysis.application.use_cases import (
    KMindHubWorkspaceMappingAlreadyExists,
    KMindHubWorkspaceMappingNotFound,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")


def test_workspace_mapping_can_be_bound_and_resolved() -> None:
    async def run() -> None:
        repository = FakeRepository()
        workspace_id = uuid4()
        use_case = ManageKMindHubWorkspaceMapping(repository, FakeClient())

        mapping = await use_case.bind_workspace(
            TENANT_ID,
            KMindHubWorkspaceMappingCommand(
                workspace_id=workspace_id,
                display_name="Acme Workspace",
            ),
        )

        assert mapping.workspace_id == workspace_id
        assert mapping.provisioning_mode == "manual"
        assert await use_case.resolve_workspace_id(TENANT_ID) == workspace_id
        assert await use_case.workspace_headers(TENANT_ID) == {
            "X-Workspace-Id": str(workspace_id)
        }

    asyncio.run(run())


def test_disabled_or_missing_mapping_is_not_resolved() -> None:
    async def run() -> None:
        repository = FakeRepository()
        use_case = ManageKMindHubWorkspaceMapping(repository, FakeClient())

        with pytest.raises(KMindHubWorkspaceMappingNotFound):
            await use_case.resolve_workspace_id(TENANT_ID)

        await use_case.bind_workspace(
            TENANT_ID,
            KMindHubWorkspaceMappingCommand(
                workspace_id=uuid4(),
                display_name="Acme Workspace",
                status="disabled",
            ),
        )

        with pytest.raises(KMindHubWorkspaceMappingNotFound):
            await use_case.resolve_workspace_id(TENANT_ID)

    asyncio.run(run())


def test_provision_workspace_creates_remote_workspace_then_saves_mapping() -> None:
    async def run() -> None:
        repository = FakeRepository()
        client = FakeClient(created_workspace_id=uuid4())
        use_case = ManageKMindHubWorkspaceMapping(repository, client)

        mapping = await use_case.provision_workspace(
            TENANT_ID,
            KMindHubWorkspaceProvisionCommand(display_name="Acme Workspace"),
        )

        assert client.created_display_names == ["Acme Workspace"]
        assert mapping.workspace_id == client.created_workspace_id
        assert mapping.provisioning_mode == "manual_provisioned"
        assert mapping.status == "active"

    asyncio.run(run())


def test_provision_workspace_rejects_existing_mapping_without_remote_call() -> None:
    async def run() -> None:
        repository = FakeRepository()
        client = FakeClient(created_workspace_id=uuid4())
        use_case = ManageKMindHubWorkspaceMapping(repository, client)
        existing_workspace_id = uuid4()
        await use_case.bind_workspace(
            TENANT_ID,
            KMindHubWorkspaceMappingCommand(
                workspace_id=existing_workspace_id,
                display_name="Existing Workspace",
                status="disabled",
            ),
        )

        with pytest.raises(KMindHubWorkspaceMappingAlreadyExists):
            await use_case.provision_workspace(
                TENANT_ID,
                KMindHubWorkspaceProvisionCommand(display_name="Acme Workspace"),
            )

        assert client.created_display_names == []
        assert repository.mappings[TENANT_ID].workspace_id == existing_workspace_id

    asyncio.run(run())


@dataclass
class FakeRepository:
    mappings: dict[UUID, KMindHubWorkspaceMappingRecord] = field(default_factory=dict)

    async def get_kmindhub_workspace_mapping(
        self,
        tenant_id: UUID,
    ) -> KMindHubWorkspaceMappingRecord | None:
        return self.mappings.get(tenant_id)

    async def upsert_kmindhub_workspace_mapping(
        self,
        tenant_id: UUID,
        command: KMindHubWorkspaceMappingCommand,
    ) -> KMindHubWorkspaceMappingRecord:
        now = datetime(2026, 7, 2, tzinfo=UTC)
        current = self.mappings.get(tenant_id)
        mapping = KMindHubWorkspaceMappingRecord(
            **command.model_dump(),
            id=current.id if current is not None else uuid4(),
            tenant_id=tenant_id,
            created_at=current.created_at if current is not None else now,
            updated_at=now,
        )
        self.mappings[tenant_id] = mapping
        return mapping


@dataclass
class FakeClient:
    created_workspace_id: UUID = field(default_factory=uuid4)
    created_display_names: list[str] = field(default_factory=list)

    async def create_workspace(self, display_name: str) -> UUID:
        self.created_display_names.append(display_name)
        return self.created_workspace_id

    def workspace_headers(self, workspace_id: UUID) -> dict[str, str]:
        return {"X-Workspace-Id": str(workspace_id)}


def test_workspace_fake_implements_mapping_persistence() -> None:
    assert isinstance(FakeRepository(), KMindHubWorkspaceMappingPersistence)
