CREATE TABLE IF NOT EXISTS tenant_kmindhub_workspace_mapping (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    display_name varchar(200) NOT NULL,
    provisioning_mode varchar(32) NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ux_tenant_kmindhub_workspace_mapping_tenant'
    ) THEN
        ALTER TABLE tenant_kmindhub_workspace_mapping
            ADD CONSTRAINT ux_tenant_kmindhub_workspace_mapping_tenant UNIQUE (tenant_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_tenant_kmindhub_workspace_mapping_tenant_id
    ON tenant_kmindhub_workspace_mapping (tenant_id);

CREATE INDEX IF NOT EXISTS ix_tenant_kmindhub_workspace_mapping_status
    ON tenant_kmindhub_workspace_mapping (status);
