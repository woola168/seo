# PostgreSQL Seed Data

Seed 與 schema baseline 分開執行：

- `002_access_control_demo_seed.sql`：僅供 local/demo Access Control 資料。
- `provider_pricing_rates.sql`：GEO provider list-price 成本估算使用的版本化系統費率，可安全重跑。

Production 不得執行 demo seed。GEO platform、tenant 與管理員 provisioning 仍由各環境既有流程處理。
