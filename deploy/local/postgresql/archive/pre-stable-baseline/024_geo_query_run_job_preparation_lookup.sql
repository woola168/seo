BEGIN;

CREATE INDEX IF NOT EXISTS ix_geo_query_run_job_project_preparing
    ON geo_query_run_job (project_id, business_date, status)
    WHERE is_daily_slot_owner = true;

COMMIT;
