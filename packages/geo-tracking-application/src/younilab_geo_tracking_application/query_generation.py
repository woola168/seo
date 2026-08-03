from younilab_geo_tracking_domain import (
    MarketType,
    ProviderCode,
    QuerySource,
    QueryStatus,
)

from younilab_geo_tracking_application.contracts import (
    GeneratedQuery,
    QueryDraft,
    QueryGenerationCommand,
    QueryGenerationResult,
    QueryIntent,
    TopicInput,
    TopicSummary,
)
from younilab_geo_tracking_application.interfaces import (
    IdGenerator,
    QueryGenerationProvider,
)
from younilab_geo_tracking_application.prompt_templates import default_language


class QueryGenerationService:
    def __init__(
        self,
        id_generator: IdGenerator,
        providers: dict[ProviderCode, QueryGenerationProvider],
    ) -> None:
        self._id_generator = id_generator
        self._providers = providers

    async def generate(
        self,
        command: QueryGenerationCommand,
    ) -> QueryGenerationResult:
        language = command.language or default_language(command.region)
        topics = self._topics(command)
        drafts = await self._providers[command.provider].generate_drafts(command)
        return self._result_from_drafts(command, topics, language, drafts)

    def _result_from_drafts(
        self,
        command: QueryGenerationCommand,
        topics: list[TopicSummary],
        language: str,
        drafts: list[QueryDraft],
    ) -> QueryGenerationResult:
        topics_by_name = {topic.name: topic for topic in topics}
        queries: list[GeneratedQuery] = []
        for draft in drafts[: command.max_queries]:
            topic = topics_by_name.get(draft.attributes.topic_name, topics[0])
            queries.append(
                GeneratedQuery(
                    id=self._id_generator.new_id(),
                    text=draft.query,
                    keywords=_draft_keywords(draft, command.keywords),
                    topic_id=topic.id,
                    topic_name=topic.name,
                    region=command.region,
                    language=language,
                    market_type=command.market_type,
                    is_branded=(
                        draft.attributes.brand_mention_rules.should_mention_own_brand
                    ),
                    attributes=draft.attributes,
                    metadata={
                        "keyword": draft.attributes.keyword,
                        "topic": topic.name,
                        "topicDescription": topic.description,
                        "intent": draft.attributes.intent.category,
                        "marketType": command.market_type,
                    },
                    source=QuerySource.RESEARCH,
                    status=QueryStatus.ACTIVE,
                )
            )
        return QueryGenerationResult(topics=topics, queries=queries)

    def _topics(self, command: QueryGenerationCommand) -> list[TopicSummary]:
        topic_inputs = self._topic_inputs(command)
        return [
            TopicSummary(
                id=self._id_generator.new_id(),
                name=topic.name,
                description=topic.description,
            )
            for topic in topic_inputs
        ]

    def _topic_inputs(self, command: QueryGenerationCommand) -> list[TopicInput]:
        if command.topics:
            return command.topics
        names = command.topic_names or self._default_topic_names(command)
        return [TopicInput(name=name) for name in names]

    def _default_topic_names(self, command: QueryGenerationCommand) -> list[str]:
        if command.market_type == MarketType.B2B_PROCUREMENT:
            return ["品牌型", "產品型", "採購評估"]
        return ["品牌型", "產品型", "資訊型"]


class DummyQueryGenerationProvider:
    async def generate_drafts(
        self,
        command: QueryGenerationCommand,
    ) -> list[QueryDraft]:
        topics = _topic_inputs(command, self._default_topic_names(command))
        drafts: list[QueryDraft] = []
        for keyword in command.keywords:
            for topic in topics:
                for intent in command.intents:
                    drafts.append(
                        QueryDraft(
                            attributes={
                                "intent": intent,
                                "keyword": keyword,
                                "topicName": topic.name,
                                "topicDescription": topic.description,
                                "audience": command.audience,
                                "brandMentionRules": command.brand_mention_rules,
                            },
                            query=self._query_text(command, keyword, intent),
                            keywords=[keyword],
                        )
                    )
                    if len(drafts) >= command.max_queries:
                        return drafts
        return drafts

    def _default_topic_names(self, command: QueryGenerationCommand) -> list[str]:
        if command.market_type == MarketType.B2B_PROCUREMENT:
            return ["品牌型", "產品型", "採購評估"]
        return ["品牌型", "產品型", "資訊型"]

    def _query_text(
        self,
        command: QueryGenerationCommand,
        keyword: str,
        intent: QueryIntent,
    ) -> str:
        competitor = command.competitor_brands[0] if command.competitor_brands else ""
        rules = command.brand_mention_rules
        language = command.language or default_language(command.region)
        if language == "en-US":
            return self._english_query(command, keyword, intent, competitor)
        if (
            rules.should_mention_competitor
            and competitor
            and intent.category == "commercial_investigation"
        ):
            if rules.should_mention_own_brand:
                return (
                    f"{command.brand_name} 和 {competitor} 在 {keyword} 的"
                    f"{intent.description}上有什麼差異？"
                )
            return f"{competitor} 的 {keyword} 有哪些值得比較的地方？"
        if rules.should_mention_own_brand:
            return (
                f"{command.brand_name} 的 {keyword} 在{intent.description}"
                "上應該怎麼評估？"
            )
        return f"{keyword} 在{intent.description}上有哪些推薦品牌或評估重點？"

    def _english_query(
        self,
        command: QueryGenerationCommand,
        keyword: str,
        intent: QueryIntent,
        competitor: str,
    ) -> str:
        rules = command.brand_mention_rules
        if (
            rules.should_mention_competitor
            and competitor
            and intent.category == "commercial_investigation"
        ):
            if rules.should_mention_own_brand:
                return (
                    f"How does {command.brand_name} compare with {competitor} "
                    f"for {keyword}?"
                )
            return f"How does {competitor} compare with other {keyword} options?"
        if rules.should_mention_own_brand:
            return (
                f"What should buyers evaluate about {command.brand_name} for {keyword}?"
            )
        return f"What are the best {keyword} options for {intent.description}?"


def _topic_inputs(
    command: QueryGenerationCommand,
    default_names: list[str],
) -> list[TopicInput]:
    if command.topics:
        return command.topics
    names = command.topic_names or default_names
    return [TopicInput(name=name) for name in names]


def _draft_keywords(draft: QueryDraft, allowed_keywords: list[str]) -> list[str]:
    keywords = [
        keyword
        for keyword in dict.fromkeys(draft.keywords or [draft.attributes.keyword])
        if keyword in allowed_keywords
    ]
    return keywords or [draft.attributes.keyword]
