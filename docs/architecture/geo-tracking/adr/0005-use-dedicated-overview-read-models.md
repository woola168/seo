# 使用專用 Overview Read Models

- 狀態：Accepted
- 日期：2026-07-27
- 範圍：`geo-analysis` Overview 報表與回答清單

## 背景

Overview 原本由 application use case 分別讀取 Query、Topic、metrics facts 與整個 Project 的 run results，再於 Python 內完成 metadata 篩選、join、排序及 offset pagination。

資料量小時可以正常運作，但只要求一頁回答時仍會載入整個 Project 的結果與 references。報表與回答清單也各自組合相同的日期、Topic、Provider、地區及 metadata 條件，容易產生不同的篩選結果。

## 決策

Overview 使用兩個 application read model seam：

1. `OverviewReportReadModel`
   - 接收 tenant、Project、報表期間、篩選條件、台北營業日與 citation normalizer version。
   - 回傳 `GeoOverviewReportSource`，內容包含已篩選的 formula source、Query／Topic 顯示維度、filter options 與 `isPreparing`。
2. `OverviewResponseReadModel`
   - 接收 tenant、Project 與 `GeoOverviewResponsePageQuery`。
   - 直接回傳已篩選、排序及分頁的 `GeoOverviewResponsePage` 與完整 filtered total。

`GetGeoOverviewReport` 只負責呼叫 report read model、執行既有 `CalculateGeoMetricFormulas`，再組裝 HTTP 所需的 view model。`ListGeoOverviewResponses` 只保留輸入驗證與 read model 委派。

## Adapter 責任

`GeoApiStore` 與 `PostgresGeoAnalysisRepository` 都直接實作兩個 read model。

PostgreSQL adapter 負責：

- tenant 與 Project scope。
- 目前期間與前一個等長比較期間。
- Topic 多選、Provider 多選、地區、metadata industry 與 metadata type。
- 最新 semantic analysis 狀態與自有品牌提及狀態。
- completed time 排序、filtered total 與 offset pagination。
- 只針對目前頁面的回答讀取 reference 與 sentiment 計數。

Metrics calculator 不移入 SQL。Visibility、Mentions、SOV、平均排名、Citation 與 Sentiment 公式仍由既有純 application calculator 計算。

## Filter Options

使用者篩選只限制報表資料，不限制選單內容：

- Topic 與 metadata options 來自整個 Project 的 Query／Topic 維度。
- Provider 與地區 options 來自目前期間內未套用使用者條件的 completed run results。
- 同一維度採 OR，不同維度採 AND。

## 保留行為

- HTTP endpoint、query parameter、JSON response 與 Problem Details 不變。
- 目前期間使用半開區間：`periodStart <= runAt < periodEnd`。
- 比較期間為目前期間之前的等長區間。
- `isPreparing` 使用台北時區營業日。
- `mentionStatus` 支援 `all`、`mentioned`、`not_mentioned`；analysis 未完成或失敗時為 `unknown`，只出現在 `all`。
- 回答清單維持 completed time 由新到舊、offset pagination 與 `pageSize <= 100`。
- 本決策不新增 database schema、migration、index、cache、snapshot 或 materialized view。

## 移除項目

- 移除短期使用的 `CompatibilityOverviewReportReadModel`。
- 移除 Overview 專用的 `OverviewReadPersistence` 全量讀取 port。
- `list_project_run_results` 仍保留在 run lifecycle 的 `RunResultReadPersistence`，供既有 Job／Result API 使用，但 Overview 不再呼叫它。

## 測試與閱讀順序

建議依下列順序閱讀：

1. `application/contracts.py`：`GeoOverviewQuery`、`GeoOverviewReportSource`、`GeoOverviewResponsePageQuery` 與 response contracts。
2. `application/interfaces/overview_read.py`：兩個公開 read model seams。
3. `application/use_cases/overview_report.py`：calculator orchestration 與輸入驗證。
4. `apps/geo-analysis-api/.../store.py`：in-memory observable behavior。
5. `infrastructure/persistence/postgres/repository.py`：資料庫端篩選、排序與分頁。

測試分成四層：application use case、in-memory adapter、真實 PostgreSQL adapter、HTTP contract。RabbitMQ、Gemini、Google AIO 與 KMindHub 不參與此唯讀路徑。

## 影響

好處：

- Overview use case 不再知道 persistence join、metadata filter 或分頁細節。
- PostgreSQL 只載入目前報表與當頁回答所需資料。
- Report 與 response page 的篩選責任集中於 adapter，較容易維持一致。
- 後續可在不修改 HTTP 或 calculator 的情況下加入 query tuning、cache 或 snapshot。

代價：

- PostgreSQL adapter 需要維護 Overview 專用查詢。
- In-memory adapter 必須實作相同 observable behavior，不能只依賴 generic CRUD methods。
