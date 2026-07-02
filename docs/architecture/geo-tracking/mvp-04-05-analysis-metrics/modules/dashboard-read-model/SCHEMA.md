# Dashboard Read Model Schema

MVP 不需要專用 dashboard persistence。

Dashboard read APIs should query:

- `geo_metric_snapshot` from Metrics Engine.
- `geo_run_result_analysis`, `geo_run_result_entity_mention`, `geo_sentiment_statement`, `geo_response_semantic_fact` from Semantic Analysis.
- `geo_run_result_citation` from Citation Normalization.
- Existing run result tables: `geo_run_result`, `geo_run_result_reference`.

如果 read latency 成為問題，後續再加 materialized read-model tables。MVP 不應在尚未量測前先新增這類表。
