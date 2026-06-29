import pytest
from pydantic import ValidationError

from younilab_seo.geo_analysis.application import QueryIntent, QueryResearchCommand


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
