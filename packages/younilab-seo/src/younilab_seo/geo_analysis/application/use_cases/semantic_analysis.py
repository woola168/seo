from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    AnalyzeGeoRunResultCommand,
    GeoAnalysisEntityContext,
    GeoAnalysisEntityInput,
    GeoEntityRecord,
    GeoRunResultAnalysis,
    GeoRunResultEntityDetection,
    SaveRunResultEntityDetectionCommand,
    SaveSemanticRunResultAnalysisCommand,
)
from younilab_seo.geo_analysis.application.entity_mention_detection import (
    ENTITY_MENTION_DETECTOR_VERSION,
    detect_entity_mentions,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    GeoRunResultAnalyzer,
)
from younilab_seo.geo_analysis.application.interfaces.semantic_analysis import (
    SemanticAnalysisPersistence,
)


class RunResultSemanticAnalysisNotFound(LookupError):
    """找不到租戶可存取的 GEO run result，無法進行 semantic analysis。"""


@dataclass(frozen=True)
class AnalyzeRunResult:
    """將已保存的 raw run result 轉成 semantic facts 並保存分析結果。"""

    persistence: SemanticAnalysisPersistence
    analyzer: GeoRunResultAnalyzer
    clock: Clock

    async def execute(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
        force_reanalyze: bool = False,
    ) -> GeoRunResultAnalysis:
        context = await self.persistence.load_semantic_analysis_context(
            tenant_id,
            run_result_id,
        )
        if context is None:
            raise RunResultSemanticAnalysisNotFound("run result not found")
        result = context.run_result

        if not force_reanalyze:
            current = await self.persistence.get_existing_semantic_analysis(
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

        query = context.query
        if query is None:
            return await self._save_failed(
                tenant_id,
                run_result_id,
                "query_context_missing",
                "query context is missing",
            )

        own_brand = context.own_brand
        if own_brand is None:
            return await self._save_failed(
                tenant_id,
                run_result_id,
                "own_brand_missing",
                "active own brand entity is missing",
            )

        try:
            detection = detect_entity_mentions(
                run_result_id=run_result_id,
                raw_response=result.raw_response,
                entities=[own_brand, *context.competitors],
                aliases=list(context.aliases),
            )
        except Exception as exc:
            detection = GeoRunResultEntityDetection(
                run_result_id=run_result_id,
                detector_version=ENTITY_MENTION_DETECTOR_VERSION,
                status="failed",
                error_code=exc.__class__.__name__,
                error_message=str(exc),
            )
        saved_detection = await self.persistence.save_semantic_entity_detection(
            tenant_id,
            SaveRunResultEntityDetectionCommand(detection=detection),
            self.clock.now(),
        )
        if saved_detection is None:
            raise RunResultSemanticAnalysisNotFound("run result not found")

        topic = context.topic
        command = AnalyzeGeoRunResultCommand(
            tenant_id=tenant_id,
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
                    _entity_input(item, "competitor") for item in context.competitors
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
                analyzer_request_payload=getattr(exc, "request_payload", None),
                analyzer_response_payload=getattr(exc, "response_payload", None),
                validation_failures=getattr(exc, "validation_failures", None),
            )
        return await self._save(tenant_id, analysis)

    async def _save_failed(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
        error_code: str,
        error_message: str,
        *,
        analyzer_request_payload: dict | None = None,
        analyzer_response_payload: dict | None = None,
        validation_failures: list[dict] | None = None,
    ) -> GeoRunResultAnalysis:
        return await self._save(
            tenant_id,
            GeoRunResultAnalysis(
                run_result_id=run_result_id,
                analyzer="semantic_analysis",
                status="failed",
                error_code=error_code,
                error_message=error_message,
                analyzer_request_payload=analyzer_request_payload,
                analyzer_response_payload=analyzer_response_payload,
                validation_failures=validation_failures or [],
            ),
        )

    async def _save(
        self,
        tenant_id: UUID,
        analysis: GeoRunResultAnalysis,
    ) -> GeoRunResultAnalysis:
        saved = await self.persistence.save_semantic_analysis(
            tenant_id,
            SaveSemanticRunResultAnalysisCommand(analysis=analysis),
            self.clock.now(),
        )
        if saved is None:
            raise RunResultSemanticAnalysisNotFound("run result not found")
        return saved


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
