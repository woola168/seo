# GEO MVP 第 4、5 點 Module Docs

此資料夾把第 4 點「解析成結構化資料」與第 5 點「核心指標與前期比較」拆成可分工的 module 文件。

## 如何開始讀

第一次接手請照這個順序讀：

1. 先讀 high level plan：[`../mvp-04-05-analysis-metrics-implementation-plan.md`](../mvp-04-05-analysis-metrics-implementation-plan.md)
   - 目的：理解 MVP 第 4、5 點的 scope、non-goals、module map、rollout、open decisions。
   - 不要從 schema 開始讀，否則容易只看到資料表而漏掉 module 責任。
2. 再讀本 README。
   - 目的：理解文件分層、module 依賴與建議開發順序。
3. 再讀 [`COVERAGE.md`](COVERAGE.md)。
   - 目的：確認 high level plan 的每個要求已由哪些 module 文件承接。
4. 若要開始切實作，讀 [`PHASED-IMPLEMENTATION-PLAN.md`](PHASED-IMPLEMENTATION-PLAN.md)。
   - 目的：依照小階段推進，避免一次同時改 contracts、schema、repository、API、worker。
5. 最後依你負責的 module 讀該 module 的 `PLAN.md`、`SPEC.md`、`SCHEMA.md`。
   - `PLAN.md`：先看，理解責任、依賴、rollout。
   - `SPEC.md`：實作 use case、interface、API/read model、公式、錯誤行為時看。
   - `SCHEMA.md`：寫 migration、SQLModel、repository adapter 時看。

若只要快速了解全貌，讀 high level plan + 本 README + `COVERAGE.md` 即可。若要開始實作，必須讀對應 module 的三份文件。

## 文件分層

- High level plan：只放 scope、module map、rollout、跨 module 決策。
- Module plan：描述某 module 的責任、流程、依賴、測試方向。
- Spec：描述 interface、use case、API/query shape、公式或錯誤行為。
- Schema：描述 persistence tables、欄位、約束與 indexing 建議。

## 建議開發順序

這些 module 不是完全線性，但有明確依賴關係。

### 第一波：可平行

1. `semantic-analysis`
   - 先定 `GeoRunResultAnalyzer` seam、contracts、facts schema。
   - 產出 mention / position / sentiment / semantic facts。
   - Metrics Engine 需要這些 facts 才能計算 Visibility、SOV、Position、Mentions、Sentiment Count。
2. `citation-normalization`
   - 可與 `semantic-analysis` 平行。
   - 只依賴既有 `geo_run_result_reference`，不依賴 KMindHub。
   - 產出 citation facts，供 Citation Count、Used %、Share % 使用。

### 第二波：依賴 facts 穩定後

3. `metrics-engine`
   - 依賴 semantic facts 與 citation facts 的 schema/contract。
   - 負責 deterministic formula、daily snapshot、前期比較。
   - 不應在 facts schema 尚未穩定前開始重度實作，否則公式與 repository query 容易返工。

### 第三波：可部分提前，但完整功能依賴 Metrics Engine

4. `dashboard-read-model`
   - 可先定 API shape 與 mock read model。
   - 完整串接需等 Metrics Engine snapshot 與 facts query 穩定。
5. `worker-integration`
   - 可先做 skeleton 與 internal endpoint。
   - 完整串接需等 `AnalyzeRunResult`、`NormalizeRunResultCitations`、`CalculateGeoMetrics` 都存在。

建議執行方式：

```text
semantic-analysis       ┐
                        ├─ metrics-engine ── dashboard-read-model
citation-normalization  ┘              └── worker-integration
```

如果人力有限，最保守順序是：

```text
semantic-analysis
-> citation-normalization
-> metrics-engine
-> dashboard-read-model
-> worker-integration
```

如果多人平行，優先讓 `semantic-analysis` 與 `citation-normalization` 同時啟動。

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
