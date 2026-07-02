from datetime import datetime, timezone
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from younilab_geo_analysis_api.presentation.http import create_app
from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import (
    AuthorizedPrincipal,
    GeoRunResultRecord,
    GeoRunResultReferenceRecord,
    PublishResult,
    QueryRunJobMessage,
    ResourceCatalogVerificationDenied,
    ResourceCatalogVerificationUnavailable,
    ResourceTaskReference,
)
from younilab_seo.geo_analysis.domain import JobStatus


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000002")
AUTH_HEADERS = {"Authorization": "Bearer test-token"}


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
    assert second_response.json()["detail"] == "KMindHub workspace mapping already exists"
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
    allowed_result_response = restricted.get(f"/api/geo/run-results/{allowed_result_id}")
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


def test_project_allows_empty_customer_reference_but_rejects_task_without_customer() -> None:
    client = _client()

    response = client.post("/api/geo/projects", json={"name": "Draft GEO"})

    assert response.status_code == 201
    assert response.json()["customerId"] is None
    assert response.json()["seoTaskId"] is None

    invalid = client.post(
        "/api/geo/projects",
        json={"name": "Broken GEO", "seoTaskId": str(uuid4())},
    )

    assert invalid.status_code == 422
    assert invalid.headers["content-type"] == "application/problem+json"
    assert invalid.json()["detail"] == "seoTaskId requires customerId"


def test_project_rejects_task_from_different_customer() -> None:
    client = _client(
        reference_verifier=FakeReferenceVerifier(fixed_task_customer_id=uuid4())
    )

    response = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(uuid4()),
            "seoTaskId": str(uuid4()),
            "name": "Broken GEO",
        },
    )

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "seoTaskId does not belong to customerId"


def test_project_reference_verification_denied_returns_forbidden() -> None:
    client = _client(reference_verifier=FakeReferenceVerifier(denied=True))

    response = client.post(
        "/api/geo/projects",
        json={"customerId": str(uuid4()), "name": "Denied GEO"},
    )

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "resource catalog reference verification denied"


def test_project_reference_verification_unavailable_returns_service_unavailable() -> None:
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
        json={"customerId": str(uuid4()), "seoTaskId": str(uuid4()), "name": "Acme GEO"},
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
            "intents": [{"category": "commercial", "description": "比較供應商"}],
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
    assert research_body["requestPayload"]["intents"][0]["category"] == "commercial"
    assert research_body["requestPayload"]["brandMentionRules"] == {
        "shouldMentionOwnBrand": True,
        "shouldMentionCompetitor": True,
    }

    generation_response = client.post(
        f"/api/geo/projects/{project_id}/query-generation-runs",
        json={
            "seoTaskId": project_response.json()["seoTaskId"],
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
        (
            "intents",
            [
                {"category": f"intent-{index}", "description": "比較供應商"}
                for index in range(9)
            ],
        ),
    ]

    for field, value in cases:
        payload = _query_research_payload()
        payload[field] = value
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
    assert message.seo_task_id is not None
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


def test_dispatch_without_project_seo_task_id_returns_conflict() -> None:
    publisher = FakePublisher()
    client, store, query_id = _client_with_query(publisher=publisher)
    query = store.queries[UUID(query_id)]
    store.projects[query.project_id].seo_task_id = None
    platform_id = uuid4()
    store.platform_codes[platform_id] = "gemini"
    job_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={"platformId": str(platform_id)},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    response = client.post(f"/api/geo/jobs/{job_id}/dispatch")

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "project seoTaskId is required to dispatch job"
    assert publisher.messages == []


def test_create_query_accepts_market_type() -> None:
    client, _, query_id = _client_with_query(market_type="b2c")

    response = client.get(f"/api/geo/queries/{query_id}")

    assert response.status_code == 200
    assert response.json()["marketType"] == "b2c"


def test_job_run_results_can_be_listed_and_loaded() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)

    list_response = client.get(f"/api/geo/jobs/{job_id}/run-results")
    detail_response = client.get(f"/api/geo/run-results/{result_id}")

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    item = list_response.json()["items"][0]
    assert item["id"] == str(result_id)
    assert item["rawResponse"] == "Raw answer"
    assert item["references"][0]["url"] == "https://example.com/reference"
    assert detail_response.status_code == 200
    assert detail_response.json()["references"][0]["domain"] == "example.com"


def test_project_run_results_are_scoped_to_project() -> None:
    client, store, job_id = _client_with_job()
    result_id = _add_run_result(store, job_id)
    project_id = store.jobs[job_id].project_id

    response = client.get(f"/api/geo/projects/{project_id}/run-results")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(result_id)]


def test_missing_run_result_returns_problem_details() -> None:
    client = _client()

    response = client.get(f"/api/geo/run-results/{uuid4()}")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "run result not found"


def test_app_lifespan_closes_injected_publisher() -> None:
    publisher = FakePublisher()
    store = GeoApiStore()

    with _client(repository=store, publisher=publisher) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert publisher.closed is True


def test_job_dedupe_key_uses_normalized_utc_seconds() -> None:
    client, _, query_id = _client_with_query()
    platform_id = str(uuid4())

    first_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T00:00:00.123456+00:00",
        },
    )
    second_response = client.post(
        f"/api/geo/queries/{query_id}/jobs",
        json={
            "platformId": platform_id,
            "scheduledFor": "2026-06-22T08:00:00.987654+08:00",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["dedupeKey"] == second_response.json()["dedupeKey"]
    assert (
        datetime.fromisoformat(first_response.json()["scheduledFor"])
        == datetime(2026, 6, 22, tzinfo=timezone.utc)
    )


def _client(**kwargs) -> TestClient:
    return TestClient(
        create_app(
            authorizer=kwargs.pop("authorizer", FakeAuthorizer()),
            reference_verifier=kwargs.pop("reference_verifier", FakeReferenceVerifier()),
            **kwargs,
        ),
        headers=AUTH_HEADERS,
    )


def _client_with_job() -> tuple[TestClient, GeoApiStore, UUID]:
    client, store, query_id = _client_with_query()
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
) -> tuple[TestClient, GeoApiStore, str]:
    store = GeoApiStore()
    client = _client(
        repository=store,
        publisher=publisher,
        callback_base_url=callback_base_url,
    )
    project_response = client.post(
        "/api/geo/projects",
        json={
            "customerId": str(uuid4()),
            "seoTaskId": str(uuid4()),
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


def _create_project(client: TestClient) -> str:
    response = client.post(
        "/api/geo/projects",
        json={"customerId": str(uuid4()), "seoTaskId": str(uuid4()), "name": "Acme GEO"},
    )
    assert response.status_code == 201
    return response.json()["id"]


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
        "intents": [{"category": "commercial", "description": "比較供應商"}],
        "audience": {"name": "採購", "description": "B2B 採購人員"},
        "brandMentionRules": {
            "shouldMentionOwnBrand": True,
            "shouldMentionCompetitor": True,
        },
    }


def _add_run_result(store: GeoApiStore, job_id: UUID) -> UUID:
    job = store.jobs[job_id]
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
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

    async def create_workspace(self, display_name: str) -> UUID:
        self.created_display_names.append(display_name)
        return self.created_workspace_id

    def workspace_headers(self, workspace_id: UUID) -> dict[str, str]:
        return {"X-Workspace-Id": str(workspace_id)}


@dataclass
class FakeAuthorizer:
    tenant_id: UUID = TENANT_ID
    has_global_resource_access: bool = True
    customer_ids: frozenset[UUID] = frozenset()
    task_ids: frozenset[UUID] = frozenset()

    async def require(self, access_token: str, permission: str) -> AuthorizedPrincipal:
        assert access_token == "test-token"
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
        if self.denied:
            raise ResourceCatalogVerificationDenied(
                "resource catalog reference verification denied"
            )
        if self.unavailable:
            raise ResourceCatalogVerificationUnavailable("resource catalog unavailable")


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
                    "seoTaskId": str(command.seo_task_id),
                    "queryText": "Acme ERP 適合哪些 B2B 採購情境?",
                    "keywords": command.keywords,
                    "topicId": None,
                    "topicName": "ERP 導入",
                    "region": command.region,
                    "language": command.language or "zh-TW",
                    "marketType": command.market_type,
                    "isBranded": True,
                    "attributes": {
                        "intent": {"category": "commercial", "description": "比較供應商"},
                        "topicName": "ERP 導入",
                    },
                    "metadata": {"source": "fake"},
                    "source": "generated",
                    "status": "draft",
                }
            ],
        }
