# Citation Normalization Plan

## Responsibility

Citation Normalization 負責把 runner 已保存的 `geo_run_result_reference` 轉成 normalized citation facts：

- normalized URL。
- normalized domain。
- title snapshot。
- reference position。
- ownership：`owned` / `other`。
- source type：`owned_site` / `search_result` / `publisher` / `social` / `marketplace` / `unknown`。

此 module 不呼叫 KMindHub，不解析 raw response，不計算 KPI。

## Architecture

```text
NormalizeRunResultCitations
  -> load GeoRunResultRecord.references
  -> load project primary brand website_url / owned domains
  -> normalize URL and domain
  -> classify ownership
  -> classify source_type
  -> save citation normalization status + citation facts
```

## Why It Stays In Geo Analysis

Runner references are already structured provider output. URL parsing, domain normalization, ownership classification, source type allowlists, Used %, Share %, Citation Count, By URL, and By Domain are deterministic data processing problems. Sending them to KMindHub would make metrics harder to audit and more expensive without adding semantic value.

## Rollout Slice

1. Add citation normalization lifecycle schema.
2. Add normalized citation facts schema.
3. Implement URL/domain normalizer.
4. Implement ownership rule.
5. Implement source type rule.
6. Add use case and repository tests.

## Acceptance

- Runner references can produce citation facts.
- 不新增 KMindHub dependency。
- Missing references produce completed normalization with zero citation facts.
- Used % / Share % / Citation Count can be computed from citation facts.
- Unknown source type returns `unknown`.
