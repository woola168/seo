# Citation Normalization Spec

## Use Case: NormalizeRunResultCitations

Input：

- `run_result_id`
- optional `force_renormalize`
- optional `normalizer_version`

流程：

1. Load `GeoRunResultRecord.references`.
2. Load project primary brand `website_url` and configured owned domains.
3. Normalize each URL and domain.
4. Classify `ownership = owned | other`.
5. Classify `source_type`.
6. 在同一個 transaction 保存 `geo_run_result_citation_normalization` 與 `geo_run_result_citation`。

## Ownership Rules

- Domain matching primary brand `website_url` domain or configured `owned_domains` is `owned`.
- Everything else is `other`.
- Competitor domain classification is not MVP; future extension may add `competitor`.
- Do not use LLM to determine ownership.

## Source Type Rules

第一版採 deterministic rules：

- `owned_site`: citation domain is owned.
- `search_result`: provider explicitly marks raw item as search result, if available.
- `social`: domain is in maintained social allowlist.
- `marketplace`: domain is in maintained marketplace allowlist.
- `publisher`: domain is in maintained publisher allowlist.
- `unknown`: no rule matched.

If no owner exists for allowlist maintenance, MVP should only emit `owned_site` and `unknown`.

## URL Normalization Rules

MVP 最小行為：

- Lowercase host.
- Remove default ports.
- Remove URL fragments.
- Preserve path.
- Preserve query string unless product decision says tracking parameters should be stripped.
- Normalize trailing slash consistently.

## Open Decisions

- `owned_domains` 是否只從 primary brand `website_url` 推導，或新增 project-level explicit owned domains table。
- `source_type` 第一版 allowlist 要由誰維護；若沒有維護者，MVP 應只保留 `owned_site` / `unknown`。
- MVP 是否要移除 UTM 與常見 tracking query parameters。

## Test Cases

- Builds citation facts from `geo_run_result_reference`.
- Does not call analyzer / KMindHub.
- Marks own domain as `owned` and `owned_site`.
- Marks unmatched domain as `other` and `unknown`.
- Handles missing references with zero facts.
- Links every citation fact to original `reference_id`.
- Re-run with same `normalizer_version` is idempotent.
