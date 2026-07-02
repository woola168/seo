# Worker Integration Plan

## Responsibility

Worker Integration 負責在 runner result 保存後觸發後續 pipeline：

- Semantic Analysis。
- Citation Normalization。
- Metrics invalidation or aggregation。
- Compensation job for missed analysis/normalization.

此 module 不定義 facts schema，不計算公式，不呼叫 KMindHub directly；它只呼叫 application use cases。

## Current Context

`ProcessQueryRunJobMessage` already calls `geo-tracking` and saves raw results in `geo-analysis`.

Existing saved data:

- `geo_run_result`
- `geo_run_result_reference`

New integration begins after raw result persistence succeeds.

## Option A: Synchronous Trigger

```text
save_tracking_run_result
  -> list saved run result ids
  -> AnalyzeRunResult each id
  -> NormalizeRunResultCitations each id
  -> enqueue or run metric refresh
```

優點：

- Short MVP flow.
- Results are visible sooner.

缺點：

- KMindHub latency can lengthen worker message processing.

## Option B: Analysis Queue

```text
save_tracking_run_result
  -> publish geo.run-results.analysis message
  -> analysis worker calls application use cases
```

優點：

- Better retry and horizontal scaling.
- Worker for runner dispatch stays smaller.

缺點：

- Additional queue and worker.

## MVP Recommendation

第一版先用 Option A，但保留 `AnalyzePendingRunResults` 作為補償路徑。若 KMindHub latency 或 retry 壓力明顯，再切到 Option B；semantic / citation / metrics module interfaces 不需要跟著改。

## Open Decisions

- Analysis trigger 第一版採 worker 同步或獨立 analysis queue。

## Acceptance

- A completed run result can produce raw result, semantic facts, citation facts, and metric snapshot.
- Failed run results are not analyzed.
- Missing analysis/normalization can be recovered by compensation job.
- Default test suite 使用 fake analyzer，不呼叫 live KMindHub 或 live LLM。
