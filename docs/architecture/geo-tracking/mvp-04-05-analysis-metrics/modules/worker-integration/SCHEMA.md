# Worker Integration Schema

MVP 不需要專用 worker integration schema。

Worker integration writes through module-owned persistence:

- Semantic Analysis owns `geo_run_result_analysis`, mention, sentiment, and semantic facts.
- Citation Normalization owns citation normalization and citation facts.
- Metrics Engine owns metric snapshots.

If Option B analysis queue is implemented later, add queue/audit fields in a separate worker/queue migration. Do not mix queue lifecycle columns into semantic facts or metric snapshots.
