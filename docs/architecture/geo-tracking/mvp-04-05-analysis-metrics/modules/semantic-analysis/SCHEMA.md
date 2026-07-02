# Semantic Analysis Schema

Add these tables in a future patch migration, for example:

```text
deploy/local/postgresql/006_geo_analysis_analysis_metrics_patch.sql
```

## `geo_run_result_analysis`

保存單筆 run result 的 semantic analysis lifecycle。

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | analysis id |
| `run_result_id` | `uuid` | FK to `geo_run_result.id` |
| `project_id` | `uuid` | FK to `geo_project.id` |
| `analyzer` | `varchar(64)` | `kmindhub` |
| `analyzer_version` | `varchar(100)` | adapter / prompt / task version |
| `status` | `varchar(32)` | `pending`, `completed`, `failed` |
| `error_code` | `varchar(100)` | optional |
| `error_message` | `text` | optional |
| `created_at` | `timestamptz` | created time |
| `completed_at` | `timestamptz` | completed time |

Constraint:

```sql
UNIQUE (run_result_id, analyzer, analyzer_version)
```

## `geo_run_result_entity_mention`

保存 entity mention facts。Visibility、SOV、Mentions、Position 都從此表計算。

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | mention fact id |
| `analysis_id` | `uuid` | FK to `geo_run_result_analysis.id` |
| `run_result_id` | `uuid` | FK to `geo_run_result.id` |
| `entity_id` | `uuid` | FK to `geo_entity.id` |
| `entity_role` | `varchar(32)` | `own_brand`, `competitor` |
| `entity_name` | `varchar(200)` | analysis-time snapshot |
| `mentioned` | `boolean` | whether entity is mentioned |
| `first_mention_order` | `integer` | first appearance order among own brand + configured competitors |
| `evidence_text` | `text` | supporting excerpt |
| `confidence` | `numeric(5,4)` | optional |
| `created_at` | `timestamptz` | created time |

規則：

- Unique logical fact: `run_result_id + entity_id`.
- Same entity mentioned multiple times in one response counts once.
- `first_mention_order` only exists when `mentioned = true`.

## `geo_sentiment_statement`

保存品牌相關 sentiment statements。MVP 只支援 positive / negative。

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | sentiment fact id |
| `analysis_id` | `uuid` | FK to `geo_run_result_analysis.id` |
| `run_result_id` | `uuid` | FK to `geo_run_result.id` |
| `entity_id` | `uuid` | FK to `geo_entity.id` |
| `entity_role` | `varchar(32)` | `own_brand`, `competitor` |
| `sentiment` | `varchar(16)` | `positive`, `negative` |
| `theme` | `varchar(200)` | theme |
| `statement` | `text` | normalized statement |
| `evidence_text` | `text` | source excerpt |
| `confidence` | `numeric(5,4)` | optional |
| `created_at` | `timestamptz` | created time |

## `geo_response_semantic_fact`

保存 response detail 需要的 product、service、topic、common statement facts。

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | semantic fact id |
| `analysis_id` | `uuid` | FK to `geo_run_result_analysis.id` |
| `run_result_id` | `uuid` | FK to `geo_run_result.id` |
| `fact_type` | `varchar(32)` | `product`, `service`, `topic`, `common_statement` |
| `value` | `text` | normalized label or statement |
| `evidence_text` | `text` | source excerpt |
| `confidence` | `numeric(5,4)` | optional |
| `created_at` | `timestamptz` | created time |

規則：

- This table does not participate in the six core KPI formulas.
- It supports response detail display and future recommendation modules.
