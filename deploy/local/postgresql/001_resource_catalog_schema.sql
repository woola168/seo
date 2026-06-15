CREATE TABLE IF NOT EXISTS customer (
    id uuid PRIMARY KEY,
    name varchar(200) NOT NULL UNIQUE,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS seo_task (
    id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
    name varchar(200) NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_seo_task_customer_id
    ON seo_task (customer_id);

CREATE INDEX IF NOT EXISTS ix_customer_status_name
    ON customer (status, name);

CREATE INDEX IF NOT EXISTS ix_seo_task_status_name
    ON seo_task (status, name);
