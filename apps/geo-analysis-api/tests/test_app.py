import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from younilab_geo_analysis_api.presentation.http import create_app
from younilab_geo_analysis_api.presentation.http.composition import (
    _build_planning_client,
    build_dependencies,
)
from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import (
    AnalyzeRunResult,
    AuthenticationRequired,
    AuthorizedPrincipal,
    CalculateGeoReportMetrics,
    EvidenceTextRepairCommand,
    EvidenceTextRepairResult,
    GeoAiPlatformRecord,
    GeoEntityAliasRecord,
    GeoEntityMentionDetectionItem,
    GeoRunResultAnalysis,
    GeoRunResultCitationFact,
    GeoRunResultCitationNormalization,
    GeoRunResultEntityDetection,
    GeoRunResultRecord,
    GeoRunResultReferenceRecord,
    GetGeoDashboardReport,
    KMindHubExtractionCommitResult,
    KMindHubExtractionFieldValue,
    KMindHubExtractionPreviewItem,
    KMindHubExtractionPreviewResult,
    PublishResult,
    QueryRunJobMessage,
    ResourceCatalogVerificationDenied,
    ResourceCatalogVerificationUnavailable,
    ResourceTaskReference,
    SaveRunResultCitationNormalizationCommand,
    SaveRunResultEntityDetectionCommand,
    SaveSemanticRunResultAnalysisCommand,
)
from younilab_seo.geo_analysis.domain import JobStatus
from younilab_seo.geo_analysis.infrastructure import KMindHubGeoRunResultAnalyzer

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000002")
AUTH_HEADERS = {"Authorization": "Bearer test-token"}


@dataclass
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


@dataclass
class FakeEvidenceTextRepairer:
    close_calls: int = 0

    async def repair(
        self,
        command: EvidenceTextRepairCommand,
    ) -> EvidenceTextRepairResult:
        raise AssertionError("repair should not run during composition tests")

    async def close(self) -> None:
        self.close_calls += 1


def test_local_admin_portal_preflight_is_allowed() -> None:
    response = _client().options(
        "/api/geo/projects",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]


def test_missing_bearer_token_returns_unauthorized() -> None:
    client = TestClient(
        create_app(
            authorizer=FakeAuthorizer(),
            reference_verifier=FakeReferenceVerifier(),
        )
    )

    response = client.get("/api/geo/projects")

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Authentication required"


def test_expired_access_token_returns_unauthorized() -> None:
    client = _client(authorizer=FakeAuthorizer(authentication_required=True))

    response = client.get("/api/geo/projects")

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Authentication required"


def test_permission_denial_returns_forbidden() -> None:
    client = _client(authorizer=FakeAuthorizer(access_denied=True))

    response = client.get("/api/geo/projects")

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "access denied"


def test_list_ai_platforms_returns_persisted_status() -> None:
    store = GeoApiStore()
    platform_id = uuid4()
    store.ai_platforms[platform_id] = GeoAiPlatformRecord(
        id=platform_id,
        code="google_aio",
        display_name="Google AIO",
        provider_type="serpapi",
        default_model="ai-overview",
        status="paused",
    )
    client = _client(repository=store)

    response = client.get("/api/geo/platforms")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(platform_id),
                "code": "google_aio",
                "displayName": "Google AIO",
                "providerType": "serpapi",
                "defaultModel": "ai-overview",
                "status": "paused",
            }
        ],
        "total": 1,
    }


def test_project_topic_query_and_job_crud_flow() -> None:
    client = _client()

    project_response = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(uuid4()),
            "name": "Acme GEO",
            "defaultRegion": "US",
            "defaultLanguage": "en-US",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    assert project_response.json()["tenantId"] == str(TENANT_ID)

    topic_response = client.post(
        f"/api/geo/projects/{project_id}/topics",
        json={"name": "Supplier evaluation"},
    )
    assert topic_response.status_code == 201
    topic_id = topic_response.json()["id"]

    query_response = client.post(
        f"/api/geo/projects/{project_id}/queries",
        json={
            "topicId": topic_id,
            "queryText": "Who are reliable O-ring suppliers in Taiwan?",
            "region": "US",
            "language": "en-US",
            "intent": "commercial",
            "buyerStage": "supplier_evaluation",
        },
    )
    assert query_response.status_code == 201
    assert query_response.json()["marketType"] == "b2b_procurement"
    query_id = query_response.json()["id"]

    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(uuid4())},
    )
    assert job_response.status_code == 201
    assert job_response.json()["status"] == "pending"

    jobs_response = client.get(f"/api/geo/projects/{project_id}/jobs")
    assert jobs_response.status_code == 200
    assert jobs_response.json()["total"] == 1


def test_project_scoped_setup_lists_return_only_project_resources() -> None:
    client = _client()
    first = _create_project_setup_resources(client, "First GEO")
    second = _create_project_setup_resources(client, "Second GEO")

    expectations = {
        "entity-aliases": first["alias_id"],
        "query-platforms": first["query_platform_id"],
        "schedules": first["schedule_id"],
    }
    excluded_ids = {
        second["alias_id"],
        second["query_platform_id"],
        second["schedule_id"],
    }

    for resource, expected_id in expectations.items():
        response = client.get(
            f"/api/geo/projects/{first['project_id']}/{resource}"
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert [item["id"] for item in response.json()["items"]] == [expected_id]
        assert expected_id not in excluded_ids


def test_project_scoped_setup_lists_respect_resource_grants() -> None:
    store = GeoApiStore()
    allowed_customer_id = uuid4()
    denied_customer_id = uuid4()
    admin = _client(repository=store)
    allowed = _create_project_setup_resources(
        admin,
        "Allowed GEO",
        customer_id=allowed_customer_id,
    )
    denied = _create_project_setup_resources(
        admin,
        "Denied GEO",
        customer_id=denied_customer_id,
    )
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({allowed_customer_id}),
        ),
    )

    for resource in ("entity-aliases", "query-platforms", "schedules"):
        allowed_response = restricted.get(
            f"/api/geo/projects/{allowed['project_id']}/{resource}"
        )
        denied_response = restricted.get(
            f"/api/geo/projects/{denied['project_id']}/{resource}"
        )

        assert allowed_response.status_code == 200
        assert allowed_response.json()["total"] == 1
        assert denied_response.status_code == 200
        assert denied_response.json() == {"items": [], "total": 0}


def test_project_scoped_setup_lists_require_read_capability() -> None:
    client = _client(authorizer=FakeAuthorizer(access_denied=True))
    project_id = uuid4()

    for resource in ("entity-aliases", "query-platforms", "schedules"):
        response = client.get(f"/api/geo/projects/{project_id}/{resource}")

        assert response.status_code == 403
        assert response.headers["content-type"] == "application/problem+json"


def test_projects_are_scoped_by_authorized_tenant() -> None:
    store = GeoApiStore()
    tenant_a = _client(repository=store, authorizer=FakeAuthorizer(TENANT_ID))
    tenant_b = _client(repository=store, authorizer=FakeAuthorizer(OTHER_TENANT_ID))

    created = tenant_a.post("/api/geo/projects", json={"name": "Tenant A GEO"})
    assert created.status_code == 201
    project_id = created.json()["id"]

    list_response = tenant_b.get("/api/geo/projects")
    detail_response = tenant_b.get(f"/api/geo/projects/{project_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"] == []
    assert detail_response.status_code == 404


def test_kmindhub_workspace_mapping_endpoints() -> None:
    workspace_id = uuid4()
    client = _client()

    missing_response = client.get("/api/geo/integrations/kmindhub/workspace")
    assert missing_response.status_code == 404

    bind_response = client.put(
        "/api/geo/integrations/kmindhub/workspace",
        json={
            "workspaceId": str(workspace_id),
            "displayName": "Acme Workspace",
        },
    )

    assert bind_response.status_code == 200
    body = bind_response.json()
    assert body["tenantId"] == str(TENANT_ID)
    assert body["workspaceId"] == str(workspace_id)
    assert body["displayName"] == "Acme Workspace"
    assert body["provisioningMode"] == "manual"
    assert body["status"] == "active"

    get_response = client.get("/api/geo/integrations/kmindhub/workspace")

    assert get_response.status_code == 200
    assert get_response.json()["workspaceId"] == str(workspace_id)


def test_composition_builds_report_semantic_analysis_dependency() -> None:
    kmindhub_client = FakeKMindHubClient()
    repairer = FakeEvidenceTextRepairer()
    dependencies = build_dependencies(
        repository=GeoApiStore(),
        planning_client=FakePlanningClient(),
        kmindhub_client=kmindhub_client,
        evidence_text_repairer=repairer,
        authorizer=FakeAuthorizer(),
        reference_verifier=FakeReferenceVerifier(),
    )

    assert isinstance(dependencies.analyze_run_result, AnalyzeRunResult)
    assert isinstance(
        dependencies.analyze_run_result.analyzer,
        KMindHubGeoRunResultAnalyzer,
    )
    assert dependencies.analyze_run_result.analyzer.evidence_text_repairer is repairer
    assert dependencies.evidence_text_repairer is repairer
    assert not hasattr(dependencies, "run_kmindhub_analysis_extraction")
    assert isinstance(
        dependencies.calculate_geo_report_metrics,
        CalculateGeoReportMetrics,
    )
    assert isinstance(
        dependencies.get_geo_dashboard_report,
        GetGeoDashboardReport,
    )
    assert dependencies.closeables.count(kmindhub_client) == 1
    assert dependencies.closeables.count(repairer) == 1

    asyncio.run(dependencies.close())

    assert repairer.close_calls == 1


def test_api_planning_client_keeps_environment_timeout(monkeypatch) -> None:
    monkeypatch.setenv("GEO_TRACKING_BASE_URL", "http://tracking.example")
    monkeypatch.setenv("GEO_TRACKING_TIMEOUT_SECONDS", "37")

    client = _build_planning_client()

    assert client.base_url == "http://tracking.example"
    assert client.timeout_seconds == 37.0


def test_app_state_exposes_report_semantic_analysis_dependency() -> None:
    client = _client(kmindhub_client=FakeKMindHubClient())

    assert isinstance(client.app.state.analyze_run_result, AnalyzeRunResult)
    assert not hasattr(client.app.state, "run_kmindhub_analysis_extraction")
    assert isinstance(
        client.app.state.calculate_geo_report_metrics,
        CalculateGeoReportMetrics,
    )
    assert isinstance(
        client.app.state.get_geo_dashboard_report,
        GetGeoDashboardReport,
    )


def test_kmindhub_workspace_provision_creates_remote_workspace() -> None:
    kmindhub_client = FakeKMindHubClient(created_workspace_id=uuid4())
    client = _client(kmindhub_client=kmindhub_client)

    response = client.post(
        "/api/geo/integrations/kmindhub/workspace/provision",
        json={"displayName": "Acme Workspace"},
    )

    assert response.status_code == 201
    assert kmindhub_client.created_display_names == ["Acme Workspace"]
    assert response.json()["workspaceId"] == str(kmindhub_client.created_workspace_id)
    assert response.json()["provisioningMode"] == "manual_provisioned"


def test_kmindhub_workspace_provision_rejects_existing_mapping() -> None:
    kmindhub_client = FakeKMindHubClient(created_workspace_id=uuid4())
    client = _client(kmindhub_client=kmindhub_client)
    first_response = client.post(
        "/api/geo/integrations/kmindhub/workspace/provision",
        json={"displayName": "Acme Workspace"},
    )

    second_response = client.post(
        "/api/geo/integrations/kmindhub/workspace/provision",
        json={"displayName": "Another Workspace"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"] == "KMindHub workspace mapping already exists"
    )
    assert kmindhub_client.created_display_names == ["Acme Workspace"]


def test_kmindhub_workspace_mapping_rejects_tenant_id_from_request() -> None:
    client = _client()

    response = client.put(
        "/api/geo/integrations/kmindhub/workspace",
        json={
            "tenantId": str(OTHER_TENANT_ID),
            "workspaceId": str(uuid4()),
            "displayName": "Acme Workspace",
        },
    )

    assert response.status_code == 422
    assert "body.tenantId" in _invalid_param_names(response.json())


def test_projects_are_scoped_by_resource_grants() -> None:
    store = GeoApiStore()
    allowed_customer_id = uuid4()
    denied_customer_id = uuid4()
    admin = _client(repository=store)
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({allowed_customer_id}),
        ),
    )
    allowed_project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(allowed_customer_id), "name": "Allowed GEO"},
    )
    denied_project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(denied_customer_id), "name": "Denied GEO"},
    )
    unscoped_project = admin.post("/api/geo/projects", json={"name": "Unscoped GEO"})
    assert allowed_project.status_code == 201
    assert denied_project.status_code == 201
    assert unscoped_project.status_code == 201

    list_response = restricted.get("/api/geo/projects")
    denied_detail = restricted.get(f"/api/geo/projects/{denied_project.json()['id']}")
    unscoped_detail = restricted.get(
        f"/api/geo/projects/{unscoped_project.json()['id']}"
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [
        allowed_project.json()["id"]
    ]
    assert denied_detail.status_code == 404
    assert unscoped_detail.status_code == 404


def test_project_summary_includes_own_brand_aliases_and_customer_name() -> None:
    customer_id = uuid4()
    customer_reader = FakeCustomerReader({customer_id: "範例客戶"})
    client = _client(customer_reader=customer_reader)
    project = client.post(
        "/api/geo/projects",
        json={"customerId": str(customer_id), "name": "範例 Project"},
    )
    project_id = project.json()["id"]
    entity = client.post(
        f"/api/geo/projects/{project_id}/entities",
        json={
            "entityType": "own_brand",
            "name": "範例品牌",
            "websiteUrl": "https://example.com",
        },
    )
    client.put(
        f"/api/geo/entities/{entity.json()['id']}/aliases",
        json={"items": [{"alias": "品牌別名"}]},
    )

    response = client.get("/api/geo/projects")

    assert response.status_code == 200
    assert response.json()["items"][0]["customerName"] == "範例客戶"
    assert response.json()["items"][0]["ownBrand"] == {
        "entityId": entity.json()["id"],
        "websiteUrl": "https://example.com",
        "aliases": ["品牌別名"],
    }
    assert customer_reader.requested_ids == {customer_id}


def test_project_summary_keeps_local_data_when_customer_catalog_is_unavailable() -> None:
    customer_id = uuid4()
    client = _client(customer_reader=FakeCustomerReader({}, unavailable=True))
    project = client.post(
        "/api/geo/projects",
        json={"customerId": str(customer_id), "name": "Local Project"},
    )

    response = client.get("/api/geo/projects")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "id": project.json()["id"],
            "tenantId": str(TENANT_ID),
            "customerId": str(customer_id),
            "customerName": None,
            "name": "Local Project",
            "defaultRegion": "TW",
            "defaultLanguage": "zh-TW",
            "status": "active",
            "dailyRunBudget": 0,
            "ownBrand": None,
            "createdAt": project.json()["createdAt"],
            "updatedAt": project.json()["updatedAt"],
        }
    ]


def test_alias_collection_replaces_all_entity_aliases_idempotently() -> None:
    client = _client()
    project_id = _create_project(client)
    entity = client.post(
        f"/api/geo/projects/{project_id}/entities",
        json={"entityType": "own_brand", "name": "範例品牌"},
    ).json()

    created = client.put(
        f"/api/geo/entities/{entity['id']}/aliases",
        json={
            "items": [
                {"alias": " 品牌別名 ", "matchType": "exact"},
                {"alias": "Brand", "matchType": "contains"},
            ]
        },
    )
    assert created.status_code == 200
    assert {item["alias"] for item in created.json()["items"]} == {"品牌別名", "Brand"}
    original = {item["alias"]: item for item in created.json()["items"]}

    replaced = client.put(
        f"/api/geo/entities/{entity['id']}/aliases",
        json={
            "items": [
                {"alias": "Brand", "matchType": "domain"},
                {"alias": "brand", "matchType": "exact"},
            ]
        },
    )
    assert replaced.status_code == 200
    assert replaced.json()["total"] == 2
    values = {item["alias"]: item for item in replaced.json()["items"]}
    assert set(values) == {"Brand", "brand"}
    assert values["Brand"]["id"] == original["Brand"]["id"]
    assert values["Brand"]["createdAt"] == original["Brand"]["createdAt"]
    assert values["Brand"]["matchType"] == "domain"

    repeated = client.put(
        f"/api/geo/entities/{entity['id']}/aliases",
        json={
            "items": [
                {"alias": "Brand", "matchType": "domain"},
                {"alias": "brand", "matchType": "exact"},
            ]
        },
    )
    assert repeated.json() == replaced.json()
    assert client.get(f"/api/geo/entities/{entity['id']}/aliases").json() == replaced.json()

    cleared = client.put(
        f"/api/geo/entities/{entity['id']}/aliases",
        json={"items": []},
    )
    assert cleared.json() == {"items": [], "total": 0}


def test_alias_collection_get_preserves_legacy_whitespace() -> None:
    store = GeoApiStore()
    client = _client(repository=store)
    project_id = _create_project(client)
    entity = client.post(
        f"/api/geo/projects/{project_id}/entities",
        json={"entityType": "own_brand", "name": "Legacy Brand"},
    ).json()
    legacy_alias = GeoEntityAliasRecord(
        id=uuid4(),
        entity_id=UUID(entity["id"]),
        alias=" Legacy Alias ",
        match_type="exact",
        created_at=datetime.now(UTC),
    )
    store.aliases[legacy_alias.id] = legacy_alias

    aliases = client.get(f"/api/geo/entities/{entity['id']}/aliases")
    projects = client.get("/api/geo/projects")

    assert aliases.status_code == 200
    assert aliases.json()["items"][0]["alias"] == " Legacy Alias "
    assert projects.json()["items"][0]["ownBrand"]["aliases"] == [
        " Legacy Alias "
    ]


@pytest.mark.parametrize(
    ("payload", "invalid_name"),
    [
        (
            {"items": [{"alias": "Same"}, {"alias": "Same"}]},
            "body.items",
        ),
        ({"items": [{"alias": "   "}]}, "body.items.0.alias"),
        ({"items": [{"alias": "Alias", "unknown": True}]}, "body.items.0.unknown"),
        ({"items": [], "unknown": True}, "body.unknown"),
    ],
)
def test_alias_collection_rejects_invalid_payloads(
    payload: dict,
    invalid_name: str,
) -> None:
    client = _client()
    project_id = _create_project(client)
    entity = client.post(
        f"/api/geo/projects/{project_id}/entities",
        json={"entityType": "own_brand", "name": "範例品牌"},
    ).json()

    response = client.put(
        f"/api/geo/entities/{entity['id']}/aliases",
        json=payload,
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert invalid_name in _invalid_param_names(response.json())


def test_alias_collection_replace_respects_permissions_tenant_and_customer_scope() -> None:
    store = GeoApiStore()
    allowed_customer_id = uuid4()
    denied_customer_id = uuid4()
    admin = _client(repository=store)
    allowed = _create_project_setup_resources(
        admin,
        "Allowed Aliases",
        customer_id=allowed_customer_id,
    )
    denied = _create_project_setup_resources(
        admin,
        "Denied Aliases",
        customer_id=denied_customer_id,
    )
    allowed_entity_id = admin.get(
        f"/api/geo/projects/{allowed['project_id']}/entities"
    ).json()["items"][0]["id"]
    denied_entity_id = admin.get(
        f"/api/geo/projects/{denied['project_id']}/entities"
    ).json()["items"][0]["id"]
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({allowed_customer_id}),
        ),
    )

    assert restricted.put(
        f"/api/geo/entities/{allowed_entity_id}/aliases",
        json={"items": [{"alias": "Allowed"}]},
    ).status_code == 200
    assert restricted.put(
        f"/api/geo/entities/{denied_entity_id}/aliases",
        json={"items": [{"alias": "Denied"}]},
    ).status_code == 404
    assert restricted.get(
        f"/api/geo/entities/{denied_entity_id}/aliases"
    ).status_code == 404
    assert _client(
        repository=store,
        authorizer=FakeAuthorizer(OTHER_TENANT_ID),
    ).put(
        f"/api/geo/entities/{allowed_entity_id}/aliases",
        json={"items": []},
    ).status_code == 404
    assert _client(
        repository=store,
        authorizer=FakeAuthorizer(OTHER_TENANT_ID),
    ).get(
        f"/api/geo/entities/{allowed_entity_id}/aliases"
    ).status_code == 404
    forbidden = _client(
        repository=store,
        authorizer=FakeAuthorizer(access_denied=True),
    ).put(
        f"/api/geo/entities/{allowed_entity_id}/aliases",
        json={"items": []},
    )
    assert forbidden.status_code == 403
    assert forbidden.headers["content-type"] == "application/problem+json"


def test_project_summary_customer_filter_is_optional_and_scope_safe() -> None:
    store = GeoApiStore()
    first_customer_id = uuid4()
    second_customer_id = uuid4()
    admin = _client(repository=store)
    first = admin.post(
        "/api/geo/projects",
        json={"customerId": str(first_customer_id), "name": "First"},
    )
    second = admin.post(
        "/api/geo/projects",
        json={"customerId": str(second_customer_id), "name": "Second"},
    )
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({first_customer_id}),
        ),
    )

    all_response = admin.get("/api/geo/projects")
    filtered_response = admin.get(
        "/api/geo/projects", params={"customerId": str(first_customer_id)}
    )
    denied_filter = restricted.get(
        "/api/geo/projects", params={"customerId": str(second_customer_id)}
    )

    assert {item["id"] for item in all_response.json()["items"]} == {
        first.json()["id"],
        second.json()["id"],
    }
    assert [item["id"] for item in filtered_response.json()["items"]] == [
        first.json()["id"]
    ]
    assert denied_filter.json() == {"items": [], "total": 0}


def test_project_query_settings_crud_is_idempotent_and_scope_safe() -> None:
    store = GeoApiStore()
    customer_id = uuid4()
    admin = _client(repository=store)
    project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(customer_id), "name": "Settings Project"},
    )
    project_id = project.json()["id"]
    missing = admin.get(f"/api/geo/projects/{project_id}/query-settings")

    first = admin.put(
        f"/api/geo/projects/{project_id}/query-settings",
        json=_query_settings_payload(),
    )
    repeated = admin.put(
        f"/api/geo/projects/{project_id}/query-settings",
        json=_query_settings_payload(),
    )
    fetched = admin.get(f"/api/geo/projects/{project_id}/query-settings")
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({uuid4()}),
        ),
    )

    assert missing.status_code == 404
    assert first.status_code == 200
    assert first.json()["keywords"] == ["ERP", "採購"]
    assert [intent["category"] for intent in first.json()["intents"]] == [
        "commercial_investigation",
        "transactional",
    ]
    assert repeated.json()["updatedAt"] == first.json()["updatedAt"]
    assert fetched.json() == first.json()
    assert not store.query_research_runs
    assert not store.query_generation_runs
    assert not store.query_drafts
    assert not store.queries
    assert not store.jobs
    assert not store.schedules
    assert (
        restricted.get(f"/api/geo/projects/{project_id}/query-settings").status_code
        == 404
    )
    assert (
        restricted.put(
            f"/api/geo/projects/{project_id}/query-settings",
            json=_query_settings_payload(),
        ).status_code
        == 404
    )

    assert admin.delete(f"/api/geo/projects/{project_id}").status_code == 204
    assert UUID(project_id) not in store.project_query_settings


def test_project_status_api_pauses_and_resumes_without_replacing_project() -> None:
    client = _client()
    customer_id = uuid4()
    created = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(customer_id),
            "name": "Status Project",
            "defaultRegion": "US",
            "defaultLanguage": "en-US",
            "dailyRunBudget": 12,
        },
    )
    project_id = created.json()["id"]

    paused = client.patch(
        f"/api/geo/projects/{project_id}/status",
        json={"status": "paused"},
    )
    repeated = client.patch(
        f"/api/geo/projects/{project_id}/status",
        json={"status": "paused"},
    )
    paused_project = client.get(f"/api/geo/projects/{project_id}")
    resumed = client.patch(
        f"/api/geo/projects/{project_id}/status",
        json={"status": "active"},
    )
    active_project = client.get(f"/api/geo/projects/{project_id}")

    assert paused.status_code == 200
    assert paused.json()["projectId"] == project_id
    assert paused.json()["status"] == "paused"
    assert repeated.json()["updatedAt"] == paused.json()["updatedAt"]
    assert paused_project.json()["status"] == "paused"
    assert paused_project.json()["name"] == "Status Project"
    assert paused_project.json()["customerId"] == str(customer_id)
    assert paused_project.json()["dailyRunBudget"] == 12
    assert resumed.json()["status"] == "active"
    assert active_project.json()["status"] == "active"


@pytest.mark.parametrize("payload", [{"status": "archived"}, {"status": ""}, {}])
def test_project_status_api_rejects_unsupported_status(payload: dict) -> None:
    client = _client()
    project_id = _create_project(client)

    response = client.patch(
        f"/api/geo/projects/{project_id}/status",
        json=payload,
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "body.status" in _invalid_param_names(response.json())


def test_project_status_api_hides_project_outside_resource_scope() -> None:
    store = GeoApiStore()
    customer_id = uuid4()
    admin = _client(repository=store)
    project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(customer_id), "name": "Denied Status Project"},
    )
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({uuid4()}),
        ),
    )

    response = restricted.patch(
        f"/api/geo/projects/{project.json()['id']}/status",
        json={"status": "paused"},
    )

    assert response.status_code == 404
    current = admin.get(f"/api/geo/projects/{project.json()['id']}")
    assert current.json()["status"] == "active"


def test_query_status_api_pauses_without_replacing_query() -> None:
    client, _, query_id = _client_with_query(market_type="b2c")
    before = client.get(f"/api/geo/queries/{query_id}").json()

    paused = client.patch(
        f"/api/geo/queries/{query_id}/status",
        json={"status": "paused"},
    )
    repeated = client.patch(
        f"/api/geo/queries/{query_id}/status",
        json={"status": "paused"},
    )
    after = client.get(f"/api/geo/queries/{query_id}").json()

    assert paused.status_code == 200
    assert paused.json()["queryId"] == query_id
    assert paused.json()["status"] == "paused"
    assert repeated.json()["updatedAt"] == paused.json()["updatedAt"]
    assert after == {**before, "status": "paused", "updatedAt": paused.json()["updatedAt"]}


@pytest.mark.parametrize("payload", [{"status": "archived"}, {"status": ""}, {}])
def test_query_status_api_rejects_unsupported_status(payload: dict) -> None:
    client, _, query_id = _client_with_query()

    response = client.patch(
        f"/api/geo/queries/{query_id}/status",
        json=payload,
    )

    assert response.status_code == 422
    assert "body.status" in _invalid_param_names(response.json())


def test_query_status_api_does_not_restore_archived_query() -> None:
    client, store, query_id = _client_with_query()
    query_uuid = UUID(query_id)
    store.queries[query_uuid] = store.queries[query_uuid].model_copy(
        update={"status": "archived"}
    )

    response = client.patch(
        f"/api/geo/queries/{query_id}/status",
        json={"status": "active"},
    )

    assert response.status_code == 409
    assert store.queries[query_uuid].status == "archived"


def test_query_status_api_hides_query_outside_resource_scope() -> None:
    store = GeoApiStore()
    customer_id = uuid4()
    admin = _client(repository=store)
    query_id = _create_query_for_customer(admin, customer_id)
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({uuid4()}),
        ),
    )

    response = restricted.patch(
        f"/api/geo/queries/{query_id}/status",
        json={"status": "paused"},
    )

    assert response.status_code == 404
    assert admin.get(f"/api/geo/queries/{query_id}").json()["status"] == "active"


@pytest.mark.parametrize(
    ("override", "invalid_name"),
    [
        ({"researchProvider": "openai"}, "body.researchProvider"),
        ({"marketType": "consumer"}, "body.marketType"),
        ({"maxQueries": 0}, "body.maxQueries"),
        ({"unknown": True}, "body.unknown"),
    ],
)
def test_project_query_settings_rejects_invalid_payload(
    override: dict,
    invalid_name: str,
) -> None:
    client = _client()
    project_id = _create_project(client)

    response = client.put(
        f"/api/geo/projects/{project_id}/query-settings",
        json={**_query_settings_payload(), **override},
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert invalid_name in _invalid_param_names(response.json())


def test_project_query_settings_accepts_legacy_single_intent_request() -> None:
    client = _client()
    project_id = _create_project(client)
    payload = _query_settings_payload()
    legacy_intent = payload.pop("intents")[0]

    response = client.put(
        f"/api/geo/projects/{project_id}/query-settings",
        json={**payload, "intent": legacy_intent},
    )

    assert response.status_code == 200
    assert response.json()["intents"] == [
        {
            "category": "commercial_investigation",
            "description": "比較供應商",
        }
    ]


def test_openapi_describes_project_summary_and_query_settings() -> None:
    schema = _client().get("/openapi.json").json()

    projects = schema["paths"]["/api/geo/projects"]["get"]
    settings_path = schema["paths"]["/api/geo/projects/{project_id}/query-settings"]
    status_path = schema["paths"]["/api/geo/projects/{project_id}/status"]
    query_status_path = schema["paths"]["/api/geo/queries/{query_id}/status"]
    create_job_path = schema["paths"]["/api/geo/queries/{query_id}/jobs"]["post"]
    aliases_path = schema["paths"]["/api/geo/entities/{entity_id}/aliases"]
    overview_response = schema["components"]["schemas"]["OverviewReportResponse"]
    assert projects["parameters"][0]["name"] == "customerId"
    assert "ProjectSummaryPageResponse" in str(projects["responses"]["200"])
    assert "ProblemDetailsResponse" in str(projects["responses"]["422"])
    assert "ProjectQuerySettingsResponse" in str(settings_path["get"]["responses"]["200"])
    assert "ProjectQuerySettingsRequest" in str(settings_path["put"]["requestBody"])
    assert "ProblemDetailsResponse" in str(settings_path["put"]["responses"]["422"])
    assert "ProjectStatusRequest" in str(status_path["patch"]["requestBody"])
    assert "ProjectStatusResponse" in str(status_path["patch"]["responses"]["200"])
    assert "QueryStatusRequest" in str(query_status_path["patch"]["requestBody"])
    assert "QueryStatusResponse" in str(query_status_path["patch"]["responses"]["200"])
    assert "ProblemDetailsResponse" in str(query_status_path["patch"]["responses"]["409"])
    assert "CreateJobResponse" in str(create_job_path["responses"]["200"])
    assert "CreateJobResponse" in str(create_job_path["responses"]["201"])
    assert "AliasCollectionResponse" in str(aliases_path["get"]["responses"]["200"])
    assert "AliasCollectionRequest" in str(aliases_path["put"]["requestBody"])
    assert "AliasCollectionResponse" in str(aliases_path["put"]["responses"]["200"])
    assert "ProblemDetailsResponse" in str(aliases_path["put"]["responses"]["422"])
    assert overview_response["properties"]["isPreparing"]["type"] == "boolean"
    assert "isPreparing" in overview_response["required"]
    assert "post" not in aliases_path
    assert "/api/geo/entity-aliases/{alias_id}" not in schema["paths"]


def test_job_and_run_result_are_scoped_by_resource_grants() -> None:
    store = GeoApiStore()
    allowed_customer_id = uuid4()
    denied_customer_id = uuid4()
    admin = _client(repository=store)
    allowed_query_id = _create_query_for_customer(admin, allowed_customer_id)
    denied_query_id = _create_query_for_customer(admin, denied_customer_id)
    allowed_job = admin.post(
        f"/api/geo/queries/{allowed_query_id}/jobs",
        json={"platformId": str(uuid4())},
    )
    denied_job = admin.post(
        f"/api/geo/queries/{denied_query_id}/jobs",
        json={"platformId": str(uuid4())},
    )
    assert allowed_job.status_code == 201
    assert denied_job.status_code == 201
    allowed_result_id = _add_run_result(store, UUID(allowed_job.json()["id"]))
    denied_result_id = _add_run_result(store, UUID(denied_job.json()["id"]))
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({allowed_customer_id}),
        ),
    )

    allowed_job_response = restricted.get(f"/api/geo/jobs/{allowed_job.json()['id']}")
    denied_job_response = restricted.get(f"/api/geo/jobs/{denied_job.json()['id']}")
    allowed_result_response = restricted.get(
        f"/api/geo/run-results/{allowed_result_id}"
    )
    denied_result_response = restricted.get(f"/api/geo/run-results/{denied_result_id}")

    assert allowed_job_response.status_code == 200
    assert denied_job_response.status_code == 404
    assert allowed_result_response.status_code == 200
    assert denied_result_response.status_code == 404


def test_validation_error_returns_problem_details() -> None:
    client = _client()

    response = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(uuid4()),
            "name": "   ",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["detail"] == "Request validation failed"
    assert _invalid_param_names(body) == {"body.name"}


def test_project_accepts_and_ignores_deprecated_seo_task_id() -> None:
    client = _client()

    response = client.post("/api/geo/projects", json={"name": "Draft GEO"})

    assert response.status_code == 201
    assert response.json()["customerId"] is None
    assert "seoTaskId" not in response.json()

    compatible = client.post(
        "/api/geo/projects",
        json={"name": "Compatible GEO", "seoTaskId": str(uuid4())},
    )

    assert compatible.status_code == 201
    assert "seoTaskId" not in compatible.json()


def test_project_reference_verification_denied_returns_forbidden() -> None:
    client = _client(reference_verifier=FakeReferenceVerifier(denied=True))

    response = client.post(
        "/api/geo/projects",
        json={"customerId": str(uuid4()), "name": "Denied GEO"},
    )

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "resource catalog reference verification denied"


def test_project_reference_authentication_failure_returns_unauthorized() -> None:
    client = _client(
        reference_verifier=FakeReferenceVerifier(authentication_required=True)
    )

    response = client.post(
        "/api/geo/projects",
        json={"customerId": str(uuid4()), "name": "Denied GEO"},
    )

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Authentication required"


def test_project_reference_unavailable_returns_service_unavailable() -> None:
    client = _client(reference_verifier=FakeReferenceVerifier(unavailable=True))

    response = client.post(
        "/api/geo/projects",
        json={"customerId": str(uuid4()), "name": "Unavailable GEO"},
    )

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "resource catalog unavailable"


def test_project_request_rejects_client_tenant_id() -> None:
    client = _client()

    response = client.post(
        "/api/geo/projects",
        json={"tenantId": str(uuid4()), "name": "Tenant spoof"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "body.tenantId" in _invalid_param_names(response.json())


def test_query_research_generation_and_draft_accept_flow() -> None:
    planning_client = FakePlanningClient()
    client = _client(planning_client=planning_client)
    project_response = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(uuid4()),
            "name": "Acme GEO",
        },
    )
    project_id = project_response.json()["id"]

    research_response = client.post(
        f"/api/geo/projects/{project_id}/query-research-runs",
        json={
            "provider": "gemini",
            "brandName": "Acme",
            "keywords": ["erp"],
            "region": "TW",
            "language": "zh-TW",
            "marketType": "b2b_procurement",
            "audience": {"name": "採購", "description": "B2B 採購人員"},
            "brandMentionRules": {
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": True,
            },
        },
    )

    assert research_response.status_code == 201
    research_body = research_response.json()
    assert research_body["status"] == "completed"
    assert research_body["result"]["researchContext"] == "研究摘要"
    assert research_body["result"]["sourceUrls"] == ["https://example.com/source"]
    assert "intents" not in research_body["requestPayload"]
    assert research_body["requestPayload"]["brandMentionRules"] == {
        "shouldMentionOwnBrand": True,
        "shouldMentionCompetitor": True,
    }

    generation_response = client.post(
        f"/api/geo/projects/{project_id}/query-generation-runs",
        json={
            "provider": "gemini",
            "brandName": "Acme",
            "keywords": ["erp"],
            "region": "TW",
            "language": "zh-TW",
            "marketType": "b2b_procurement",
            "topicNames": ["ERP 導入"],
            "intents": [{"category": "commercial", "description": "比較供應商"}],
            "audience": {"name": "採購", "description": "B2B 採購人員"},
            "researchContext": research_body["result"]["researchContext"],
        },
    )

    assert generation_response.status_code == 201
    generation_body = generation_response.json()
    draft = generation_body["drafts"][0]
    assert draft["queryText"] == "Acme ERP 適合哪些 B2B 採購情境?"
    assert draft["topicName"] == "ERP 導入"

    selection_response = client.patch(
        f"/api/geo/query-drafts/{draft['id']}/selection",
        json={"selectionStatus": "shortlisted"},
    )

    assert selection_response.status_code == 200
    assert selection_response.json()["selectionStatus"] == "shortlisted"

    accept_response = client.post(
        f"/api/geo/query-drafts/{draft['id']}/accept",
        json={"createTopicIfMissing": True},
    )

    assert accept_response.status_code == 200
    assert accept_response.json()["queryText"] == draft["queryText"]
    assert accept_response.json()["marketType"] == "b2b_procurement"

    rejected_after_accept = client.patch(
        f"/api/geo/query-drafts/{draft['id']}/selection",
        json={"selectionStatus": "rejected"},
    )

    assert rejected_after_accept.status_code == 409
    assert rejected_after_accept.headers["content-type"] == "application/problem+json"
    assert rejected_after_accept.json()["detail"] == "query draft already accepted"


def test_unselected_generated_intent_remains_acceptable_as_unclassified() -> None:
    class UnclassifiedPlanningClient(FakePlanningClient):
        async def generate(self, command) -> dict:
            result = await super().generate(command)
            result["queries"][0]["attributes"]["intent"] = {
                "category": "transactional",
                "description": "立即購買",
            }
            return result

    client = _client(planning_client=UnclassifiedPlanningClient())
    project_id = _create_project(client)
    response = client.post(
        f"/api/geo/projects/{project_id}/query-generation-runs",
        json={
            "provider": "gemini",
            "brandName": "Acme",
            "keywords": ["erp"],
            "region": "TW",
            "language": "zh-TW",
            "marketType": "b2b_procurement",
            "topicNames": ["ERP 導入"],
            "intents": [
                {"category": "informational", "description": "了解 ERP"}
            ],
            "audience": {"name": "採購", "description": "B2B 採購人員"},
            "maxQueries": 1,
        },
    )

    assert response.status_code == 201
    draft = response.json()["drafts"][0]
    assert draft["intent"] is None
    assert draft["metadata"]["rawIntentCategory"] == "transactional"

    accepted = client.post(
        f"/api/geo/query-drafts/{draft['id']}/accept",
        json={"createTopicIfMissing": True},
    )

    assert accepted.status_code == 200
    assert accepted.json()["intent"] is None


def test_query_research_rejects_empty_keywords() -> None:
    client = _client(planning_client=FakePlanningClient())
    project_id = _create_project(client)
    payload = _query_research_payload()
    payload["keywords"] = []

    response = client.post(
        f"/api/geo/projects/{project_id}/query-research-runs",
        json=payload,
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


def test_query_research_rejects_oversized_arrays() -> None:
    client = _client(planning_client=FakePlanningClient())
    project_id = _create_project(client)
    cases = [
        ("keywords", [f"keyword-{index}" for index in range(11)]),
        ("competitorBrands", [f"Competitor {index}" for index in range(9)]),
    ]

    for field_name, value in cases:
        payload = _query_research_payload()
        payload[field_name] = value
        response = client.post(
            f"/api/geo/projects/{project_id}/query-research-runs",
            json=payload,
        )

        assert response.status_code == 422
        assert response.headers["content-type"] == "application/problem+json"


def test_query_research_rejects_generation_intents() -> None:
    client = _client(planning_client=FakePlanningClient())
    project_id = _create_project(client)
    payload = _query_research_payload()
    payload["intents"] = [
        {"category": "commercial_investigation", "description": "比較供應商"}
    ]

    response = client.post(
        f"/api/geo/projects/{project_id}/query-research-runs",
        json=payload,
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


def test_missing_resource_returns_problem_details() -> None:
    client = _client()

    response = client.get(f"/api/geo/projects/{uuid4()}")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "project not found"


def test_query_platform_accepts_and_ignores_legacy_model_override() -> None:
    client, _, query_id = _client_with_query()

    response = client.put(
        f"/api/geo/queries/{query_id}/platforms",
        json=[
            {
                "platformId": str(uuid4()),
                "model": "gemini-2.5-pro",
                "status": "active",
            }
        ],
    )

    assert response.status_code == 200
    assert "model" not in response.json()["items"][0]


def test_query_platform_response_omits_model() -> None:
    client, _, query_id = _client_with_query()

    response = client.put(
        f"/api/geo/queries/{query_id}/platforms",
        json=[{"platformId": str(uuid4()), "status": "active"}],
    )

    assert response.status_code == 200
    assert "model" not in response.json()["items"][0]


def test_terminal_job_cancel_returns_problem_details() -> None:
    client, store, job_id = _client_with_job()
    store.jobs[job_id].status = JobStatus.SUCCEEDED

    response = client.post(f"/api/geo/jobs/{job_id}/cancel")

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "cannot cancel succeeded job"


def test_terminal_job_external_callback_returns_problem_details() -> None:
    client, store, job_id = _client_with_job()
    store.jobs[job_id].status = JobStatus.SUCCEEDED

    response = client.post(
        f"/api/geo/jobs/{job_id}/external-callbacks",
        json={"externalRunId": "runner-1", "status": "running"},
    )

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "cannot apply external status from succeeded"


def test_external_callback_updates_job_through_application_repository() -> None:
    client, store, job_id = _client_with_job()
    store.jobs[job_id].status = JobStatus.PUBLISHED

    response = client.post(
        f"/api/geo/jobs/{job_id}/external-callbacks",
        json={"externalRunId": "runner-1", "status": "running"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running_external"
    assert response.json()["externalRunId"] == "runner-1"
    assert len(store.callbacks) == 1
    assert store.callbacks[0][0].job_id == job_id


def test_dispatch_without_publisher_returns_not_implemented() -> None:
    client, _, job_id = _client_with_job()

    response = client.post(f"/api/geo/jobs/{job_id}/dispatch")

    assert response.status_code == 501
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "message publisher adapter is not configured"


def test_dispatch_publishes_job_message_through_application_use_case() -> None:
    publisher = FakePublisher()
    client, store, query_id = _client_with_query(
        publisher=publisher,
        callback_base_url="http://geo-analysis-api:8002/",
    )
    platform_id = uuid4()
    store.platform_codes[platform_id] = "gemini"
    store.platform_models[platform_id] = "gemini-2.5-flash"
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(platform_id)},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    response = client.post(f"/api/geo/jobs/{job_id}/dispatch")

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert response.json()["dispatchBackend"] == "fake"
    assert len(publisher.messages) == 1
    message = publisher.messages[0]
    assert message.platform == "gemini"
    assert message.model == "gemini-2.5-flash"
    assert message.query_id == UUID(query_id)
    assert not hasattr(message, "seo_task_id")
    assert message.topic_name == ""
    assert message.market_type == "b2b_procurement"
    assert message.is_branded is False
    assert (
        message.callback_url
        == f"http://geo-analysis-api:8002/api/geo/jobs/{job_id}/external-callbacks"
    )


def test_dispatch_google_aio_job_records_provider_queue_destination() -> None:
    publisher = FakePublisher()
    client, store, query_id = _client_with_query(publisher=publisher)
    platform_id = uuid4()
    store.platform_codes[platform_id] = "google_aio"
    store.platform_models[platform_id] = "serpapi-google-ai-overview"
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(platform_id)},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    response = client.post(f"/api/geo/jobs/{job_id}/dispatch")

    assert response.status_code == 200
    assert publisher.messages[0].platform == "google_aio"
    assert store.dispatches[0][1].destination == "geo.query-runs.google_aio"


def test_dispatch_uses_job_snapshot_after_query_is_modified() -> None:
    publisher = FakePublisher()
    client, store, query_id = _client_with_query(publisher=publisher)
    platform_id = uuid4()
    store.platform_codes[platform_id] = "gemini"
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(platform_id)},
    )
    job_id = UUID(job_response.json()["id"])
    store.jobs[job_id].execution_snapshot = {
        "queryText": "建立 job 時的 query",
        "platform": "gemini",
        "region": "TW",
        "language": "zh-TW",
        "marketType": "b2b_procurement",
        "isBranded": False,
    }
    store.queries[UUID(query_id)].query_text = "建立 job 後修改的 query"

    response = client.post(f"/api/geo/jobs/{job_id}/dispatch")

    assert response.status_code == 200
    assert publisher.messages[0].query_text == "建立 job 時的 query"


def test_dispatch_does_not_require_project_seo_task_id() -> None:
    publisher = FakePublisher()
    client, store, query_id = _client_with_query(publisher=publisher)
    platform_id = uuid4()
    store.platform_codes[platform_id] = "gemini"
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(platform_id)},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    response = client.post(f"/api/geo/jobs/{job_id}/dispatch")

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert len(publisher.messages) == 1
    assert not hasattr(publisher.messages[0], "seo_task_id")


def test_create_query_accepts_market_type() -> None:
    client, _, query_id = _client_with_query(market_type="b2c")

    response = client.get(f"/api/geo/queries/{query_id}")

    assert response.status_code == 200
    assert response.json()["marketType"] == "b2c"


def test_job_run_results_can_be_listed_and_loaded() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)
    store.semantic_run_result_analyses[result_id] = GeoRunResultAnalysis(
        runResultId=result_id,
        analyzer="fake",
        analyzerVersion="v1",
        status="completed",
    )

    list_response = client.get(f"/api/geo/jobs/{job_id}/run-results")
    detail_response = client.get(f"/api/geo/run-results/{result_id}")

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    item = list_response.json()["items"][0]
    assert item["id"] == str(result_id)
    assert item["rawResponse"] == "Raw answer"
    assert item["references"][0]["url"] == "https://example.com/reference"
    assert item["analysisStatus"] == "completed"
    assert detail_response.status_code == 200
    assert detail_response.json()["references"][0]["domain"] == "example.com"
    assert detail_response.json()["analysisStatus"] == "completed"


def test_project_run_results_are_scoped_to_project() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)
    project_id = store.jobs[job_id].project_id

    response = client.get(f"/api/geo/projects/{project_id}/run-results")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(result_id)]


def test_run_result_semantic_analysis_can_be_loaded() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)
    entity_id = uuid4()
    store.semantic_run_result_analyses[result_id] = GeoRunResultAnalysis(
        runResultId=result_id,
        analyzer="fake",
        analyzerVersion="v1",
        status="completed",
        sentiments=[
            {
                "entityId": str(entity_id),
                "entityRole": "own_brand",
                "entityName": "Acme",
                "sentiment": "positive",
                "theme": "供應商比較",
                "statement": "Acme is recommended.",
                "evidenceText": "Acme is recommended.",
                "confidence": 0.9,
            }
        ],
    )

    response = client.get(f"/api/geo/run-results/{result_id}/semantic-analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["runResultId"] == str(result_id)
    assert body["status"] == "completed"
    assert body["sentiments"][0]["sentiment"] == "positive"
    assert body["sentiments"][0]["evidenceText"] == "Acme is recommended."


def test_run_result_semantic_analysis_returns_404_when_missing() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)

    response = client.get(f"/api/geo/run-results/{result_id}/semantic-analysis")

    assert response.status_code == 404
    assert response.json()["detail"] == "semantic analysis not found"


def test_project_metrics_returns_report_metrics() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)
    project_id = store.jobs[job_id].project_id
    entity_id = uuid4()
    store.semantic_run_result_analyses[result_id] = GeoRunResultAnalysis(
        runResultId=result_id,
        analyzer="fake",
        analyzerVersion="v1",
        status="completed",
        entityMentions=[
            {
                "entityId": str(entity_id),
                "entityRole": "own_brand",
                "entityName": "Acme",
                "mentioned": True,
                "firstMentionOrder": 1,
            }
        ],
        sentiments=[
            {
                "entityId": str(entity_id),
                "entityRole": "own_brand",
                "entityName": "Acme",
                "sentiment": "positive",
                "theme": "供應商比較",
                "statement": "Acme is recommended.",
            }
        ],
    )
    normalization = GeoRunResultCitationNormalization(
        runResultId=result_id,
        projectId=project_id,
        status="completed",
        citations=[
            GeoRunResultCitationFact(
                runResultId=result_id,
                referenceId=store.run_results[result_id].references[0].id,
                url="https://example.com/reference",
                domain="example.com",
                position=1,
                ownership="other",
                sourceType="unknown",
            )
        ],
    )
    store.run_result_citation_normalizations[
        (result_id, normalization.normalizer_version)
    ] = normalization

    response = client.get(
        f"/api/geo/projects/{project_id}/metrics",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
            "comparisonStart": "2026-06-22T00:00:00+00:00",
            "comparisonEnd": "2026-06-24T00:00:00+00:00",
            "provider": "gemini",
            "region": "TW",
            "language": "zh-TW",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["periodStart"] == "2026-06-24T00:00:00Z"
    assert body["comparisonStart"] == "2026-06-22T00:00:00Z"
    assert "period_start" not in body
    visibility = _metric(body["metrics"], "visibility", "project")
    citation = _metric(
        body["metrics"],
        "citation_count",
        "citation_url",
        "https://example.com/reference",
    )
    sentiment = _metric(body["metrics"], "sentiment_count", "sentiment", "positive")
    assert visibility["value"] == 100
    assert visibility["comparisonValue"] == 0
    assert citation["scopeLabel"] == "https://example.com/reference"
    assert sentiment["value"] == 1


def test_project_dashboard_report_returns_report_view_model() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)
    project_id = store.jobs[job_id].project_id
    entity_id = uuid4()
    store.semantic_run_result_analyses[result_id] = GeoRunResultAnalysis(
        runResultId=result_id,
        analyzer="fake",
        analyzerVersion="v1",
        status="completed",
        entityMentions=[
            {
                "entityId": str(entity_id),
                "entityRole": "own_brand",
                "entityName": "Acme",
                "mentioned": True,
                "firstMentionOrder": 1,
            }
        ],
        sentiments=[
            {
                "entityId": str(entity_id),
                "entityRole": "own_brand",
                "entityName": "Acme",
                "sentiment": "positive",
                "theme": "供應商比較",
                "statement": "Acme is recommended.",
            }
        ],
    )
    normalization = GeoRunResultCitationNormalization(
        runResultId=result_id,
        projectId=project_id,
        status="completed",
        citations=[
            GeoRunResultCitationFact(
                runResultId=result_id,
                referenceId=store.run_results[result_id].references[0].id,
                url="https://example.com/reference",
                domain="example.com",
                position=1,
                ownership="other",
                sourceType="unknown",
            )
        ],
    )
    store.run_result_citation_normalizations[
        (result_id, normalization.normalizer_version)
    ] = normalization

    response = client.get(
        f"/api/geo/projects/{project_id}/reports/dashboard",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
            "comparisonStart": "2026-06-22T00:00:00+00:00",
            "comparisonEnd": "2026-06-24T00:00:00+00:00",
            "provider": "gemini",
            "region": "TW",
            "language": "zh-TW",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["periodStart"] == "2026-06-24T00:00:00Z"
    assert body["comparisonStart"] == "2026-06-22T00:00:00Z"
    assert "citation_urls" not in body
    visibility = next(
        item for item in body["overview"] if item["metricName"] == "visibility"
    )
    assert visibility["metric"]["value"] == 100
    assert visibility["metric"]["comparisonValue"] == 0
    entity = body["entities"][0]
    assert entity["entityRole"] == "own_brand"
    assert entity["visibility"]["value"] == 100
    citation_url = body["citationUrls"][0]
    assert citation_url["value"] == "https://example.com/reference"
    assert citation_url["ownership"] == "other"
    assert citation_url["citationCount"]["value"] == 1
    citation_domain = body["citationDomains"][0]
    assert citation_domain["value"] == "example.com"
    sentiment = body["sentiments"][0]
    assert sentiment["sentiment"] == "positive"
    assert sentiment["statementCount"]["value"] == 1


def test_project_metrics_are_scoped_by_resource_grants() -> None:
    store = GeoApiStore()
    allowed_customer_id = uuid4()
    denied_customer_id = uuid4()
    admin = _client(repository=store)
    allowed_project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(allowed_customer_id), "name": "Allowed GEO"},
    )
    denied_project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(denied_customer_id), "name": "Denied GEO"},
    )
    assert allowed_project.status_code == 201
    assert denied_project.status_code == 201
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({allowed_customer_id}),
        ),
    )

    allowed_response = restricted.get(
        f"/api/geo/projects/{allowed_project.json()['id']}/metrics",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
        },
    )
    denied_response = restricted.get(
        f"/api/geo/projects/{denied_project.json()['id']}/metrics",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
        },
    )

    assert allowed_response.status_code == 200
    assert denied_response.status_code == 404


def test_project_dashboard_report_is_scoped_by_resource_grants() -> None:
    store = GeoApiStore()
    allowed_customer_id = uuid4()
    denied_customer_id = uuid4()
    admin = _client(repository=store)
    allowed_project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(allowed_customer_id), "name": "Allowed GEO"},
    )
    denied_project = admin.post(
        "/api/geo/projects",
        json={"customerId": str(denied_customer_id), "name": "Denied GEO"},
    )
    assert allowed_project.status_code == 201
    assert denied_project.status_code == 201
    restricted = _client(
        repository=store,
        authorizer=FakeAuthorizer(
            has_global_resource_access=False,
            customer_ids=frozenset({allowed_customer_id}),
        ),
    )

    allowed_response = restricted.get(
        f"/api/geo/projects/{allowed_project.json()['id']}/reports/dashboard",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
        },
    )
    denied_response = restricted.get(
        f"/api/geo/projects/{denied_project.json()['id']}/reports/dashboard",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
        },
    )

    assert allowed_response.status_code == 200
    assert denied_response.status_code == 404


def test_project_metrics_validation_error_returns_problem_details() -> None:
    client = _client()
    project_id = _create_project(client)

    response = client.get(
        f"/api/geo/projects/{project_id}/metrics",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
            "comparisonStart": "2026-06-23T00:00:00+00:00",
            "comparisonEnd": "2026-06-25T00:00:00+00:00",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "comparisonEnd" in response.json()["detail"]


def test_project_dashboard_report_validation_error_returns_problem_details() -> None:
    client = _client()
    project_id = _create_project(client)

    response = client.get(
        f"/api/geo/projects/{project_id}/reports/dashboard",
        params={
            "periodStart": "2026-06-24T00:00:00+00:00",
            "periodEnd": "2026-06-26T00:00:00+00:00",
            "comparisonStart": "2026-06-23T00:00:00+00:00",
            "comparisonEnd": "2026-06-25T00:00:00+00:00",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "comparisonEnd" in response.json()["detail"]


def test_missing_run_result_returns_problem_details() -> None:
    client = _client()

    response = client.get(f"/api/geo/run-results/{uuid4()}")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "run result not found"


def test_run_result_analysis_extraction_route_is_disabled() -> None:
    kmindhub_client = FakeKMindHubClient(created_workspace_id=uuid4())
    store = GeoApiStore()
    client, store, job_id = _client_with_job(
        repository=store, kmindhub_client=kmindhub_client
    )
    result_id = _add_run_result(store, job_id)
    client.put(
        "/api/geo/integrations/kmindhub/workspace",
        json={
            "workspaceId": str(kmindhub_client.created_workspace_id),
            "displayName": "Acme Workspace",
        },
    )

    response = client.post(f"/api/geo/run-results/{result_id}/analysis-extractions")

    assert response.status_code == 410
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == (
        "legacy analysis extraction is disabled; dashboard reports use the "
        "worker semantic and citation pipeline"
    )
    assert kmindhub_client.preview_texts == []
    assert kmindhub_client.committed_items == []


def test_store_saves_and_loads_semantic_run_result_analysis() -> None:
    async def run() -> None:
        store = GeoApiStore()
        client, store, job_id = _client_with_job(repository=store)
        result_id = _add_run_result(store, job_id)
        entity_id = uuid4()
        analysis = GeoRunResultAnalysis(
            runResultId=result_id,
            analyzer="fake",
            analyzerVersion="v1",
            status="completed",
            entityMentions=[
                {
                    "entityId": str(entity_id),
                    "entityRole": "own_brand",
                    "entityName": "Acme",
                    "mentioned": True,
                    "firstMentionOrder": 1,
                }
            ],
            sentiments=[
                {
                    "entityId": str(entity_id),
                    "entityRole": "own_brand",
                    "entityName": "Acme",
                    "sentiment": "positive",
                    "theme": "供應商比較",
                    "statement": "Acme is recommended.",
                }
            ],
            semanticFacts=[
                {
                    "factType": "topic",
                    "value": "供應商比較",
                }
            ],
        )

        saved = await store.save_semantic_run_result_analysis(
            TENANT_ID,
            SaveSemanticRunResultAnalysisCommand(analysis=analysis),
            datetime(2026, 7, 5, tzinfo=UTC),
        )
        await store.save_run_result_entity_detection(
            TENANT_ID,
            SaveRunResultEntityDetectionCommand(
                detection=GeoRunResultEntityDetection(
                    runResultId=result_id,
                    status="completed",
                    items=[
                        GeoEntityMentionDetectionItem(
                            entityId=entity_id,
                            entityRole="own_brand",
                            entityName="Acme deterministic",
                            mentioned=True,
                            firstMentionOrder=1,
                            evidenceText="Acme",
                            matchedBy="canonical",
                            matchedValue="Acme",
                            matchType="canonical",
                        )
                    ],
                )
            ),
            datetime(2026, 7, 5, tzinfo=UTC),
        )
        loaded = await store.get_semantic_run_result_analysis(TENANT_ID, result_id)

        client.close()
        assert saved == analysis
        assert loaded is not None
        assert loaded.entity_mentions[0].first_mention_order == 1
        assert loaded.entity_mentions[0].entity_name == "Acme deterministic"
        assert loaded.sentiments[0].sentiment == "positive"
        assert loaded.semantic_facts[0].fact_type == "topic"

    asyncio.run(run())


def test_store_saves_and_loads_citation_normalization() -> None:
    async def run() -> None:
        store = GeoApiStore()
        client, store, job_id = _client_with_job(repository=store)
        result_id = _add_run_result(store, job_id)
        reference_id = store.run_results[result_id].references[0].id
        normalization = GeoRunResultCitationNormalization(
            runResultId=result_id,
            projectId=store.jobs[job_id].project_id,
            status="completed",
            citations=[
                GeoRunResultCitationFact(
                    runResultId=result_id,
                    referenceId=reference_id,
                    url="https://example.com/reference",
                    domain="example.com",
                    title="Example reference",
                    position=1,
                    ownership="other",
                    sourceType="unknown",
                )
            ],
        )

        saved = await store.save_run_result_citation_normalization(
            TENANT_ID,
            SaveRunResultCitationNormalizationCommand(normalization=normalization),
            datetime(2026, 7, 5, tzinfo=UTC),
        )
        loaded = await store.get_run_result_citation_normalization(
            TENANT_ID,
            result_id,
            "url_domain:v2",
        )

        client.close()
        assert saved == normalization
        assert loaded == normalization
        with pytest.raises(ValueError, match="reference_id must belong"):
            await store.save_run_result_citation_normalization(
                TENANT_ID,
                SaveRunResultCitationNormalizationCommand(
                    normalization=GeoRunResultCitationNormalization(
                        runResultId=result_id,
                        projectId=store.jobs[job_id].project_id,
                        status="completed",
                        citations=[
                            GeoRunResultCitationFact(
                                runResultId=result_id,
                                referenceId=uuid4(),
                                url="https://example.com/other",
                                domain="example.com",
                                position=1,
                                ownership="other",
                                sourceType="unknown",
                            )
                        ],
                    )
                ),
                datetime(2026, 7, 5, tzinfo=UTC),
            )

    asyncio.run(run())


def test_app_lifespan_closes_injected_publisher() -> None:
    publisher = FakePublisher()
    store = GeoApiStore()

    with _client(repository=store, publisher=publisher) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert publisher.closed is True


def test_job_creation_reuses_the_daily_query_platform_slot() -> None:
    client, store, query_id = _client_with_query()
    platform_id = str(uuid4())

    first_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T00:00:00.123456+00:00",
        },
    )
    store.jobs[UUID(first_response.json()["id"])].status = JobStatus.FAILED
    second_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T08:00:00.987654+08:00",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["wasCreated"] is True
    assert second_response.json()["wasCreated"] is False
    assert first_response.json()["id"] == second_response.json()["id"]
    assert second_response.json()["status"] == "failed"
    assert first_response.json()["dedupeKey"] == second_response.json()["dedupeKey"]
    assert datetime.fromisoformat(first_response.json()["scheduledFor"]) == datetime(
        2026, 6, 22, tzinfo=UTC
    )


@pytest.mark.parametrize("existing_status", [JobStatus.PENDING, JobStatus.DELAYED])
def test_first_run_promotes_a_retryable_manual_daily_slot(
    existing_status: JobStatus,
) -> None:
    client, store, query_id = _client_with_query()
    platform_id = str(uuid4())
    manual_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T00:00:00Z",
            "jobType": "manual_run",
        },
    )
    store.jobs[UUID(manual_response.json()["id"])].status = existing_status

    first_run_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T08:00:00+08:00",
            "jobType": "query_research_first_run",
        },
    )

    assert first_run_response.status_code == 200
    assert first_run_response.json()["wasCreated"] is False
    assert first_run_response.json()["id"] == manual_response.json()["id"]
    assert first_run_response.json()["jobType"] == "query_research_first_run"
    assert first_run_response.json()["status"] == existing_status.value


@pytest.mark.parametrize("existing_status", [JobStatus.FAILED, JobStatus.CANCELLED])
def test_first_run_does_not_promote_a_terminal_manual_daily_slot(
    existing_status: JobStatus,
) -> None:
    client, store, query_id = _client_with_query()
    platform_id = str(uuid4())
    manual_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T00:00:00Z",
            "jobType": "manual_run",
        },
    )
    store.jobs[UUID(manual_response.json()["id"])].status = existing_status

    first_run_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T08:00:00+08:00",
            "jobType": "query_research_first_run",
        },
    )

    assert first_run_response.status_code == 200
    assert first_run_response.json()["wasCreated"] is False
    assert first_run_response.json()["jobType"] == "manual_run"
    assert first_run_response.json()["status"] == existing_status.value


def test_job_daily_slot_uses_the_taipei_business_date() -> None:
    client, _, query_id = _client_with_query()
    platform_id = str(uuid4())

    before_midnight = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T15:59:59Z",
        },
    )
    after_midnight = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T16:00:00Z",
        },
    )

    assert before_midnight.status_code == 201
    assert after_midnight.status_code == 201
    assert before_midnight.json()["id"] != after_midnight.json()["id"]


def test_overview_endpoints_return_stable_empty_read_models() -> None:
    client = _client()
    project = client.post("/api/geo/projects", json={"name": "Overview Project"})
    project_id = project.json()["id"]
    params = {
        "periodStart": "2026-07-01T00:00:00Z",
        "periodEnd": "2026-07-08T00:00:00Z",
        "timeZone": "Asia/Taipei",
    }

    report = client.get(
        f"/api/geo/projects/{project_id}/reports/overview",
        params=params,
    )
    responses = client.get(
        f"/api/geo/projects/{project_id}/reports/overview/responses",
        params=params,
    )

    assert report.status_code == 200
    assert report.json()["isPreparing"] is False
    assert report.json()["filterOptions"]["topics"] == []
    assert report.json()["topics"] == []
    assert [
        group["intentCategory"] for group in report.json()["intentGroups"]
    ] == [
        "navigational",
        "informational",
        "commercial_investigation",
        "transactional",
        "unclassified",
    ]
    assert all(
        group["queries"] == []
        and group["visibilityPercent"] == 0
        and group["sovPercent"] == 0
        and group["citationCount"] == 0
        for group in report.json()["intentGroups"]
    )
    assert report.json()["citationSummary"]["citationCount"] == 0
    assert responses.status_code == 200
    assert responses.json() == {"items": [], "total": 0, "page": 1, "pageSize": 20}


def test_overview_rejects_invalid_time_zone() -> None:
    client = _client()
    project = client.post("/api/geo/projects", json={"name": "Overview Project"})

    response = client.get(
        f"/api/geo/projects/{project.json()['id']}/reports/overview",
        params={
            "periodStart": "2026-07-01T00:00:00Z",
            "periodEnd": "2026-07-08T00:00:00Z",
            "timeZone": "Mars/Olympus",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize(
    "invalid_params",
    [
        {"mentionStatus": "unknown"},
        {"page": 0},
        {"pageSize": 101},
    ],
)
def test_overview_responses_preserve_problem_details_for_invalid_query_params(
    invalid_params: dict[str, object],
) -> None:
    client = _client()
    project = client.post("/api/geo/projects", json={"name": "Overview Project"})
    params = {
        "periodStart": "2026-07-01T00:00:00Z",
        "periodEnd": "2026-07-08T00:00:00Z",
        **invalid_params,
    }

    response = client.get(
        f"/api/geo/projects/{project.json()['id']}/reports/overview/responses",
        params=params,
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize(
    "status",
    [
        JobStatus.PENDING,
        JobStatus.PUBLISHING,
        JobStatus.PUBLISHED,
        JobStatus.RUNNING_EXTERNAL,
        JobStatus.DELAYED,
    ],
)
def test_overview_reports_current_taipei_day_preparing_jobs(status: JobStatus) -> None:
    clock = FakeClock(datetime(2026, 7, 27, 15, 59, tzinfo=UTC))
    client, store, query_id = _client_with_query(clock=clock)
    project_id = store.queries[UUID(query_id)].project_id
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": str(uuid4()),
            "scheduledFor": "2026-07-26T16:00:00Z",
        },
    )
    store.jobs[UUID(job_response.json()["id"])].status = status

    report = client.get(
        f"/api/geo/projects/{project_id}/reports/overview",
        params={
            "periodStart": "2026-07-01T00:00:00Z",
            "periodEnd": "2026-07-08T00:00:00Z",
        },
    )

    assert report.status_code == 200
    assert report.json()["isPreparing"] is True


@pytest.mark.parametrize(
    "status",
    [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED],
)
def test_overview_ignores_terminal_jobs(status: JobStatus) -> None:
    clock = FakeClock(datetime(2026, 7, 27, 15, 59, tzinfo=UTC))
    client, store, query_id = _client_with_query(clock=clock)
    project_id = store.queries[UUID(query_id)].project_id
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(uuid4())},
    )
    store.jobs[UUID(job_response.json()["id"])].status = status

    report = client.get(
        f"/api/geo/projects/{project_id}/reports/overview",
        params={
            "periodStart": "2026-07-01T00:00:00Z",
            "periodEnd": "2026-07-08T00:00:00Z",
        },
    )

    assert report.status_code == 200
    assert report.json()["isPreparing"] is False


def test_overview_uses_taipei_business_date_at_utc_boundary() -> None:
    clock = FakeClock(datetime(2026, 7, 27, 15, 59, tzinfo=UTC))
    client, store, query_id = _client_with_query(clock=clock)
    project_id = store.queries[UUID(query_id)].project_id
    client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": str(uuid4()),
            "scheduledFor": "2026-07-26T16:00:00Z",
        },
    )
    params = {
        "periodStart": "2026-07-01T00:00:00Z",
        "periodEnd": "2026-07-08T00:00:00Z",
    }

    before_midnight = client.get(
        f"/api/geo/projects/{project_id}/reports/overview",
        params=params,
    )
    clock.current = datetime(2026, 7, 27, 16, tzinfo=UTC)
    after_midnight = client.get(
        f"/api/geo/projects/{project_id}/reports/overview",
        params=params,
    )

    assert before_midnight.json()["isPreparing"] is True
    assert after_midnight.json()["isPreparing"] is False


def test_overview_ignores_historical_non_owner_jobs() -> None:
    clock = FakeClock(datetime(2026, 7, 27, 8, tzinfo=UTC))
    client, store, query_id = _client_with_query(clock=clock)
    project_id = store.queries[UUID(query_id)].project_id
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(uuid4())},
    )
    store.non_daily_slot_owner_job_ids.add(UUID(job_response.json()["id"]))

    report = client.get(
        f"/api/geo/projects/{project_id}/reports/overview",
        params={
            "periodStart": "2026-07-01T00:00:00Z",
            "periodEnd": "2026-07-08T00:00:00Z",
        },
    )

    assert report.status_code == 200
    assert report.json()["isPreparing"] is False


def _client(**kwargs) -> TestClient:
    return TestClient(
        create_app(
            authorizer=kwargs.pop("authorizer", FakeAuthorizer()),
            reference_verifier=kwargs.pop(
                "reference_verifier", FakeReferenceVerifier()
            ),
            **kwargs,
        ),
        headers=AUTH_HEADERS,
    )


def _client_with_job(**kwargs) -> tuple[TestClient, GeoApiStore, UUID]:
    client, store, query_id = _client_with_query(**kwargs)
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(uuid4())},
    )
    assert job_response.status_code == 201
    return client, store, UUID(job_response.json()["id"])


def _client_with_query(
    *,
    publisher=None,
    callback_base_url: str | None = None,
    market_type: str | None = None,
    repository: GeoApiStore | None = None,
    kmindhub_client=None,
    clock=None,
) -> tuple[TestClient, GeoApiStore, str]:
    store = repository or GeoApiStore()
    client = _client(
        repository=store,
        publisher=publisher,
        callback_base_url=callback_base_url,
        clock=clock,
        **({"kmindhub_client": kmindhub_client} if kmindhub_client is not None else {}),
    )
    project_response = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(uuid4()),
            "name": "Acme GEO",
            "defaultRegion": "US",
            "defaultLanguage": "en-US",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    query_response = client.post(
        f"/api/geo/projects/{project_id}/queries",
        json={
            "queryText": "Who are reliable O-ring suppliers in Taiwan?",
            "region": "US",
            "language": "en-US",
            **({"marketType": market_type} if market_type is not None else {}),
        },
    )
    assert query_response.status_code == 201
    return client, store, query_response.json()["id"]


def _invalid_param_names(body: dict) -> set[str]:
    return {item["name"] for item in body["invalidParams"]}


def _metric(
    metrics: list[dict],
    metric_name: str,
    scope_type: str,
    scope_value: str | None = None,
) -> dict:
    for metric in metrics:
        if (
            metric["metricName"] == metric_name
            and metric["scopeType"] == scope_type
            and metric["scopeValue"] == scope_value
        ):
            return metric
    raise AssertionError(f"metric not found: {metric_name} {scope_type} {scope_value}")


def _create_project(client: TestClient) -> str:
    response = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(uuid4()),
            "name": "Acme GEO",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _query_settings_payload() -> dict:
    return {
        "researchProvider": "gemini",
        "runProvider": "gemini",
        "keywords": [" ERP ", "erp", "", "採購"],
        "marketType": "b2b_procurement",
        "maxQueries": 20,
        "audience": {
            "name": "採購主管",
            "description": "負責供應商評估",
        },
        "intents": [
            {"category": "commercial", "description": "比較供應商"},
            {"category": "交易型", "description": "尋找購買或洽詢方式"},
        ],
        "shouldMentionOwnBrand": True,
        "shouldMentionCompetitor": False,
    }


def _create_project_setup_resources(
    client: TestClient,
    name: str,
    *,
    customer_id: UUID | None = None,
) -> dict[str, str]:
    project_response = client.post(
        "/api/geo/projects",
        json={
            **({"customerId": str(customer_id)} if customer_id else {}),
            "name": name,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    entity_response = client.post(
        f"/api/geo/projects/{project_id}/entities",
        json={"entityType": "own_brand", "name": f"{name} Entity"},
    )
    assert entity_response.status_code == 201
    alias_response = client.put(
        f"/api/geo/entities/{entity_response.json()['id']}/aliases",
        json={"items": [{"alias": f"{name} Alias"}]},
    )
    assert alias_response.status_code == 200
    query_response = client.post(
        f"/api/geo/projects/{project_id}/queries",
        json={
            "queryText": f"What is {name}?",
            "region": "TW",
            "language": "zh-TW",
        },
    )
    assert query_response.status_code == 201
    query_id = query_response.json()["id"]
    platform_id = uuid4()
    platform_response = client.put(
        f"/api/geo/queries/{query_id}/platforms",
        json=[{"platformId": str(platform_id)}],
    )
    assert platform_response.status_code == 200
    schedule_response = client.post(
        f"/api/geo/queries/{query_id}/schedules",
        json={"platformId": str(platform_id), "frequency": "daily"},
    )
    assert schedule_response.status_code == 201
    return {
        "project_id": project_id,
        "alias_id": alias_response.json()["items"][0]["id"],
        "query_platform_id": platform_response.json()["items"][0]["id"],
        "schedule_id": schedule_response.json()["id"],
    }


def _create_query_for_customer(client: TestClient, customer_id: UUID) -> str:
    project_response = client.post(
        "/api/geo/projects",
        json={"customerId": str(customer_id), "name": f"GEO {customer_id}"},
    )
    assert project_response.status_code == 201
    query_response = client.post(
        f"/api/geo/projects/{project_response.json()['id']}/queries",
        json={
            "queryText": "Who are reliable suppliers?",
            "region": "TW",
            "language": "zh-TW",
        },
    )
    assert query_response.status_code == 201
    return query_response.json()["id"]


def _query_research_payload() -> dict:
    return {
        "provider": "gemini",
        "brandName": "Acme",
        "competitorBrands": ["Beta"],
        "keywords": ["erp"],
        "region": "TW",
        "language": "zh-TW",
        "marketType": "b2b_procurement",
        "audience": {"name": "採購", "description": "B2B 採購人員"},
        "brandMentionRules": {
            "shouldMentionOwnBrand": True,
            "shouldMentionCompetitor": True,
        },
    }


def _add_run_result(store: GeoApiStore, job_id: UUID) -> UUID:
    job = store.jobs[job_id]
    now = datetime(2026, 6, 25, tzinfo=UTC)
    result_id = uuid4()
    reference = GeoRunResultReferenceRecord(
        id=uuid4(),
        run_result_id=result_id,
        url="https://example.com/reference",
        title="Example reference",
        domain="example.com",
        position=1,
    )
    store.run_results[result_id] = GeoRunResultRecord(
        id=result_id,
        run_request_id=uuid4(),
        job_id=job_id,
        tracking_result_id="tracking-result-1",
        query_id=job.query_id,
        provider="gemini",
        surface="Gemini",
        model="gemini-2.5-flash",
        region="TW",
        language="zh-TW",
        status="completed",
        raw_response="Raw answer",
        error=None,
        run_at=now,
        references=[reference],
        created_at=now,
    )
    return result_id


@dataclass
class FakePublisher:
    messages: list[QueryRunJobMessage] = field(default_factory=list)
    closed: bool = False

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        self.messages.append(message)
        return PublishResult(
            backend="fake",
            destination=f"geo.query-runs.{message.platform}",
            message_id="message-1",
            status="published",
        )

    async def close(self) -> None:
        self.closed = True


@dataclass
class FakeKMindHubClient:
    created_workspace_id: UUID = field(default_factory=uuid4)
    created_display_names: list[str] = field(default_factory=list)
    created_task_ids: list[UUID] = field(default_factory=list)
    preview_texts: list[str] = field(default_factory=list)
    committed_items: list[list[dict]] = field(default_factory=list)

    async def create_workspace(self, display_name: str) -> UUID:
        self.created_display_names.append(display_name)
        return self.created_workspace_id

    def workspace_headers(self, workspace_id: UUID) -> dict[str, str]:
        return {"X-Workspace-Id": str(workspace_id)}

    async def create_extraction_task(self, *, workspace_id, definition) -> UUID:
        task_id = uuid4()
        self.created_task_ids.append(task_id)
        return task_id

    async def preview_text_extraction(self, *, workspace_id, task_id, text):
        self.preview_texts.append(text)
        return KMindHubExtractionPreviewResult(
            task_id=task_id,
            items=[
                KMindHubExtractionPreviewItem(
                    fields={
                        "summary": KMindHubExtractionFieldValue(value="Raw answer"),
                        "overallSentiment": KMindHubExtractionFieldValue(
                            value="neutral"
                        ),
                        "theme": KMindHubExtractionFieldValue(value="供應商比較"),
                        "entityName": KMindHubExtractionFieldValue(value="Acme"),
                        "entityType": KMindHubExtractionFieldValue(value="own_brand"),
                        "mentionCount": KMindHubExtractionFieldValue(value=1),
                        "statementText": KMindHubExtractionFieldValue(
                            value="Raw answer"
                        ),
                        "statementSentiment": KMindHubExtractionFieldValue(
                            value="neutral"
                        ),
                        "subjectEntityName": KMindHubExtractionFieldValue(value="Acme"),
                        "evidenceText": KMindHubExtractionFieldValue(
                            value="Raw answer"
                        ),
                    },
                    verification={"passed": True},
                )
            ],
        )

    async def commit_extraction_items(self, *, workspace_id, task_id, items):
        self.committed_items.append(items)
        return KMindHubExtractionCommitResult(
            commit_batch_id="commit-batch-1",
            item_ids=["item-1"],
        )


@dataclass
class FakeAuthorizer:
    tenant_id: UUID = TENANT_ID
    has_global_resource_access: bool = True
    customer_ids: frozenset[UUID] = frozenset()
    task_ids: frozenset[UUID] = frozenset()
    authentication_required: bool = False
    access_denied: bool = False

    async def require(self, access_token: str, permission: str) -> AuthorizedPrincipal:
        assert access_token == "test-token"
        if self.authentication_required:
            raise AuthenticationRequired
        if self.access_denied:
            raise PermissionError("access denied")
        return AuthorizedPrincipal(
            tenant_id=self.tenant_id,
            permissions=frozenset({permission}),
            has_global_resource_access=self.has_global_resource_access,
            customer_ids=self.customer_ids,
            task_ids=self.task_ids,
        )


@dataclass
class FakeReferenceVerifier:
    customer_id: UUID | None = None
    fixed_task_customer_id: UUID | None = None
    denied: bool = False
    unavailable: bool = False
    authentication_required: bool = False

    async def customer_exists(
        self,
        *,
        access_token: str,
        customer_id: UUID,
    ) -> bool:
        self._raise_if_configured()
        if self.fixed_task_customer_id is None:
            self.customer_id = customer_id
        return True

    async def get_task(
        self,
        *,
        access_token: str,
        task_id: UUID,
    ) -> ResourceTaskReference | None:
        self._raise_if_configured()
        return ResourceTaskReference(
            id=task_id,
            customer_id=self.fixed_task_customer_id or self.customer_id or uuid4(),
        )

    def _raise_if_configured(self) -> None:
        if self.authentication_required:
            raise AuthenticationRequired
        if self.denied:
            raise ResourceCatalogVerificationDenied(
                "resource catalog reference verification denied"
            )
        if self.unavailable:
            raise ResourceCatalogVerificationUnavailable("resource catalog unavailable")


@dataclass
class FakeCustomerReader:
    names: dict[UUID, str]
    requested_ids: set[UUID] = field(default_factory=set)
    unavailable: bool = False

    async def list_customer_names(
        self,
        *,
        access_token: str,
        customer_ids: frozenset[UUID],
    ) -> dict[UUID, str]:
        assert access_token == "test-token"
        if self.unavailable:
            raise ResourceCatalogVerificationUnavailable("resource catalog unavailable")
        self.requested_ids.update(customer_ids)
        return {
            customer_id: self.names[customer_id]
            for customer_id in customer_ids
            if customer_id in self.names
        }


class FakePlanningClient:
    async def research(self, command) -> dict:
        return {
            "researchContext": "研究摘要",
            "searchedKeywords": command.keywords,
            "sourceUrls": ["https://example.com/source"],
        }

    async def generate(self, command) -> dict:
        return {
            "topics": [],
            "queries": [
                {
                    "id": str(uuid4()),
                    "queryText": "Acme ERP 適合哪些 B2B 採購情境?",
                    "keywords": command.keywords,
                    "topicId": None,
                    "topicName": "ERP 導入",
                    "region": command.region,
                    "language": command.language or "zh-TW",
                    "marketType": command.market_type,
                    "isBranded": True,
                    "attributes": {
                        "intent": {
                            "category": "commercial",
                            "description": "比較供應商",
                        },
                        "topicName": "ERP 導入",
                    },
                    "metadata": {"source": "fake"},
                    "source": "generated",
                    "status": "draft",
                }
            ],
        }
