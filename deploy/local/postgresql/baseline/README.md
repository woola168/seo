# PostgreSQL Stable Baseline

這個目錄保存目前 stable 版本的新環境初始化 schema。三份 SQL 必須分別對對應的 database 執行：

- `access_control.sql`：Access Control database。
- `resource_catalog.sql`：Resource Catalog database。
- `geo_analysis.sql`：GEO Analysis schema；本機 compose 目前與 Resource Catalog 共用同一個 PostgreSQL database。

Baseline 只供空白 database 初始化，不是既有環境的升級 migration。已完成 pre-stable patches 的環境不可重跑 baseline。後續 schema 變更從 `deploy/local/postgresql/027_*.sql` 開始，以此 stable baseline 為前置版本。

Baseline 不包含 demo account、default tenant 或 GEO platform seed。Provider pricing rate 是成本估算需要的系統資料，需另外執行 `../seed/provider_pricing_rates.sql`。
