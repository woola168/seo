# Semantic Analysis Spec

## Interface

`geo-analysis` application layer exposes one interface:

```python
class GeoRunResultAnalyzer(Protocol):
    async def analyze(self, command: AnalyzeGeoRunResultCommand) -> GeoRunResultAnalysis:
        ...
```

這是 `geo-analysis` 與 KMindHub 之間的 seam。Caller 只依賴此 interface；HTTP payload mapping、retry、timeout、KMindHub task selection 與 response validation 都屬於 adapter 內部實作。

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

## Tests

- Contract tests for JSON shape.
- Contract rejects invalid sentiment, entity role, negative position, unsupported semantic fact type.
- `AnalyzeRunResult` succeeds with fake analyzer.
- `AnalyzeRunResult` does not call analyzer for failed run result.
- `AnalyzeRunResult` persists failed analysis on analyzer failure.
- KMindHub adapter mapping tests for request casing, response mapping, timeout and error mapping.
