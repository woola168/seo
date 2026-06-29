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
        intents = ", ".join(intent.category for intent in command.intents) or "not specified"
        brand_rules = command.brand_mention_rules
        return QueryResearchResult(
            research_context=(
                f"Dummy research context for {command.brand_name}. "
                f"Competitors: {competitors}. Keywords: {', '.join(command.keywords)}. "
                f"Intents: {intents}. "
                "Brand mention rules: "
                f"ownBrand={brand_rules.should_mention_own_brand}, "
                f"competitor={brand_rules.should_mention_competitor}."
            ),
            searched_keywords=command.keywords,
            source_urls=[],
        )
