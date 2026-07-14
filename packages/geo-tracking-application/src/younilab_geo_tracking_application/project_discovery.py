from younilab_geo_tracking_application.contracts import (
    ProjectInspectionCommand,
    ProjectInspectionResult,
    ProjectSuggestionCommand,
    ProjectSuggestionsResult,
    TopicInput,
    VerifiedProjectIdentity,
)
from younilab_geo_tracking_application.interfaces import (
    ProjectDiscoveryProvider,
    ProviderRequestError,
)


class ProjectDiscoveryError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ProjectDiscoveryService:
    def __init__(self, provider: ProjectDiscoveryProvider) -> None:
        self._provider = provider

    async def inspect(
        self, command: ProjectInspectionCommand
    ) -> ProjectInspectionResult:
        try:
            inspection = await self._provider.inspect_url(command)
        except ProviderRequestError as exc:
            raise ProjectDiscoveryError(exc.code) from exc
        if (
            not inspection.retrieval_succeeded
            or inspection.retrieved_url is None
            or inspection.identity is None
        ):
            raise ProjectDiscoveryError("project_url_retrieval_failed")
        project_name = _clean_text(inspection.identity.project_name)
        project_description = _clean_text(inspection.identity.project_description)
        core_offerings = _clean_text_items(
            inspection.identity.core_offerings,
            limit=8,
        )
        if (
            not inspection.identity.sufficient_context
            or not project_name
            or not project_description
            or not core_offerings
        ):
            raise ProjectDiscoveryError("insufficient_project_context")

        return ProjectInspectionResult(
            source_url=command.project_url,
            retrieved_url=inspection.retrieved_url,
            project_name=project_name,
            project_description=project_description,
            project_type=inspection.identity.project_type,
            core_offerings=core_offerings,
            target_audiences=_clean_text_items(
                inspection.identity.target_audiences,
                limit=8,
            ),
        )

    async def suggest(
        self, command: ProjectSuggestionCommand
    ) -> ProjectSuggestionsResult:
        confirmed = command.confirmed_project
        project_name = _clean_text(confirmed.project_name)
        project_description = _clean_text(confirmed.project_description)
        core_offerings = tuple(_clean_text_items(confirmed.core_offerings, limit=8))
        if not project_name or not project_description or not core_offerings:
            raise ProjectDiscoveryError("invalid_confirmed_project")

        identity = VerifiedProjectIdentity(
            source_url=confirmed.source_url,
            retrieved_url=confirmed.retrieved_url,
            project_name=project_name,
            project_description=project_description,
            project_type=confirmed.project_type,
            core_offerings=core_offerings,
            target_audiences=tuple(
                _clean_text_items(confirmed.target_audiences, limit=8)
            ),
        )
        try:
            suggestions = await self._provider.research_suggestions(
                command,
                identity,
            )
        except ProviderRequestError as exc:
            raise ProjectDiscoveryError(exc.code) from exc
        if not suggestions.search_succeeded:
            raise ProjectDiscoveryError("project_market_research_not_grounded")
        competitors = _clean_text_items(
            suggestions.competitors,
            limit=command.competitor_count,
            excluded_names=(identity.project_name,),
        )
        topics = _clean_topics(suggestions.topics, limit=command.topic_count)
        keywords = _clean_text_items(
            suggestions.keywords,
            limit=command.keyword_count,
            excluded_names=(identity.project_name, *competitors),
        )
        return ProjectSuggestionsResult(
            competitors=competitors,
            topics=topics,
            keywords=keywords,
            references=suggestions.references,
        )


def _clean_text_items(
    values: list[str],
    *,
    limit: int,
    excluded_names: tuple[str, ...] = (),
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    normalized_exclusions = tuple(_normalize(value) for value in excluded_names)
    for value in values:
        cleaned = " ".join(value.split())
        normalized = _normalize(cleaned)
        if not normalized or normalized in seen:
            continue
        if any(excluded in normalized for excluded in normalized_exclusions):
            continue
        seen.add(normalized)
        result.append(cleaned)
        if len(result) == limit:
            break
    return result


def _clean_topics(values: list[TopicInput], *, limit: int) -> list[TopicInput]:
    result: list[TopicInput] = []
    seen: set[str] = set()
    for topic in values:
        name = _clean_text(topic.name)
        description = _clean_text(topic.description)
        normalized = _normalize(name)
        if not normalized or not description or normalized in seen:
            continue
        seen.add(normalized)
        result.append(
            TopicInput(
                name=name,
                description=description,
            )
        )
        if len(result) == limit:
            break
    return result


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def _clean_text(value: str) -> str:
    return " ".join(value.split())
