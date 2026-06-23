from collections.abc import Mapping

from younilab_geo_tracking_domain import ProviderCode, RunResultStatus

from younilab_geo_tracking_application.contracts import (
    AnswerRequest,
    Reference,
    RunRequestCommand,
    RunRequestResult,
    RunResult,
)
from younilab_geo_tracking_application.interfaces import (
    AnswerProvider,
    Clock,
    IdGenerator,
)
from younilab_geo_tracking_application.prompt_templates import system_prompt


class RunEngineService:
    def __init__(
        self,
        answer_providers: Mapping[ProviderCode, AnswerProvider],
        id_generator: IdGenerator,
        clock: Clock,
    ) -> None:
        self._answer_providers = dict(answer_providers)
        self._id_generator = id_generator
        self._clock = clock

    async def run(self, command: RunRequestCommand) -> RunRequestResult:
        run_request_id = self._id_generator.new_id()
        results: list[RunResult] = []
        answer_provider = self._answer_providers[command.provider]
        for query in command.queries:
            run_at = self._clock.now()
            try:
                answer = await answer_provider.generate_answer(
                    AnswerRequest(
                        query_id=query.id,
                        query_text=query.text,
                        region=query.region,
                        language=query.language,
                        market_type=query.market_type,
                        is_branded=query.is_branded,
                        system_prompt=system_prompt(
                            query.market_type,
                            query.region,
                            query.language,
                        ),
                    )
                )
                results.append(
                    RunResult(
                        id=self._id_generator.new_id(),
                        run_request_id=run_request_id,
                        query_id=query.id,
                        provider=answer.provider,
                        surface=answer.surface,
                        model=answer.model,
                        region=query.region,
                        language=query.language,
                        status=RunResultStatus.COMPLETED,
                        raw_response=answer.raw_response,
                        reference_urls=answer.reference_urls,
                        references=_answer_references(
                            answer.references, answer.reference_urls
                        ),
                        error=None,
                        run_at=run_at,
                    )
                )
            except Exception:
                results.append(
                    RunResult(
                        id=self._id_generator.new_id(),
                        run_request_id=run_request_id,
                        query_id=query.id,
                        provider=command.provider,
                        surface=command.provider,
                        model="",
                        region=query.region,
                        language=query.language,
                        status=RunResultStatus.FAILED,
                        raw_response="",
                        reference_urls=[],
                        references=[],
                        error="provider_request_failed",
                        run_at=run_at,
                    )
                )
        return RunRequestResult(
            id=run_request_id,
            seo_task_id=command.seo_task_id,
            timing=command.timing,
            results=results,
        )


def _answer_references(
    references: list[Reference],
    reference_urls: list[str],
) -> list[Reference]:
    if references:
        return references
    return [Reference(url=url) for url in reference_urls]
