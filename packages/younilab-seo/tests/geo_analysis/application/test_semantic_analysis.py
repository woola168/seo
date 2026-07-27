import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from younilab_seo.geo_analysis.application import (
    AnalyzeGeoRunResultCommand,
    AnalyzeRunResult,
    GeoEntityMentionFact,
    GeoEntityRecord,
    GeoQueryRecord,
    GeoResponseSemanticFact,
    GeoRunResultAnalysis,
    GeoRunResultEntityDetection,
    GeoRunResultRecord,
    GeoSentimentFact,
    GeoTopicRecord,
    KMindHubExtractionValidationError,
    RunResultSemanticAnalysisNotFound,
    SaveRunResultEntityDetectionCommand,
    SaveSemanticRunResultAnalysisCommand,
)
from younilab_seo.geo_analysis.application.entity_mention_detection import (
    ENTITY_MENTION_DETECTOR_VERSION,
)
from younilab_seo.geo_analysis.application.interfaces.semantic_analysis import (
    SemanticAnalysisContext,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 7, 5, tzinfo=UTC)
_DEFAULT = object()


@dataclass
class FakeClock:
    current: datetime = NOW

    def now(self) -> datetime:
        return self.current


@dataclass
class FakeRepository:
    result: GeoRunResultRecord | None = None
    query: GeoQueryRecord | None = None
    topics: list[GeoTopicRecord] = field(default_factory=list)
    entities: list[GeoEntityRecord] = field(default_factory=list)
    semantic_analysis: GeoRunResultAnalysis | None = None
    saved_commands: list[SaveSemanticRunResultAnalysisCommand] = field(
        default_factory=list
    )
    detection: GeoRunResultEntityDetection | None = None
    saved_detections: list[SaveRunResultEntityDetectionCommand] = field(
        default_factory=list
    )
    save_returns_none: bool = False

    async def load_semantic_analysis_context(self, tenant_id, result_id):
        result = await self.get_run_result(tenant_id, result_id)
        if result is None:
            return None
        query = await self.get_query(tenant_id, result.query_id)
        if query is None:
            return SemanticAnalysisContext(run_result=result)
        active_entities = [
            entity
            for entity in await self.list_entities(tenant_id, query.project_id)
            if entity.status == "active"
            and entity.entity_type in {"own_brand", "competitor"}
        ]
        topic = next(
            (
                item
                for item in await self.list_topics(tenant_id, query.project_id)
                if item.id == query.topic_id and item.status == "active"
            ),
            None,
        )
        return SemanticAnalysisContext(
            run_result=result,
            query=query,
            topic=topic,
            own_brand=next(
                (item for item in active_entities if item.entity_type == "own_brand"),
                None,
            ),
            competitors=tuple(
                item for item in active_entities if item.entity_type == "competitor"
            ),
        )

    async def get_existing_semantic_analysis(self, tenant_id, result_id):
        return await self.get_semantic_run_result_analysis(tenant_id, result_id)

    async def save_semantic_entity_detection(
        self,
        tenant_id,
        command,
        occurred_at,
    ):
        return await self.save_run_result_entity_detection(
            tenant_id,
            command,
            occurred_at,
        )

    async def save_semantic_analysis(self, tenant_id, command, occurred_at):
        return await self.save_semantic_run_result_analysis(
            tenant_id,
            command,
            occurred_at,
        )

    async def get_run_result(self, tenant_id, result_id):
        if (
            tenant_id == TENANT_ID
            and self.result is not None
            and result_id == self.result.id
        ):
            return self.result
        return None

    async def get_query(self, tenant_id, query_id):
        if (
            tenant_id == TENANT_ID
            and self.query is not None
            and query_id == self.query.id
        ):
            return self.query
        return None

    async def list_topics(self, tenant_id, project_id):
        return [
            topic
            for topic in self.topics
            if tenant_id == TENANT_ID and topic.project_id == project_id
        ]

    async def list_entities(self, tenant_id, project_id):
        return [
            entity
            for entity in self.entities
            if tenant_id == TENANT_ID and entity.project_id == project_id
        ]

    async def list_project_aliases(self, tenant_id, project_id):
        return []

    async def save_run_result_entity_detection(
        self,
        tenant_id,
        command: SaveRunResultEntityDetectionCommand,
        occurred_at,
    ):
        if tenant_id != TENANT_ID:
            return None
        self.saved_detections.append(command)
        self.detection = command.detection
        return command.detection

    async def get_semantic_run_result_analysis(self, tenant_id, result_id):
        if (
            tenant_id == TENANT_ID
            and self.semantic_analysis is not None
            and result_id == self.semantic_analysis.run_result_id
        ):
            return self.semantic_analysis
        return None

    async def save_semantic_run_result_analysis(
        self,
        tenant_id,
        command: SaveSemanticRunResultAnalysisCommand,
        occurred_at,
    ):
        if tenant_id != TENANT_ID or self.save_returns_none:
            return None
        self.saved_commands.append(command)
        self.semantic_analysis = command.analysis
        if self.detection is None or self.detection.status != "completed":
            return command.analysis
        return command.analysis.model_copy(
            update={
                "entity_mentions": [
                    GeoEntityMentionFact(
                        entity_id=item.entity_id,
                        entity_role=item.entity_role,
                        entity_name=item.entity_name,
                        mentioned=item.mentioned,
                        first_mention_order=item.first_mention_order,
                        evidence_text=item.evidence_text,
                    )
                    for item in self.detection.items
                ]
            }
        )


@dataclass
class FakeAnalyzer:
    result: GeoRunResultAnalysis | None = None
    error: Exception | None = None
    commands: list[AnalyzeGeoRunResultCommand] = field(default_factory=list)

    async def analyze(
        self, command: AnalyzeGeoRunResultCommand
    ) -> GeoRunResultAnalysis:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result
        return GeoRunResultAnalysis(
            run_result_id=command.run_result_id,
            analyzer="fake_analyzer",
            analyzer_version="test",
            status="completed",
            sentiments=[
                GeoSentimentFact(
                    entity_id=command.entities.own_brand.entity_id,
                    entity_role="own_brand",
                    entity_name=command.entities.own_brand.name,
                    sentiment="positive",
                    theme="fit",
                    statement="Acme ERP 適合製造業。",
                    evidence_text="適合製造業",
                    confidence=0.8,
                )
            ],
            semantic_facts=[
                GeoResponseSemanticFact(
                    fact_type="product",
                    value="ERP",
                    evidence_text="Acme ERP",
                    confidence=0.7,
                )
            ],
        )


@dataclass
class MinimalSemanticAnalysisPersistence:
    context: SemanticAnalysisContext
    semantic_analysis: GeoRunResultAnalysis | None = None
    detection: GeoRunResultEntityDetection | None = None
    saved_commands: list[SaveSemanticRunResultAnalysisCommand] = field(
        default_factory=list
    )
    saved_detections: list[SaveRunResultEntityDetectionCommand] = field(
        default_factory=list
    )

    async def load_semantic_analysis_context(self, tenant_id, run_result_id):
        if tenant_id == TENANT_ID and run_result_id == self.context.run_result.id:
            return self.context
        return None

    async def get_existing_semantic_analysis(self, tenant_id, run_result_id):
        if tenant_id == TENANT_ID and (
            self.semantic_analysis is None
            or self.semantic_analysis.run_result_id == run_result_id
        ):
            return self.semantic_analysis
        return None

    async def save_semantic_entity_detection(
        self,
        tenant_id,
        command,
        occurred_at,
    ):
        if tenant_id != TENANT_ID:
            return None
        self.saved_detections.append(command)
        self.detection = command.detection
        return command.detection

    async def save_semantic_analysis(self, tenant_id, command, occurred_at):
        if tenant_id != TENANT_ID:
            return None
        self.saved_commands.append(command)
        self.semantic_analysis = command.analysis
        if self.detection is None or self.detection.status != "completed":
            return command.analysis
        return command.analysis.model_copy(
            update={
                "entity_mentions": [
                    GeoEntityMentionFact(
                        entity_id=item.entity_id,
                        entity_role=item.entity_role,
                        entity_name=item.entity_name,
                        mentioned=item.mentioned,
                        first_mention_order=item.first_mention_order,
                        evidence_text=item.evidence_text,
                    )
                    for item in self.detection.items
                ]
            }
        )


def test_analyze_run_result_uses_semantic_analysis_persistence_interface() -> None:
    async def run() -> None:
        repository = _repository()
        persistence = MinimalSemanticAnalysisPersistence(
            SemanticAnalysisContext(
                run_result=repository.result,
                query=repository.query,
                topic=repository.topics[0],
                own_brand=repository.entities[0],
                competitors=(repository.entities[1],),
            )
        )
        analyzer = FakeAnalyzer()

        result = await AnalyzeRunResult(
            persistence,
            analyzer,
            FakeClock(),
        ).execute(TENANT_ID, repository.result.id)

        assert result.status == "completed"
        assert result.entity_mentions[0].entity_name == "Acme"
        assert analyzer.commands[0].entities.own_brand.name == "Acme"

    asyncio.run(run())


def test_analyze_run_result_saves_completed_semantic_facts() -> None:
    async def run() -> None:
        project_id = uuid4()
        topic_id = uuid4()
        repository = _repository(project_id=project_id, topic_id=topic_id)
        analyzer = FakeAnalyzer()

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "completed"
        assert result.entity_mentions[0].entity_name == "Acme"
        assert result.sentiments[0].sentiment == "positive"
        assert result.semantic_facts[0].value == "ERP"
        assert repository.saved_commands[-1].analysis.entity_mentions == []
        assert repository.saved_detections[-1].detection.status == "completed"
        assert analyzer.commands[0].tenant_id == TENANT_ID
        assert analyzer.commands[0].project_id == project_id
        assert analyzer.commands[0].topic_id == topic_id
        assert analyzer.commands[0].entities.own_brand.name == "Acme"
        assert [item.name for item in analyzer.commands[0].entities.competitors] == [
            "Beta"
        ]

    asyncio.run(run())


def test_analyze_run_result_returns_existing_analysis_without_force() -> None:
    async def run() -> None:
        repository = _repository()
        existing = GeoRunResultAnalysis(
            run_result_id=repository.result.id,
            analyzer="existing",
            status="completed",
        )
        repository.semantic_analysis = existing
        analyzer = FakeAnalyzer()

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result == existing
        assert analyzer.commands == []
        assert repository.saved_commands == []

    asyncio.run(run())


def test_analyze_run_result_force_reanalyze_overwrites_existing_analysis() -> None:
    async def run() -> None:
        repository = _repository()
        repository.semantic_analysis = GeoRunResultAnalysis(
            run_result_id=repository.result.id,
            analyzer="existing",
            status="completed",
        )
        analyzer = FakeAnalyzer(
            result=GeoRunResultAnalysis(
                run_result_id=repository.result.id,
                analyzer="fake_analyzer",
                analyzer_version="rerun",
                status="completed",
                semantic_facts=[
                    GeoResponseSemanticFact(fact_type="service", value="導入顧問")
                ],
            )
        )

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
            force_reanalyze=True,
        )

        assert result.analyzer_version == "rerun"
        assert [fact.value for fact in result.semantic_facts] == ["導入顧問"]
        assert len(analyzer.commands) == 1
        assert repository.saved_commands[-1].analysis.entity_mentions == []

    asyncio.run(run())


def test_analyze_run_result_omits_inactive_or_missing_topic_context() -> None:
    async def run() -> None:
        project_id = uuid4()
        topic_id = uuid4()
        missing_topic_repository = _repository(
            project_id=project_id,
            topic_id=topic_id,
        )
        missing_topic_repository.topics = []
        inactive_topic_repository = _repository(
            project_id=project_id,
            topic_id=topic_id,
            topics=[
                _topic(topic_id, project_id).model_copy(update={"status": "archived"})
            ],
        )

        missing_topic_analyzer = FakeAnalyzer()
        inactive_topic_analyzer = FakeAnalyzer()
        await AnalyzeRunResult(
            missing_topic_repository,
            missing_topic_analyzer,
            FakeClock(),
        ).execute(TENANT_ID, missing_topic_repository.result.id)
        await AnalyzeRunResult(
            inactive_topic_repository,
            inactive_topic_analyzer,
            FakeClock(),
        ).execute(TENANT_ID, inactive_topic_repository.result.id)

        assert missing_topic_analyzer.commands[0].topic_id is None
        assert missing_topic_analyzer.commands[0].topic_name is None
        assert missing_topic_analyzer.commands[0].topic_description is None
        assert inactive_topic_analyzer.commands[0].topic_id is None
        assert inactive_topic_analyzer.commands[0].topic_name is None
        assert inactive_topic_analyzer.commands[0].topic_description is None

    asyncio.run(run())


def test_analyze_run_result_saves_failed_for_failed_raw_result() -> None:
    async def run() -> None:
        repository = _repository(result=_run_result(status="failed"))
        analyzer = FakeAnalyzer()

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "failed"
        assert result.error_code == "run_result_not_analyzable"
        assert analyzer.commands == []

    asyncio.run(run())


def test_analyze_run_result_saves_failed_for_empty_raw_response() -> None:
    async def run() -> None:
        repository = _repository(result=_run_result(raw_response=" "))
        analyzer = FakeAnalyzer()

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "failed"
        assert result.error_code == "run_result_not_analyzable"
        assert analyzer.commands == []

    asyncio.run(run())


def test_analyze_run_result_saves_failed_when_own_brand_missing() -> None:
    async def run() -> None:
        repository = _repository(entities=[_competitor(uuid4())])
        analyzer = FakeAnalyzer()

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "failed"
        assert result.error_code == "own_brand_missing"
        assert analyzer.commands == []

    asyncio.run(run())


def test_analyze_run_result_saves_failed_on_analyzer_exception() -> None:
    async def run() -> None:
        repository = _repository()
        analyzer = FakeAnalyzer(error=TimeoutError("semantic timeout"))

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "failed"
        assert result.error_code == "TimeoutError"
        assert result.error_message == "semantic timeout"
        assert result.entity_mentions[0].entity_name == "Acme"
        assert repository.saved_detections[-1].detection.status == "completed"

    asyncio.run(run())


def test_analyze_run_result_continues_when_entity_detection_fails(monkeypatch) -> None:
    async def run() -> None:
        repository = _repository()
        analyzer = FakeAnalyzer()

        def fail_detection(**kwargs):
            raise RuntimeError("detector failed")

        monkeypatch.setattr(
            "younilab_seo.geo_analysis.application.use_cases.semantic_analysis.detect_entity_mentions",
            fail_detection,
        )
        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "completed"
        assert result.entity_mentions == []
        assert len(analyzer.commands) == 1
        assert repository.saved_detections[-1].detection.status == "failed"
        assert repository.saved_detections[-1].detection.error_code == "RuntimeError"
        assert (
            repository.saved_detections[-1].detection.detector_version
            == ENTITY_MENTION_DETECTOR_VERSION
        )

    asyncio.run(run())


def test_analyze_run_result_saves_kmindhub_validation_diagnostics() -> None:
    async def run() -> None:
        repository = _repository()
        error = KMindHubExtractionValidationError(
            "KMindHub preview verification failed",
            request_payload={"body": {"taskId": "task-1", "text": "answer"}},
            response_payload={"items": [{"verification": {"passed": False}}]},
            validation_failures=[
                {
                    "itemIndex": 0,
                    "fieldName": "evidenceText",
                    "kind": "evidence",
                    "code": "unsupportedBySource",
                    "reason": "not supported",
                }
            ],
        )

        result = await AnalyzeRunResult(
            repository,
            FakeAnalyzer(error=error),
            FakeClock(),
        ).execute(TENANT_ID, repository.result.id)

        assert result.status == "failed"
        assert result.analyzer_request_payload == error.request_payload
        assert result.analyzer_response_payload == error.response_payload
        assert result.validation_failures == error.validation_failures

    asyncio.run(run())


def test_analyze_run_result_raises_when_run_result_not_found() -> None:
    async def run() -> None:
        repository = _repository(result=None)

        with pytest.raises(RunResultSemanticAnalysisNotFound):
            await AnalyzeRunResult(repository, FakeAnalyzer(), FakeClock()).execute(
                TENANT_ID,
                uuid4(),
            )

    asyncio.run(run())


def test_analyze_run_result_raises_when_semantic_save_returns_none() -> None:
    async def run() -> None:
        repository = _repository()
        repository.save_returns_none = True

        with pytest.raises(RunResultSemanticAnalysisNotFound):
            await AnalyzeRunResult(repository, FakeAnalyzer(), FakeClock()).execute(
                TENANT_ID,
                repository.result.id,
            )

    asyncio.run(run())


def test_analyze_run_result_saves_failed_when_query_context_missing() -> None:
    async def run() -> None:
        repository = _repository(query=None)
        analyzer = FakeAnalyzer()

        result = await AnalyzeRunResult(repository, analyzer, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "failed"
        assert result.error_code == "query_context_missing"
        assert analyzer.commands == []

    asyncio.run(run())


def _repository(
    *,
    project_id: UUID | None = None,
    topic_id: UUID | None = None,
    result: GeoRunResultRecord | None | object = _DEFAULT,
    query: GeoQueryRecord | None | object = _DEFAULT,
    topics: list[GeoTopicRecord] | None = None,
    entities: list[GeoEntityRecord] | None = None,
) -> FakeRepository:
    project_id = project_id or uuid4()
    topic_id = topic_id or uuid4()
    result = _run_result() if result is _DEFAULT else result
    if query is _DEFAULT:
        query = (
            _query(result.query_id, project_id, topic_id)
            if result is not None
            else None
        )
    return FakeRepository(
        result=result,
        query=query,
        topics=topics if topics is not None else [_topic(topic_id, project_id)],
        entities=entities
        if entities is not None
        else [
            _own_brand(project_id),
            _competitor(project_id),
            _archived_competitor(project_id),
        ],
    )


def _run_result(
    *,
    status: str = "completed",
    raw_response: str = "Acme ERP 適合製造業。",
) -> GeoRunResultRecord:
    return GeoRunResultRecord(
        id=uuid4(),
        run_request_id=uuid4(),
        job_id=uuid4(),
        tracking_result_id="tracking-result-1",
        query_id=uuid4(),
        provider="gemini",
        surface="ai_overview",
        model="gemini-2.5-pro",
        region="TW",
        language="zh-TW",
        status=status,
        raw_response=raw_response,
        run_at=NOW,
        created_at=NOW,
    )


def _query(
    query_id: UUID,
    project_id: UUID,
    topic_id: UUID | None,
) -> GeoQueryRecord:
    return GeoQueryRecord(
        id=query_id,
        project_id=project_id,
        topic_id=topic_id,
        query_text="哪個 ERP 適合製造業？",
        region="TW",
        language="zh-TW",
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )


def _topic(topic_id: UUID, project_id: UUID) -> GeoTopicRecord:
    return GeoTopicRecord(
        id=topic_id,
        project_id=project_id,
        name="ERP",
        description="企業資源規劃",
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )


def _own_brand(project_id: UUID) -> GeoEntityRecord:
    return GeoEntityRecord(
        id=uuid4(),
        project_id=project_id,
        entity_type="own_brand",
        name="Acme",
        website_url="https://acme.example",
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )


def _competitor(project_id: UUID) -> GeoEntityRecord:
    return GeoEntityRecord(
        id=uuid4(),
        project_id=project_id,
        entity_type="competitor",
        name="Beta",
        website_url="https://beta.example",
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )


def _archived_competitor(project_id: UUID) -> GeoEntityRecord:
    return GeoEntityRecord(
        id=uuid4(),
        project_id=project_id,
        entity_type="competitor",
        name="Archived",
        status="archived",
        created_at=NOW,
        updated_at=NOW,
    )
