from datetime import datetime, timezone
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from younilab_geo_analysis_api.presentation.http import create_app
from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import PublishResult, QueryRunJobMessage
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
    assert (
        message.callback_url
        == f"http://geo-analysis-api:8002/api/geo/jobs/{job_id}/external-callbacks"
    )


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
        },
    )
    assert query_response.status_code == 201
    return client, store, query_response.json()["id"]


def _invalid_param_names(body: dict) -> set[str]:
    return {item["name"] for item in body["invalidParams"]}


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
