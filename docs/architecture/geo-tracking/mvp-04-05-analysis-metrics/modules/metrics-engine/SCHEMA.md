# Metrics Engine Schema

## `geo_metric_snapshot`

保存 aggregate metric snapshots，避免 dashboard 每次 request 都掃 raw facts。

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | snapshot id |
| `project_id` | `uuid` | FK to `geo_project.id` |
| `scope_type` | `varchar(32)` | `project`, `topic`, `query`, `provider`, `entity`, `citation_url`, `citation_domain`, `sentiment` |
| `scope_id` | `uuid` | nullable; topic/query/platform/entity id |
| `scope_key` | `varchar(500)` | nullable; URL/domain or other non-UUID scope |
| `region` | `varchar(16)` | nullable |
| `language` | `varchar(16)` | nullable |
| `provider` | `varchar(64)` | nullable |
| `period_start` | `timestamptz` | inclusive |
| `period_end` | `timestamptz` | exclusive |
| `comparison_start` | `timestamptz` | nullable |
| `comparison_end` | `timestamptz` | nullable |
| `metric_name` | `varchar(64)` | `visibility`, `sov`, `average_position`, `mentions`, `citation_count`, `used_percent`, `share_percent`, `sentiment_count` |
| `metric_value` | `numeric(18,6)` | metric value |
| `numerator` | `numeric(18,6)` | optional |
| `denominator` | `numeric(18,6)` | optional |
| `comparison_value` | `numeric(18,6)` | optional |
| `delta_value` | `numeric(18,6)` | optional |
| `delta_unit` | `varchar(16)` | `pp`, `count`, `rank` |
| `calculated_at` | `timestamptz` | calculation time |

MVP 可先用這張 generic snapshot table。等查詢壓力或 UI 形狀穩定後，再拆成 `geo_query_metric_snapshot`、`geo_citation_metric_snapshot`、`geo_sentiment_metric_snapshot`。

## Open Decisions

- Metric snapshot 是否先用 generic `geo_metric_snapshot`，或直接拆成 query/citation/sentiment snapshots。
- 若使用 generic table，nullable scope 欄位的唯一性要使用 PostgreSQL 15+ `NULLS NOT DISTINCT`、generated key，或 partial unique indexes。

建議唯一性：

```sql
UNIQUE (
    project_id,
    scope_type,
    scope_id,
    scope_key,
    region,
    language,
    provider,
    period_start,
    period_end,
    comparison_start,
    comparison_end,
    metric_name
)
```

Implementation note: nullable columns in unique constraints need careful PostgreSQL handling. Use `NULLS NOT DISTINCT` on PostgreSQL 15+ or a generated key / partial unique indexes.
