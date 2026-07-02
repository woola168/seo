# Worker Integration Spec

## Use Case: AnalyzePendingRunResults

Responsibility: batch process completed run results that lack semantic analysis or citation normalization.

流程：

1. List completed run results missing analysis or citation normalization.
2. For each run result:
   - call `AnalyzeRunResult` when semantic analysis is missing.
   - call `NormalizeRunResultCitations` when citation normalization is missing.
   - trigger metrics invalidation or aggregation.
3. Persist per-result failure state without stopping the full batch.

## Worker Hook

After `save_tracking_run_result` persists completed results:

1. For every saved completed `run_result_id`, call Semantic Analysis use case.
2. For every saved completed `run_result_id`, call Citation Normalization use case.
3. Trigger Metrics Engine refresh for affected project/query/topic/provider/region/language scopes.

Failed run results:

- Save raw failure state.
- Do not call analyzer.
- Do not create citation normalization unless references exist and product decides failed references should still be visible. MVP default: skip.

## Internal Endpoints

These endpoints are for workers or internal operations. MVP does not need to expose them to the public frontend.

```text
POST /api/geo/run-results/{runResultId}/analysis
POST /api/geo/projects/{projectId}/analysis/backfill
POST /api/geo/projects/{projectId}/metrics/calculate
```

Endpoint behavior：

- Analysis trigger validates run result id and status.
- Backfill calls `AnalyzePendingRunResults`.
- Metrics calculate calls Metrics Engine for selected period and filters.

## Error Handling

- Semantic analysis failure persists `geo_run_result_analysis.status = failed`.
- Citation normalization failure 會保存 `geo_run_result_citation_normalization.status = failed`。
- Metrics refresh failure should be retryable and should not erase facts.
- Batch compensation should log failures and continue.

## Tests

- Completed result triggers semantic analysis and citation normalization.
- Failed result does not call analyzer.
- Analyzer timeout records failed analysis.
- Citation normalization failure records failed normalization.
- Compensation job processes missing analysis.
- Metrics refresh is triggered after facts are saved.
