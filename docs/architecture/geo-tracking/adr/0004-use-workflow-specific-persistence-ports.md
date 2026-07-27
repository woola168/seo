# 使用 Workflow-Specific Persistence Ports

- 狀態：Accepted
- 日期：2026-07-27
- 範圍：`geo-analysis` 後端 application 與 persistence boundary

## 背景

`geo-analysis` 原本以 `GeoAnalysisRepository` 承接 Project 設定、Query Planning、Run lifecycle、Semantic Analysis、Citation、Metrics、Overview 與 KMindHub mapping。任一 use case 只使用其中少數方法，卻必須依賴整個 interface。

這使新增或修改單一 workflow 時，經常同時修改大型 interface、Postgres adapter、in-memory adapter、composition 與大型 fake。問題不是單一檔案太長，而是 application boundary 沒有表達實際的 workflow 責任。

## 決策

Application persistence interface 依 workflow 定義，不依資料表定義。每個 use case 只依賴完成自身行為所需的 port。

目前 ports 分組如下：

| Workflow | Persistence port |
| --- | --- |
| Semantic Analysis | `SemanticAnalysisPersistence` |
| Citation Normalization | `CitationNormalizationPersistence` |
| Metrics / Overview | `MetricsReadPersistence`、`OverviewReadPersistence` |
| Run lifecycle | `RunDispatchPersistence`、`RunCallbackPersistence`、`RunExecutionPersistence`、`RunResultReadPersistence`、`RunJobManagementPersistence`、`RunSchedulerPersistence` |
| Query Planning | `QueryPlanningPersistence` |
| Project setup | `ProjectSetupPersistence`、`EntityCatalogPersistence`、`QueryCatalogPersistence` |
| KMindHub | `KMindHubWorkspaceMappingPersistence`、`KMindHubTaskMappingPersistence`、`LegacyAnalysisExtractionPersistence` |

Port 可以包含跨表 context load 或原子保存操作。Application caller 不自行組合 SQL join、tenant filter、active status、claim、idempotency 或 transaction。

## Runtime 組裝

正式環境仍使用一個 `PostgresGeoAnalysisRepository` 實例，本機與 HTTP tests 仍可使用一個 `GeoApiStore` 實例。這兩個 adapter 可共用 session factory、transaction helper、row mapping 與 in-memory state。

`composition.py` 負責把同一個 adapter 明確視為不同 workflow port，再分別注入 use case。共享 adapter 是 infrastructure implementation detail，不再由 application layer 以大型 façade 表達。

## 測試規則

- Application test 使用只具備該 workflow 所需方法的小型 fake。
- Runtime-checkable protocol tests 驗證 Postgres adapter 可直接實作各 port。
- 既有 package、API、worker 與 scheduler tests 保留外部行為、授權、tenant scope、idempotency 與狀態轉移。
- 不測試 private SQL helper、檔案位置或 class inheritance。

## 影響

好處：

- Use case 的依賴範圍可直接從 constructor 看出。
- 新增 workflow 行為時，不需要擴張所有 fake。
- Context load 與原子保存責任集中在 adapter，較容易維持 tenant 與 transaction 規則。
- 可在不拆 deployable service 的情況下，逐步深化 module boundary。

代價：

- `application/interfaces/` 會有較多小檔案。
- Composition root 需要明確組裝多個 ports。
- `PostgresGeoAnalysisRepository` 與 `GeoApiStore` 目前仍是大型 concrete adapters；後續可依維護需要切 implementation 檔案，但檔案切分不是本 ADR 的完成條件。

## 不包含

- 不修改 database schema 或 migration。
- 不修改 HTTP endpoint、JSON contract、queue payload 或 metrics 公式。
- 不改 Overview pagination、KMindHub evidence validation 或 provider 行為。
- 不建立 per-table repositories。
