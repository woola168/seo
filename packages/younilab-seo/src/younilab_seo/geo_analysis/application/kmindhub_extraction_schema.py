from younilab_seo.geo_analysis.application.contracts import (
    KMindHubExtractionTaskDefinition,
    KMindHubExtractionTaskField,
)

SENTIMENT_VALUES = frozenset(
    {"positive", "neutral", "negative", "mixed", "unknown"}
)
ENTITY_TYPE_VALUES = frozenset({"own_brand", "competitor", "other"})
SEMANTIC_ENTITY_ROLE_VALUES = frozenset({"own_brand", "competitor"})
SEMANTIC_SENTIMENT_VALUES = frozenset({"positive", "negative"})
SEMANTIC_FACT_TYPE_VALUES = frozenset(
    {"product", "service", "topic", "common_statement"}
)
ANALYSIS_TASK_KEY = "geo_answer_analysis"
ANALYSIS_SCHEMA_VERSION = 1
SEMANTIC_ANALYSIS_TASK_KEY = "geo_semantic_analysis"
SEMANTIC_ANALYSIS_SCHEMA_VERSION = 2


def geo_answer_analysis_task_definition() -> KMindHubExtractionTaskDefinition:
    """回傳 GEO answer analysis v1 的 KMindHub task schema。"""

    return KMindHubExtractionTaskDefinition(
        task_key=ANALYSIS_TASK_KEY,
        schema_version=ANALYSIS_SCHEMA_VERSION,
        name="GEO answer analysis v1",
        task=(
            "Extract report-ready facts from one AI answer. Return one item for "
            "the answer summary, mentions, and key statement evidence."
        ),
        description=(
            "GEO 報表前處理 schema，用於擷取答案摘要、情緒、主題、"
            "品牌或競品提及，以及可供人工檢視的重要陳述。"
        ),
        fields=[
            _field(
                "summary",
                "答案摘要",
                "用繁體中文摘要 AI answer 的主要結論。",
                "以 1 到 3 句繁體中文回傳，不要新增原文沒有的資訊。",
                "AI 建議優先評估具備在地服務能力的供應商。",
                0,
            ),
            _field(
                "overallSentiment",
                "整體情緒",
                "AI answer 對自有品牌或主要討論對象的整體情緒。",
                _enum_instruction(SENTIMENT_VALUES),
                "neutral",
                1,
            ),
            _field(
                "theme",
                "主題",
                "答案主要討論的主題或評估面向。",
                "回傳短詞，例如價格、導入風險、品牌比較或售後服務。",
                "售後服務",
                2,
            ),
            _field(
                "entityName",
                "提及對象",
                "答案中被提及的品牌、競品或其他公司/產品名稱。",
                "只回傳 answer 原文中明確出現或可由別名明確對應的名稱。",
                "Acme",
                3,
            ),
            _field(
                "entityType",
                "提及類型",
                "提及對象的類型。",
                _enum_instruction(ENTITY_TYPE_VALUES),
                "competitor",
                4,
            ),
            _field(
                "mentionCount",
                "提及次數",
                "該 entity 在答案中被提及的次數。",
                "只回傳 0 或正整數；不確定時回傳 0。",
                "2",
                5,
                field_type="int",
            ),
            _field(
                "statementText",
                "重要陳述",
                "答案中可作為報表觀察的關鍵陳述。",
                "必須是 answer 原文中的短句或忠實摘錄，不要創造新陳述。",
                "Acme 在售後服務上較具優勢。",
                6,
            ),
            _field(
                "statementSentiment",
                "陳述情緒",
                "重要陳述呈現的情緒或評價方向。",
                _enum_instruction(SENTIMENT_VALUES),
                "positive",
                7,
            ),
            _field(
                "subjectEntityName",
                "陳述對象",
                "重要陳述主要描述的品牌、競品或其他 entity。",
                "若陳述沒有特定對象，請留空。",
                "Acme",
                8,
            ),
            _field(
                "evidenceText",
                "證據文字",
                "支持 mention 或 statement 的原文片段。",
                "必須能在 raw answer 中找到相同或高度相近的片段。",
                "Acme 在售後服務上較具優勢。",
                9,
            ),
        ],
    )


def geo_semantic_analysis_task_definition() -> KMindHubExtractionTaskDefinition:
    """定義 semantic facts extraction task schema。"""

    return KMindHubExtractionTaskDefinition(
        task_key=SEMANTIC_ANALYSIS_TASK_KEY,
        schema_version=SEMANTIC_ANALYSIS_SCHEMA_VERSION,
        name="GEO semantic analysis v2",
        task=(
            "Extract entity mentions, statement sentiment, and semantic labels "
            "from one AI answer using the supplied entity context. Copy entity "
            "UUIDs exactly from Entity context and copy evidenceText only from "
            "exact text in the AI answer."
        ),
        description=(
            "只輸出 GEO semantic facts，不處理 citations、dashboard metrics 或 URL normalization。"
        ),
        fields=[
            _field(
                "entityId",
                "Entity ID",
                "Tracked entity UUID for mention or sentiment facts.",
                (
                    "Copy the exact UUID from Entity context for the matching own "
                    "brand or competitor. Do not use the entity name, website, or "
                    "an invented id. If no listed entity matches, do not emit an "
                    "entity fact."
                ),
                "00000000-0000-4000-8000-000000000001",
                0,
            ),
            _field(
                "entityRole",
                "Entity role",
                "Tracked entity role.",
                _enum_instruction(SEMANTIC_ENTITY_ROLE_VALUES),
                "own_brand",
                1,
            ),
            _field(
                "entityName",
                "Entity name",
                "Tracked entity name as it appears in the entity context.",
                "Use the canonical entity name from the provided context.",
                "Acme",
                2,
            ),
            _field(
                "mentioned",
                "Mentioned",
                "Whether the entity appears in the AI answer.",
                "Use true or false.",
                "true",
                3,
                field_type="boolean",
            ),
            _field(
                "firstMentionOrder",
                "First mention order",
                "One-based order among tracked entities mentioned in the answer.",
                "Leave empty when mentioned is false.",
                "1",
                4,
                field_type="int",
            ),
            _field(
                "sentiment",
                "Sentiment",
                "Statement-level sentiment for the tracked entity.",
                (
                    _enum_instruction(SEMANTIC_SENTIMENT_VALUES)
                    + " Do not emit a sentiment fact for neutral, mixed, unknown, "
                    "or uncertain statements."
                ),
                "positive",
                5,
            ),
            _field(
                "theme",
                "Theme",
                "Short theme for a sentiment statement.",
                "Use a concise stable theme.",
                "product fit",
                6,
            ),
            _field(
                "statement",
                "Statement",
                "A sentiment-bearing statement from the answer.",
                (
                    "Prefer copying one complete sentence from the AI answer. If "
                    "you summarize only when needed, evidenceText must still be "
                    "an exact substring copied from the AI answer."
                ),
                "Acme ERP is suitable for manufacturers.",
                7,
            ),
            _field(
                "factType",
                "Semantic fact type",
                "Semantic label category.",
                (
                    _enum_instruction(SEMANTIC_FACT_TYPE_VALUES)
                    + " Do not use brand, company, sentiment, citation, or other "
                    "unsupported categories."
                ),
                "product",
                8,
            ),
            _field(
                "value",
                "Semantic fact value",
                "Product, service, topic, or common statement value.",
                "Return one stable normalized value.",
                "ERP",
                9,
            ),
            _field(
                "evidenceText",
                "Evidence text",
                "Exact supporting text from the raw answer.",
                (
                    "Use an exact contiguous substring copied from the AI answer "
                    "section only. Do not paraphrase, summarize, translate, "
                    "normalize, or combine multiple spans. Do not copy text from "
                    "Instructions, Query context, Topic context, or Entity context. "
                    "If no exact supporting substring exists in the AI answer, "
                    "leave evidenceText empty."
                ),
                "Acme ERP",
                10,
            ),
            _field(
                "confidence",
                "Confidence",
                "Confidence score between 0 and 1.",
                "Use a decimal number between 0 and 1.",
                "0.9",
                11,
                field_type="float",
            ),
        ],
    )


def _field(
    name: str,
    display_name: str,
    description: str,
    instruction: str,
    examples: str,
    sort_order: int,
    *,
    field_type: str = "string",
) -> KMindHubExtractionTaskField:
    return KMindHubExtractionTaskField(
        name=name,
        field_type=field_type,
        lookup_role="ignored",
        display_name=display_name,
        description=description,
        normalization={"instruction": instruction},
        examples=examples,
        sort_order=sort_order,
        is_visible=True,
        is_extracted=True,
    )


def _enum_instruction(values: frozenset[str]) -> str:
    return "只能回傳其中一個值：" + ", ".join(sorted(values)) + "。"
