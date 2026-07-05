from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    AnalyzeGeoRunResultCommand,
    GeoAnalysisEntityContext,
    GeoAnalysisEntityInput,
    GeoEntityRecord,
    GeoRunResultAnalysis,
    SaveSemanticRunResultAnalysisCommand,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    GeoAnalysisRepository,
    GeoRunResultAnalyzer,
)


class RunResultSemanticAnalysisNotFound(LookupError):
    """找不到租戶可存取的 GEO run result，無法進行 semantic analysis。"""


@dataclass(frozen=True)
class AnalyzeRunResult:
    """將已保存的 raw run result 轉成 semantic facts 並保存分析結果。"""

    repository: GeoAnalysisRepository
    analyzer: GeoRunResultAnalyzer
    clock: Clock

    async def execute(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
        force_reanalyze: bool = False,
    ) -> GeoRunResultAnalysis:
        result = await self.repository.get_run_result(tenant_id, run_result_id)
        if result is None:
            raise RunResultSemanticAnalysisNotFound("run result not found")

        if not force_reanalyze:
            current = await self.repository.get_semantic_run_result_analysis(
                tenant_id,
                run_result_id,
            )
            if current is not None:
                return current

        if result.status != "completed" or not result.raw_response.strip():
            return await self._save_failed(
                tenant_id,
                run_result_id,
                "run_result_not_analyzable",
                "run result is not completed or raw response is empty",
            )

        query = await self.repository.get_query(tenant_id, result.query_id)
        if query is None:
            return await self._save_failed(
                tenant_id,
                run_result_id,
                "query_context_missing",
                "query context is missing",
            )

        entities = await self.repository.list_entities(tenant_id, query.project_id)
        own_brand = _own_brand(entities)
        if own_brand is None:
            return await self._save_failed(
                tenant_id,
                run_result_id,
                "own_brand_missing",
                "active own brand entity is missing",
            )

        topics = await self.repository.list_topics(tenant_id, query.project_id)
        topic = next(
            (
                item
                for item in topics
                if item.id == query.topic_id and item.status == "active"
            ),
            None,
        )
        command = AnalyzeGeoRunResultCommand(
            run_result_id=result.id,
            project_id=query.project_id,
            query_id=query.id,
            query_text=query.query_text,
            topic_id=topic.id if topic is not None else None,
            topic_name=topic.name if topic is not None else None,
            topic_description=topic.description if topic is not None else None,
            provider=result.provider,
            surface=result.surface,
            model=result.model,
            region=result.region,
            language=result.language,
            raw_response=result.raw_response,
            entities=GeoAnalysisEntityContext(
                own_brand=_entity_input(own_brand, "own_brand"),
                competitors=[
                    _entity_input(item, "competitor")
                    for item in entities
                    if item.status == "active" and item.entity_type == "competitor"
                ],
            ),
        )
        try:
            analysis = await self.analyzer.analyze(command)
        except Exception as exc:
            return await self._save_failed(
                tenant_id,
                run_result_id,
                exc.__class__.__name__,
                str(exc),
            )
        return await self._save(tenant_id, analysis)

    async def _save_failed(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
        error_code: str,
        error_message: str,
    ) -> GeoRunResultAnalysis:
        return await self._save(
            tenant_id,
            GeoRunResultAnalysis(
                run_result_id=run_result_id,
                analyzer="semantic_analysis",
                status="failed",
                error_code=error_code,
                error_message=error_message,
            ),
        )

    async def _save(
        self,
        tenant_id: UUID,
        analysis: GeoRunResultAnalysis,
    ) -> GeoRunResultAnalysis:
        saved = await self.repository.save_semantic_run_result_analysis(
            tenant_id,
            SaveSemanticRunResultAnalysisCommand(analysis=analysis),
            self.clock.now(),
        )
        if saved is None:
            raise RunResultSemanticAnalysisNotFound("run result not found")
        return saved


def _own_brand(entities: list[GeoEntityRecord]) -> GeoEntityRecord | None:
    return next(
        (
            item
            for item in entities
            if item.status == "active" and item.entity_type == "own_brand"
        ),
        None,
    )


def _entity_input(
    entity: GeoEntityRecord,
    role: str,
) -> GeoAnalysisEntityInput:
    return GeoAnalysisEntityInput(
        entity_id=entity.id,
        entity_role=role,
        name=entity.name,
        website_url=entity.website_url,
    )
