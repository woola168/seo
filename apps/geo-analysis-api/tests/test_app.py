from datetime import datetime, timezone
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from younilab_geo_analysis_api.presentation.http import create_app
from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import (
    GeoRunResultRecord,
    GeoRunResultReferenceRecord,
    PublishResult,
    QueryRunJobMessage,
)
from younilab_seo.geo_analysis.domain import JobStatus


def test_project_topic_query_and_job_crud_flow() -> None:
    client = TestClient(create_app())

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


def test_validation_error_returns_problem_details() -> None:
    client = TestClient(create_app())

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
    client = TestClient(create_app())

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


def test_query_research_generation_and_draft_accept_flow() -> None:
    planning_client = FakePlanningClient()
    client = TestClient(create_app(planning_client=planning_client))
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
    client = TestClient(create_app(planning_client=FakePlanningClient()))
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
    client = TestClient(create_app(planning_client=FakePlanningClient()))
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
    client = TestClient(create_app())

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
    client = TestClient(create_app())

    response = client.get(f"/api/geo/run-results/{uuid4()}")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "run result not found"


def test_app_lifespan_closes_injected_publisher() -> None:
    publisher = FakePublisher()
    store = GeoApiStore()

    with TestClient(create_app(repository=store, publisher=publisher)) as client:
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
    client = TestClient(
        create_app(
            repository=store,
            publisher=publisher,
            callback_base_url=callback_base_url,
        )
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
