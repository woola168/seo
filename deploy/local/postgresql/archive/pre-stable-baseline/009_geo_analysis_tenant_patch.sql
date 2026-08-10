ALTER TABLE geo_project
    ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE geo_project
SET tenant_id = '00000000-0000-4000-8000-000000000001'
WHERE tenant_id IS NULL;

ALTER TABLE geo_project
    ALTER COLUMN tenant_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_geo_project_tenant_id
    ON geo_project (tenant_id);

CREATE INDEX IF NOT EXISTS ix_geo_project_tenant_status
    ON geo_project (tenant_id, status);
