from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from younilab_seo.geo_analysis.application import (
    AnalyzeGeoRunResultCommand,
    GeoAnalysisEntityContext,
    GeoAnalysisEntityInput,
    GeoEntityMentionFact,
    GeoResponseSemanticFact,
    GeoRunResultAnalysis,
    GeoSentimentFact,
    QueryIntent,
    QueryResearchCommand,
)


def test_query_research_command_accepts_tracking_aligned_payload() -> None:
    command = QueryResearchCommand(
        provider="gemini",
        brandName="Acme",
        competitorBrands=["Beta"],
        keywords=["erp"],
        region="TW",
        language="zh-TW",
        marketType="b2b_procurement",
        intents=[QueryIntent(category="commercial", description="比較供應商")],
    )

    assert command.keywords == ["erp"]
    assert command.competitor_brands == ["Beta"]
    assert command.intents[0].category == "commercial"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("keywords", []),
        ("keywords", [f"keyword-{index}" for index in range(11)]),
        ("competitorBrands", [f"Competitor {index}" for index in range(9)]),
        (
            "intents",
            [
                {"category": f"intent-{index}", "description": "比較供應商"}
                for index in range(9)
            ],
        ),
    ],
)
def test_query_research_command_rejects_tracking_incompatible_payload(
    field: str,
    value: list,
) -> None:
    payload = {
        "provider": "gemini",
        "brandName": "Acme",
        "competitorBrands": ["Beta"],
        "keywords": ["erp"],
        "region": "TW",
        "language": "zh-TW",
        "marketType": "b2b_procurement",
        "intents": [{"category": "commercial", "description": "比較供應商"}],
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        QueryResearchCommand(**payload)


def test_analyze_geo_run_result_command_accepts_camel_case_payload() -> None:
    command = AnalyzeGeoRunResultCommand(
        tenantId=UUID("00000000-0000-4000-8000-000000000000"),
        runResultId=UUID("00000000-0000-4000-8000-000000000001"),
        projectId=UUID("00000000-0000-4000-8000-000000000002"),
        queryId=UUID("00000000-0000-4000-8000-000000000003"),
        queryText="Who are reliable suppliers?",
        topicId=UUID("00000000-0000-4000-8000-000000000004"),
        topicName="Supplier evaluation",
        topicDescription="Compare suppliers mentioned in AI answers.",
        provider="gemini",
        surface="Gemini",
        model="gemini-2.5-flash",
        region="TW",
        language="zh-TW",
        rawResponse="Acme is frequently recommended.",
        entities={
            "ownBrand": {
                "entityId": "00000000-0000-4000-8000-000000000005",
                "entityRole": "own_brand",
                "name": "Acme",
                "websiteUrl": "https://acme.example",
            },
            "competitors": [
                {
                    "entityId": "00000000-0000-4000-8000-000000000006",
                    "entityRole": "competitor",
                    "name": "Beta",
                }
            ],
        },
    )

    assert command.tenant_id == UUID("00000000-0000-4000-8000-000000000000")
    assert command.run_result_id == UUID("00000000-0000-4000-8000-000000000001")
    assert command.query_text == "Who are reliable suppliers?"
    assert command.entities.own_brand.name == "Acme"
    dumped = command.model_dump(mode="json", by_alias=True)
    assert dumped["tenantId"] == "00000000-0000-4000-8000-000000000000"
    assert dumped["runResultId"] == "00000000-0000-4000-8000-000000000001"
    assert dumped["rawResponse"] == "Acme is frequently recommended."
    assert dumped["entities"]["ownBrand"]["websiteUrl"] == "https://acme.example"


def test_geo_run_result_analysis_accepts_nested_semantic_facts() -> None:
    entity_id = uuid4()
    analysis = GeoRunResultAnalysis(
        runResultId=uuid4(),
        analyzer="fake",
        analyzerVersion="v1",
        status="completed",
        entityMentions=[
            {
                "entityId": str(entity_id),
                "entityRole": "own_brand",
                "entityName": "Acme",
                "mentioned": True,
                "firstMentionOrder": 1,
                "evidenceText": "Acme is frequently recommended.",
                "confidence": 0.95,
            }
        ],
        sentiments=[
            {
                "entityId": str(entity_id),
                "entityRole": "own_brand",
                "entityName": "Acme",
                "sentiment": "positive",
                "theme": "supplier quality",
                "statement": "Acme is frequently recommended.",
                "evidenceText": "Acme is frequently recommended.",
                "confidence": 0.9,
            }
        ],
        semanticFacts=[
            {
                "factType": "common_statement",
                "value": "Acme is frequently recommended.",
                "evidenceText": "Acme is frequently recommended.",
                "confidence": 0.8,
            }
        ],
    )

    assert analysis.status == "completed"
    assert analysis.entity_mentions[0].first_mention_order == 1
    assert analysis.sentiments[0].sentiment == "positive"
    assert analysis.semantic_facts[0].fact_type == "common_statement"
    dumped = analysis.model_dump(mode="json", by_alias=True)
    assert dumped["analyzerVersion"] == "v1"
    assert dumped["entityMentions"][0]["firstMentionOrder"] == 1
    assert dumped["semanticFacts"][0]["factType"] == "common_statement"


def test_geo_run_result_analysis_accepts_failed_result_without_facts() -> None:
    analysis = GeoRunResultAnalysis(
        runResultId=uuid4(),
        analyzer="fake",
        status="failed",
        errorCode="analyzer_timeout",
        errorMessage="analyzer timed out",
    )

    assert analysis.entity_mentions == []
    assert analysis.sentiments == []
    assert analysis.semantic_facts == []
    assert analysis.error_code == "analyzer_timeout"


def test_geo_analysis_entity_input_rejects_invalid_entity_role() -> None:
    with pytest.raises(ValidationError):
        GeoAnalysisEntityInput(
            entityId=uuid4(),
            entityRole="other",
            name="Acme",
        )


def test_geo_analysis_entity_context_rejects_invalid_own_brand_role() -> None:
    with pytest.raises(ValidationError):
        GeoAnalysisEntityContext(
            ownBrand={
                "entityId": str(uuid4()),
                "entityRole": "competitor",
                "name": "Acme",
            }
        )


def test_geo_analysis_entity_context_rejects_invalid_competitor_role() -> None:
    with pytest.raises(ValidationError):
        GeoAnalysisEntityContext(
            ownBrand={
                "entityId": str(uuid4()),
                "entityRole": "own_brand",
                "name": "Acme",
            },
            competitors=[
                {
                    "entityId": str(uuid4()),
                    "entityRole": "own_brand",
                    "name": "Beta",
                }
            ],
        )


def test_geo_run_result_analysis_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        GeoRunResultAnalysis(
            runResultId=uuid4(),
            analyzer="fake",
            status="pending",
        )


def test_geo_sentiment_fact_rejects_neutral_sentiment() -> None:
    with pytest.raises(ValidationError):
        GeoSentimentFact(
            entityId=uuid4(),
            entityRole="own_brand",
            entityName="Acme",
            sentiment="neutral",
            theme="supplier quality",
            statement="Acme is mentioned.",
        )


def test_geo_response_semantic_fact_rejects_unsupported_fact_type() -> None:
    with pytest.raises(ValidationError):
        GeoResponseSemanticFact(
            factType="recommendation",
            value="Improve product content.",
        )


@pytest.mark.parametrize("first_mention_order", [0, -1])
def test_geo_entity_mention_fact_rejects_non_positive_position(
    first_mention_order: int,
) -> None:
    with pytest.raises(ValidationError):
        GeoEntityMentionFact(
            entityId=uuid4(),
            entityRole="own_brand",
            entityName="Acme",
            mentioned=True,
            firstMentionOrder=first_mention_order,
        )


def test_geo_entity_mention_fact_rejects_position_when_not_mentioned() -> None:
    with pytest.raises(ValidationError):
        GeoEntityMentionFact(
            entityId=uuid4(),
            entityRole="own_brand",
            entityName="Acme",
            mentioned=False,
            firstMentionOrder=1,
        )


def test_geo_entity_mention_fact_rejects_evidence_when_not_mentioned() -> None:
    with pytest.raises(ValidationError):
        GeoEntityMentionFact(
            entityId=uuid4(),
            entityRole="own_brand",
            entityName="Acme",
            mentioned=False,
            evidenceText="Acme is mentioned.",
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_geo_entity_mention_fact_rejects_confidence_outside_range(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        GeoEntityMentionFact(
            entityId=uuid4(),
            entityRole="own_brand",
            entityName="Acme",
            mentioned=True,
            confidence=confidence,
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_geo_sentiment_fact_rejects_confidence_outside_range(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        GeoSentimentFact(
            entityId=uuid4(),
            entityRole="own_brand",
            entityName="Acme",
            sentiment="positive",
            theme="supplier quality",
            statement="Acme is mentioned.",
            confidence=confidence,
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_geo_response_semantic_fact_rejects_confidence_outside_range(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        GeoResponseSemanticFact(
            factType="topic",
            value="supplier quality",
            confidence=confidence,
        )
