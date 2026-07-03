BEGIN;

CREATE TABLE IF NOT EXISTS tenant (
    id uuid PRIMARY KEY,
    code varchar(80) NOT NULL UNIQUE,
    name varchar(200) NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    disabled_at timestamptz NULL
);

INSERT INTO tenant (
    id,
    code,
    name,
    status,
    created_at,
    updated_at
)
VALUES (
    '00000000-0000-4000-8000-000000000001',
    'default',
    'Default Tenant',
    'active',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    updated_at = CURRENT_TIMESTAMP;

ALTER TABLE department
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

ALTER TABLE user_account
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

ALTER TABLE role
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE department
SET tenant_id = '00000000-0000-4000-8000-000000000001'
WHERE tenant_id IS NULL;

UPDATE user_account
SET tenant_id = '00000000-0000-4000-8000-000000000001'
WHERE tenant_id IS NULL;

UPDATE role
SET tenant_id = '00000000-0000-4000-8000-000000000001'
WHERE tenant_id IS NULL;

ALTER TABLE department
    ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE user_account
    ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE role
    ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE department
    DROP CONSTRAINT IF EXISTS department_name_key;

ALTER TABLE user_account
    DROP CONSTRAINT IF EXISTS ux_user_tenant_email;

ALTER TABLE role
    DROP CONSTRAINT IF EXISTS role_name_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_department_tenant'
    ) THEN
        ALTER TABLE department
            ADD CONSTRAINT fk_department_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenant(id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_account_tenant'
    ) THEN
        ALTER TABLE user_account
            ADD CONSTRAINT fk_user_account_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenant(id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_role_tenant'
    ) THEN
        ALTER TABLE role
            ADD CONSTRAINT fk_role_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenant(id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ux_department_tenant_name'
    ) THEN
        ALTER TABLE department
            ADD CONSTRAINT ux_department_tenant_name UNIQUE (tenant_id, name);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'user_account_email_key'
    ) THEN
        ALTER TABLE user_account
            ADD CONSTRAINT user_account_email_key UNIQUE (email);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ux_role_tenant_name'
    ) THEN
        ALTER TABLE role
            ADD CONSTRAINT ux_role_tenant_name UNIQUE (tenant_id, name);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_department_tenant_id
    ON department (tenant_id);

CREATE INDEX IF NOT EXISTS ix_user_account_tenant_id
    ON user_account (tenant_id);

CREATE INDEX IF NOT EXISTS ix_role_tenant_id
    ON role (tenant_id);

COMMIT;
