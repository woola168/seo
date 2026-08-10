CREATE TABLE IF NOT EXISTS customer (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    name varchar(200) NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_customer_tenant_name UNIQUE (tenant_id, name)
);

CREATE TABLE IF NOT EXISTS seo_task (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
    name varchar(200) NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_customer_tenant_status_name
    ON customer (tenant_id, status, name);

CREATE INDEX IF NOT EXISTS ix_seo_task_tenant_customer_id
    ON seo_task (tenant_id, customer_id);

CREATE INDEX IF NOT EXISTS ix_seo_task_tenant_status_name
    ON seo_task (tenant_id, status, name);
