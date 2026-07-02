# Citation Normalization Schema

Add these tables in a future patch migration, for example:

```text
deploy/local/postgresql/006_geo_analysis_analysis_metrics_patch.sql
```

## `geo_run_result_citation_normalization`

保存單筆 citation normalization lifecycle。這是 `geo-analysis` deterministic pipeline record，不是 KMindHub analysis record。

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | normalization id |
| `run_result_id` | `uuid` | FK to `geo_run_result.id` |
| `project_id` | `uuid` | FK to `geo_project.id` |
| `normalizer_version` | `varchar(100)` | URL/domain normalization rule version |
| `status` | `varchar(32)` | `pending`, `completed`, `failed` |
| `error_code` | `varchar(100)` | optional |
| `error_message` | `text` | optional |
| `created_at` | `timestamptz` | created time |
| `completed_at` | `timestamptz` | completed time |

Constraint:

```sql
UNIQUE (run_result_id, normalizer_version)
```

## `geo_run_result_citation`

保存 normalized citation facts。Citation Count、Used %、Share % 都從此表計算。

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | citation fact id |
| `normalization_id` | `uuid` | FK to `geo_run_result_citation_normalization.id` |
| `run_result_id` | `uuid` | FK to `geo_run_result.id` |
| `reference_id` | `uuid` | nullable FK to `geo_run_result_reference.id` |
| `url` | `text` | normalized URL |
| `domain` | `varchar(255)` | normalized domain |
| `title` | `text` | title snapshot |
| `position` | `integer` | reference order |
| `ownership` | `varchar(32)` | `owned`, `other` |
| `source_type` | `varchar(32)` | `owned_site`, `search_result`, `publisher`, `social`, `marketplace`, `unknown` |
| `created_at` | `timestamptz` | created time |

建議索引：

```sql
CREATE INDEX ix_geo_run_result_citation_result ON geo_run_result_citation (run_result_id);
CREATE INDEX ix_geo_run_result_citation_domain ON geo_run_result_citation (domain);
CREATE INDEX ix_geo_run_result_citation_ownership ON geo_run_result_citation (ownership);
CREATE INDEX ix_geo_run_result_citation_source_type ON geo_run_result_citation (source_type);
```
