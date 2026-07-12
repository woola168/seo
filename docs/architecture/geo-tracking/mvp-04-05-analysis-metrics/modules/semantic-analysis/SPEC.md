# Semantic Analysis Spec

## Interface

`geo-analysis` application layer exposes one interface:

```python
class GeoRunResultAnalyzer(Protocol):
    async def analyze(self, command: AnalyzeGeoRunResultCommand) -> GeoRunResultAnalysis:
        ...
```

這是 `geo-analysis` 與 KMindHub 之間的 seam。Caller 只依賴此 interface；HTTP payload mapping、retry、timeout、KMindHub task selection 與 response validation 都屬於 adapter 內部實作。

Focused evidence repair 使用另一個 application port：

```python
class EvidenceTextRepairer(Protocol):
    async def repair(
        self,
        command: EvidenceTextRepairCommand,
    ) -> EvidenceTextRepairResult:
        ...
```

`EvidenceTextRepairCommand` 只包含 raw response 與無法逐字回溯的 `item_index` / `wrong_evidence_text`。這是 KMindHub extraction 之後、必要時才發生的第二次 Gemini LLM 呼叫；Gemini infrastructure adapter 只用 structured output 選擇 request-scoped source block ID，不重跑 extraction，也不產生 evidence 文字。Application result 才包含由程式取回的 untouched `evidence_text`，block ID 不保存也不進入 domain model。

## AnalyzeGeoRunResultCommand

```python
class AnalyzeGeoRunResultCommand(ContractModel):
    run_result_id: UUID
    project_id: UUID
    query_id: UUID
    query_text: str
    topic_id: UUID | None = None
    topic_name: str | None = None
    topic_description: str | None = None
    provider: str
    surface: str
    model: str
    region: str
    language: str
    raw_response: str
    entities: GeoAnalysisEntityContext
```

```python
class GeoAnalysisEntityContext(ContractModel):
    own_brand: GeoAnalysisEntityInput
    competitors: list[GeoAnalysisEntityInput] = Field(default_factory=list)

class GeoAnalysisEntityInput(ContractModel):
    entity_id: UUID
    entity_role: str  # own_brand | competitor
    name: str
    website_url: str | None = None
```

## GeoRunResultAnalysis

```python
class GeoRunResultAnalysis(ContractModel):
    run_result_id: UUID
    analyzer: str
    analyzer_version: str | None = None
    status: str  # completed | failed
    entity_mentions: list[GeoEntityMentionFact] = Field(default_factory=list)
    sentiments: list[GeoSentimentFact] = Field(default_factory=list)
    semantic_facts: list[GeoResponseSemanticFact] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
```

Mention fact：

```python
class GeoEntityMentionFact(ContractModel):
    entity_id: UUID
    entity_role: str  # own_brand | competitor
    entity_name: str
    mentioned: bool
    first_mention_order: int | None = None
    evidence_text: str | None = None
    confidence: float | None = None
```

Sentiment fact：

```python
class GeoSentimentFact(ContractModel):
    entity_id: UUID
    entity_role: str
    entity_name: str
    sentiment: str  # positive | negative
    theme: str
    statement: str
    evidence_text: str | None = None
    confidence: float | None = None
```

Semantic fact：

```python
class GeoResponseSemanticFact(ContractModel):
    fact_type: str  # product | service | topic | common_statement
    value: str
    evidence_text: str | None = None
    confidence: float | None = None
```

## Use Case: AnalyzeRunResult

Input：

- `run_result_id`
- optional `force_reanalyze`
- optional `analyzer_version`

流程：

1. Load `GeoRunResultRecord`.
2. Load query, topic, project, active own brand, active competitors.
3. Build `AnalyzeGeoRunResultCommand`.
4. 呼叫 `GeoRunResultAnalyzer`。
5. Persist `geo_run_result_analysis`, mentions, sentiments, semantic facts in one transaction.
6. Trigger metrics invalidation or enqueue aggregation job after completed analysis.

Errors:

- Missing run result: application error.
- Non-completed run result: skipped or rejected.
- KMindHub timeout: persist failed analysis, allow retry.
- KMindHub response validation failed: persist failed analysis with error evidence.

## Repository Port

```python
class GeoRunResultAnalysisRepository(Protocol):
    async def get_run_result_context(
        self,
        run_result_id: UUID,
    ) -> GeoRunResultAnalysisContext | None:
        ...

    async def save_analysis(
        self,
        analysis: GeoRunResultAnalysisRecord,
    ) -> None:
        ...

    async def list_unanalyzed_run_results(
        self,
        limit: int,
    ) -> list[UUID]:
        ...
```

此 port 應與既有 setup/job repository 分開，只負責 raw result 到 semantic facts 的 persistence。

## Rules

- One `run_result_id + entity_id` mention fact per analysis.
- Same entity mentioned multiple times in one response counts once.
- `first_mention_order` exists only when `mentioned = true`.
- Ranking order only considers own brand and project-selected competitors.
- Sentiment MVP supports `positive` and `negative` only.
- Statement-level sentiment is the default; response-level or entity-level sentiment can be derived from statement facts.
- Semantic `topic` fact describes what the response discusses; it does not mutate `geo_topic`.
- KMindHub `verification.passed = false` 必須直接拒絕，不進 focused repair。
- Evidence 以 Unicode NFKC 與 whitespace normalization 後，必須是 raw response 的 contiguous substring。
- Repair result 的 item indexes 必須與 failures 完全同序且無缺漏、重複或額外項目。
- 所有 repair result 驗證完成後才能原子套用；任一失敗不得修改任何 preview item。
- Repair 不重跑 KMindHub extraction，不修復 entity、sentiment、fact type 或其他 schema 錯誤。

## Tests

- Contract tests for JSON shape.
- Contract rejects invalid sentiment, entity role, negative position, unsupported semantic fact type.
- `AnalyzeRunResult` succeeds with fake analyzer.
- `AnalyzeRunResult` does not call analyzer for failed run result.
- `AnalyzeRunResult` persists failed analysis on analyzer failure.
- KMindHub adapter mapping tests for request casing, response mapping, timeout and error mapping.
- Focused repair tests for exact source mapping, Markdown preservation, malformed output, unknown block、順序與 atomicity。
- Live regression 使用 23 筆歷史失敗 response、46 個 invalid evidence 驗證正式 adapter，接受標準為 100% exact provenance。
