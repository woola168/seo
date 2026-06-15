# Resource Catalog 資料庫結構

Resource Catalog 使用獨立的 `resource_catalog` PostgreSQL，schema 來源為
`deploy/local/postgresql/001_resource_catalog_schema.sql`。

## `customer`

- `id`：UUID 主鍵。
- `name`：唯一的客戶名稱。
- `status`：`active` 或 `archived`。
- `created_at`、`updated_at`：建立與異動時間。

## `seo_task`

- `id`：UUID 主鍵。
- `customer_id`：所屬客戶外鍵。
- `name`：任務名稱。
- `status`：`active` 或 `archived`。
- `created_at`、`updated_at`：建立與異動時間。

Access Control 僅保存客戶與任務 UUID Grant，不可直接存取本資料庫。
