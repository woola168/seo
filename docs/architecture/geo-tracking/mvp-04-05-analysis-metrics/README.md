# GEO MVP 第 4、5 點 Module Docs

此資料夾把第 4 點「解析成結構化資料」與第 5 點「核心指標與前期比較」拆成可分工的 module 文件。

## 文件分層

- High level plan：只放 scope、module map、rollout、跨 module 決策。
- Module plan：描述某 module 的責任、流程、依賴、測試方向。
- Spec：描述 interface、use case、API/query shape、公式或錯誤行為。
- Schema：描述 persistence tables、欄位、約束與 indexing 建議。

## Module Tree

```text
README.md
COVERAGE.md
modules/
├─ semantic-analysis/
│  ├─ PLAN.md
│  ├─ SPEC.md
│  └─ SCHEMA.md
├─ citation-normalization/
│  ├─ PLAN.md
│  ├─ SPEC.md
│  └─ SCHEMA.md
├─ metrics-engine/
│  ├─ PLAN.md
│  ├─ SPEC.md
│  └─ SCHEMA.md
├─ dashboard-read-model/
│  ├─ PLAN.md
│  ├─ SPEC.md
│  └─ SCHEMA.md
└─ worker-integration/
   ├─ PLAN.md
   ├─ SPEC.md
   └─ SCHEMA.md
```

## Cross Module Rule

KMindHub 只負責 semantic facts：mention、position、sentiment、semantic labels。Runner references、URL/domain normalization、ownership/source type classification、Used %、Share %、Citation Count、dashboard snapshots 都留在 `geo-analysis` deterministic pipeline。
