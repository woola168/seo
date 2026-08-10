ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

ALTER TABLE seo_task
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE customer
SET tenant_id = '00000000-0000-4000-8000-000000000001'
WHERE tenant_id IS NULL;

UPDATE seo_task
SET tenant_id = customer.tenant_id
FROM customer
WHERE seo_task.customer_id = customer.id
  AND seo_task.tenant_id IS NULL;

ALTER TABLE customer
    ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE seo_task
    ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE customer
    DROP CONSTRAINT IF EXISTS customer_name_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ux_customer_tenant_name'
    ) THEN
        ALTER TABLE customer
            ADD CONSTRAINT ux_customer_tenant_name UNIQUE (tenant_id, name);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_customer_tenant_status_name
    ON customer (tenant_id, status, name);

CREATE INDEX IF NOT EXISTS ix_seo_task_tenant_customer_id
    ON seo_task (tenant_id, customer_id);

CREATE INDEX IF NOT EXISTS ix_seo_task_tenant_status_name
    ON seo_task (tenant_id, status, name);
