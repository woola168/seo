UPDATE geo_project AS project
SET customer_id = task.customer_id,
    updated_at = now()
FROM seo_task AS task
WHERE project.seo_task_id = task.id
  AND project.customer_id IS NULL
  AND project.tenant_id = task.tenant_id;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM geo_project
        WHERE seo_task_id IS NOT NULL
          AND customer_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'geo_project customer_id backfill is required before removing seo_task_id';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS geo_daily_run_batch (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    business_date date NOT NULL,
    scheduled_for timestamptz NOT NULL,
    status varchar(32) NOT NULL,
    candidate_count integer NOT NULL DEFAULT 0,
    job_count integer NOT NULL DEFAULT 0,
    budget_enforced boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_daily_run_batch_project_date
        UNIQUE (project_id, business_date)
);

ALTER TABLE geo_query_run_job
    ADD COLUMN IF NOT EXISTS batch_id uuid
        REFERENCES geo_daily_run_batch(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS source varchar(32) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS execution_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE geo_query_run_job
    DROP CONSTRAINT IF EXISTS ux_geo_query_run_job_scheduled_identity;

DROP INDEX IF EXISTS ux_geo_query_run_job_scheduled_identity;

CREATE UNIQUE INDEX ux_geo_query_run_job_scheduled_identity
    ON geo_query_run_job (query_id, platform_id, scheduled_for)
    WHERE source = 'scheduled';

CREATE INDEX IF NOT EXISTS ix_geo_daily_run_batch_date
    ON geo_daily_run_batch (business_date, status);

CREATE INDEX IF NOT EXISTS ix_geo_query_run_job_scheduler_pickup
    ON geo_query_run_job (source, status, scheduled_for, next_retry_at);

UPDATE geo_ai_platform
SET status = 'paused', updated_at = now()
WHERE code = 'google_aio'
  AND status = 'active';
