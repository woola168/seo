# Younilab SEO Python Package

`younilab-seo` 是 SEO 後台的 Python package，集中放置目前後端共用的 bounded contexts。

## 結構

```text
src/younilab_seo/
  access_control/
    domain/
    application/
    infrastructure/
    contracts/
  resource_catalog/
    domain/
    application/
    infrastructure/
  geo_analysis/
    domain/
    application/
    infrastructure/
  shared/
```

## 設計原則

- 單一 distribution package：`younilab-seo`。
- Python import namespace：`younilab_seo`。
- 以 bounded context 優先分層，避免把不同業務的 domain model 混在同一個 `domain/`。
- `shared/` 只放穩定且跨 context 重複使用的基礎能力。

## 驗證

```bash
uv run --package younilab-seo pytest packages/younilab-seo/tests
```
