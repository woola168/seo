import pytest
from pydantic import ValidationError
from younilab_geo_tracking_application import (
    ConfirmedProjectIdentity,
    ProjectDiscoveryError,
    ProjectDiscoveryIdentity,
    ProjectDiscoveryInspection,
    ProjectDiscoveryService,
    ProjectInspectionCommand,
    ProjectInspectionResult,
    ProjectSuggestionCommand,
    ProjectSuggestionResult,
    ProjectSuggestionsResult,
    ProviderRequestError,
    QueryAudience,
    Reference,
    TopicInput,
    VerifiedProjectIdentity,
)
from younilab_geo_tracking_domain import MarketType, RegionCode


class ProjectDiscoveryProviderStub:
    def __init__(
        self,
        inspection: ProjectDiscoveryInspection,
        suggestions: ProjectSuggestionResult | None = None,
    ) -> None:
        self.inspection = inspection
        self.suggestions = suggestions or ProjectSuggestionResult(
            search_succeeded=True,
            competitors=[],
            topics=[],
            keywords=[],
        )
        self.research_calls = 0
        self.researched_identity: VerifiedProjectIdentity | None = None
        self.inspection_command: ProjectInspectionCommand | None = None
        self.suggestion_command: ProjectSuggestionCommand | None = None

    async def inspect_url(
        self, command: ProjectInspectionCommand
    ) -> ProjectDiscoveryInspection:
        self.inspection_command = command
        return self.inspection

    async def research_suggestions(
        self,
        command: ProjectSuggestionCommand,
        identity: VerifiedProjectIdentity,
    ) -> ProjectSuggestionResult:
        self.research_calls += 1
        self.suggestion_command = command
        self.researched_identity = identity
        return self.suggestions


class FailingProjectDiscoveryProvider(ProjectDiscoveryProviderStub):
    async def inspect_url(
        self, command: ProjectInspectionCommand
    ) -> ProjectDiscoveryInspection:
        raise ProviderRequestError("project_url_inspection_failed")


@pytest.mark.anyio
async def test_discovery_stops_before_research_when_url_retrieval_fails() -> None:
    provider = ProjectDiscoveryProviderStub(
        ProjectDiscoveryInspection(
            retrieval_succeeded=False,
            retrieved_url=None,
            identity=None,
        )
    )
    service = ProjectDiscoveryService(provider)

    with pytest.raises(ProjectDiscoveryError) as exc_info:
        await service.inspect(_inspection_command())

    assert exc_info.value.code == "project_url_retrieval_failed"
    assert provider.research_calls == 0


@pytest.mark.anyio
async def test_discovery_stops_before_research_when_context_is_insufficient() -> None:
    provider = ProjectDiscoveryProviderStub(
        ProjectDiscoveryInspection(
            retrieval_succeeded=True,
            retrieved_url="https://github.com/pleomax0730/agent-settings",
            identity=ProjectDiscoveryIdentity(
                project_name="agent-settings",
                project_description="只有 repository 名稱，缺少用途說明。",
                project_type="repository",
                core_offerings=[],
                target_audiences=[],
                sufficient_context=False,
                limitation="README 沒有提供專案用途。",
            ),
        )
    )
    service = ProjectDiscoveryService(provider)

    with pytest.raises(ProjectDiscoveryError) as exc_info:
        await service.inspect(_inspection_command())

    assert exc_info.value.code == "insufficient_project_context"
    assert provider.research_calls == 0


@pytest.mark.anyio
async def test_discovery_requires_at_least_one_core_offering() -> None:
    provider = ProjectDiscoveryProviderStub(
        ProjectDiscoveryInspection(
            retrieval_succeeded=True,
            retrieved_url="https://example.com/",
            identity=ProjectDiscoveryIdentity(
                project_name="Example",
                project_description="頁面只有公司名稱。",
                project_type="company",
                core_offerings=[],
                target_audiences=[],
                sufficient_context=True,
                limitation="",
            ),
        )
    )

    with pytest.raises(ProjectDiscoveryError) as exc_info:
        await ProjectDiscoveryService(provider).inspect(_inspection_command())

    assert exc_info.value.code == "insufficient_project_context"
    assert provider.research_calls == 0


@pytest.mark.anyio
async def test_discovery_rejects_blank_verified_identity_fields() -> None:
    provider = ProjectDiscoveryProviderStub(
        ProjectDiscoveryInspection(
            retrieval_succeeded=True,
            retrieved_url="https://example.com/",
            identity=ProjectDiscoveryIdentity(
                project_name=" ",
                project_description=" ",
                project_type="company",
                core_offerings=[" "],
                target_audiences=[],
                sufficient_context=True,
                limitation="",
            ),
        )
    )

    with pytest.raises(ProjectDiscoveryError) as exc_info:
        await ProjectDiscoveryService(provider).inspect(_inspection_command())

    assert exc_info.value.code == "insufficient_project_context"
    assert provider.research_calls == 0


@pytest.mark.anyio
async def test_inspection_returns_editable_project_identity() -> None:
    provider = ProjectDiscoveryProviderStub(
        ProjectDiscoveryInspection(
            retrieval_succeeded=True,
            retrieved_url="https://www.kaiser.com.tw/",
            identity=ProjectDiscoveryIdentity(
                project_name="港香蘭藥廠股份有限公司",
                project_description="位於台灣的中藥製藥公司。",
                project_type="company",
                core_offerings=["科學中藥", "中藥保健產品"],
                target_audiences=["中醫醫療院所", "一般消費者"],
                sufficient_context=True,
                limitation="",
            ),
        ),
    )

    result = await ProjectDiscoveryService(provider).inspect(_inspection_command())

    assert result == ProjectInspectionResult(
        source_url="https://www.kaiser.com.tw/",
        retrieved_url="https://www.kaiser.com.tw/",
        project_name="港香蘭藥廠股份有限公司",
        project_description="位於台灣的中藥製藥公司。",
        project_type="company",
        core_offerings=["科學中藥", "中藥保健產品"],
        target_audiences=["中醫醫療院所", "一般消費者"],
    )
    assert provider.research_calls == 0


@pytest.mark.anyio
async def test_suggestions_use_confirmed_identity_from_the_user() -> None:
    provider = ProjectDiscoveryProviderStub(
        _successful_inspection(),
        suggestions=ProjectSuggestionResult(
            search_succeeded=True,
            competitors=["順天堂藥廠", "勝昌製藥"],
            topics=[
                TopicInput(
                    name="科學中藥",
                    description="聚焦製程、品質與產品使用情境。",
                )
            ],
            keywords=["科學中藥", "中藥濃縮粉"],
            references=[Reference(url="https://example.com/source", title="市場資料")],
        ),
    )

    result = await ProjectDiscoveryService(provider).suggest(_suggestion_command())

    assert provider.research_calls == 1
    assert provider.researched_identity == VerifiedProjectIdentity(
        source_url="https://www.kaiser.com.tw/",
        retrieved_url="https://www.kaiser.com.tw/",
        project_name="港香蘭",
        project_description="使用者確認的科學中藥品牌描述。",
        project_type="company",
        core_offerings=("科學中藥",),
        target_audiences=("一般消費者",),
    )
    assert result == ProjectSuggestionsResult(
        competitors=["順天堂藥廠", "勝昌製藥"],
        topics=[
            TopicInput(
                name="科學中藥",
                description="聚焦製程、品質與產品使用情境。",
            )
        ],
        keywords=["科學中藥", "中藥濃縮粉"],
        references=[Reference(url="https://example.com/source", title="市場資料")],
    )
    assert result.competitors == ["順天堂藥廠", "勝昌製藥"]
    assert result.topics[0].name == "科學中藥"
    assert result.keywords == ["科學中藥", "中藥濃縮粉"]
    assert result.references[0].title == "市場資料"


@pytest.mark.anyio
async def test_suggestions_reject_blank_confirmed_identity() -> None:
    provider = ProjectDiscoveryProviderStub(_successful_inspection())
    confirmed = _suggestion_command().confirmed_project.model_copy(
        update={"project_description": " ", "core_offerings": [" "]}
    )
    command = _suggestion_command().model_copy(update={"confirmed_project": confirmed})

    with pytest.raises(ProjectDiscoveryError) as exc_info:
        await ProjectDiscoveryService(provider).suggest(command)

    assert exc_info.value.code == "invalid_confirmed_project"
    assert provider.research_calls == 0


@pytest.mark.anyio
async def test_discovery_rejects_suggestions_without_google_search() -> None:
    provider = ProjectDiscoveryProviderStub(
        _successful_inspection(),
        suggestions=ProjectSuggestionResult(
            search_succeeded=False,
            competitors=["未查證競品"],
            topics=[],
            keywords=[],
        ),
    )

    with pytest.raises(ProjectDiscoveryError) as exc_info:
        await ProjectDiscoveryService(provider).suggest(_suggestion_command())

    assert exc_info.value.code == "project_market_research_not_grounded"


@pytest.mark.anyio
async def test_discovery_cleans_and_limits_suggestions_before_returning() -> None:
    provider = ProjectDiscoveryProviderStub(
        _successful_inspection(),
        suggestions=ProjectSuggestionResult(
            search_succeeded=True,
            competitors=[
                "港香蘭藥廠股份有限公司",
                "順天堂藥廠",
                " 順天堂藥廠 ",
                "勝昌製藥",
                "科達製藥",
            ],
            topics=[
                TopicInput(name="科學中藥", description="製程與品質。"),
                TopicInput(name=" 科學中藥 ", description="重複項目。"),
                TopicInput(name="缺少描述", description=" "),
                TopicInput(name="中藥保健", description="保健產品與需求。"),
                TopicInput(name="藥廠品質", description="GMP 與品質管理。"),
            ],
            keywords=[
                "港香蘭保健食品",
                "科學中藥",
                " 科學中藥 ",
                "順天堂藥廠評價",
                "中藥濃縮粉",
                "中藥代工",
            ],
        ),
    )
    command = _suggestion_command().model_copy(
        update={"competitor_count": 2, "topic_count": 2, "keyword_count": 2}
    )

    result = await ProjectDiscoveryService(provider).suggest(command)

    assert result.competitors == ["順天堂藥廠", "勝昌製藥"]
    assert [topic.name for topic in result.topics] == ["科學中藥", "中藥保健"]
    assert result.keywords == ["科學中藥", "中藥濃縮粉"]


@pytest.mark.parametrize(
    "project_url",
    [
        "http://localhost./",
        "http://foo.localhost/",
        "http://example.local./",
    ],
)
def test_project_discovery_rejects_local_hostname_variants(
    project_url: str,
) -> None:
    with pytest.raises(ValidationError):
        ProjectInspectionCommand(
            project_url=project_url,
            language="zh-TW",
        )


@pytest.mark.anyio
async def test_discovery_translates_provider_failures() -> None:
    provider = FailingProjectDiscoveryProvider(_successful_inspection())

    with pytest.raises(ProjectDiscoveryError) as exc_info:
        await ProjectDiscoveryService(provider).inspect(_inspection_command())

    assert exc_info.value.code == "project_url_inspection_failed"


def _successful_inspection() -> ProjectDiscoveryInspection:
    return ProjectDiscoveryInspection(
        retrieval_succeeded=True,
        retrieved_url="https://www.kaiser.com.tw/",
        identity=ProjectDiscoveryIdentity(
            project_name="港香蘭",
            project_description="位於台灣的中藥製藥公司。",
            project_type="company",
            core_offerings=["科學中藥"],
            target_audiences=["一般消費者"],
            sufficient_context=True,
            limitation="",
        ),
    )


def _inspection_command() -> ProjectInspectionCommand:
    return ProjectInspectionCommand(
        project_url="https://www.kaiser.com.tw/",
        language="zh-TW",
    )


def _suggestion_command() -> ProjectSuggestionCommand:
    return ProjectSuggestionCommand(
        confirmed_project=ConfirmedProjectIdentity(
            source_url="https://www.kaiser.com.tw/",
            retrieved_url="https://www.kaiser.com.tw/",
            project_name="港香蘭",
            project_description="使用者確認的科學中藥品牌描述。",
            project_type="company",
            core_offerings=["科學中藥"],
            target_audiences=["一般消費者"],
        ),
        region=RegionCode.TAIWAN,
        language="zh-TW",
        market_type=MarketType.B2C,
        audience=QueryAudience(
            name="B2C 消費",
            description="正在了解中藥產品的一般消費者",
        ),
    )
