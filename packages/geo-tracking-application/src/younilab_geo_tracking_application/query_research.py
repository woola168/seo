from younilab_geo_tracking_domain import ProviderCode

from younilab_geo_tracking_application.contracts import (
    QueryResearchCommand,
    QueryResearchResult,
)
from younilab_geo_tracking_application.interfaces import QueryResearchProvider


class QueryResearchService:
    def __init__(
        self,
        providers: dict[ProviderCode, QueryResearchProvider],
    ) -> None:
        self._providers = providers

    async def research(self, command: QueryResearchCommand) -> QueryResearchResult:
        return await self._providers[command.provider].research(command)


class DummyQueryResearchProvider:
    async def research(self, command: QueryResearchCommand) -> QueryResearchResult:
        competitors = ", ".join(command.competitor_brands) or "主要競品"
        return QueryResearchResult(
            research_context=(
                f"Dummy research context for {command.brand_name}. "
                f"Competitors: {competitors}. Keywords: {', '.join(command.keywords)}."
            ),
            searched_keywords=command.keywords,
            source_urls=[],
        )
