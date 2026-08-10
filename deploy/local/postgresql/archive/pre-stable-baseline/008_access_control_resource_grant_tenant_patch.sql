ALTER TABLE customer_access_grant
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

ALTER TABLE task_access_grant
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE customer_access_grant grant_row
SET tenant_id = user_account.tenant_id
FROM user_account
WHERE grant_row.user_id = user_account.id
  AND grant_row.tenant_id IS NULL;

UPDATE task_access_grant grant_row
SET tenant_id = user_account.tenant_id
FROM user_account
WHERE grant_row.user_id = user_account.id
  AND grant_row.tenant_id IS NULL;

ALTER TABLE customer_access_grant
    ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE task_access_grant
    ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_customer_access_grant_tenant'
    ) THEN
        ALTER TABLE customer_access_grant
            ADD CONSTRAINT fk_customer_access_grant_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenant(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_task_access_grant_tenant'
    ) THEN
        ALTER TABLE task_access_grant
            ADD CONSTRAINT fk_task_access_grant_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenant(id);
    END IF;
END $$;

ALTER TABLE customer_access_grant
    DROP CONSTRAINT IF EXISTS ux_user_customer_grant;

ALTER TABLE task_access_grant
    DROP CONSTRAINT IF EXISTS ux_user_task_grant;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ux_tenant_user_customer_grant'
    ) THEN
        ALTER TABLE customer_access_grant
            ADD CONSTRAINT ux_tenant_user_customer_grant
            UNIQUE (tenant_id, user_id, customer_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ux_tenant_user_task_grant'
    ) THEN
        ALTER TABLE task_access_grant
            ADD CONSTRAINT ux_tenant_user_task_grant
            UNIQUE (tenant_id, user_id, task_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_customer_access_grant_tenant_id
    ON customer_access_grant (tenant_id);

CREATE INDEX IF NOT EXISTS ix_task_access_grant_tenant_id
    ON task_access_grant (tenant_id);
