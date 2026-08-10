BEGIN;

ALTER TABLE geo_query_run_job
    ADD COLUMN IF NOT EXISTS business_date date
        GENERATED ALWAYS AS
            ((scheduled_for AT TIME ZONE 'Asia/Taipei')::date) STORED,
    ADD COLUMN IF NOT EXISTS is_daily_slot_owner boolean;

WITH ranked_jobs AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY query_id, platform_id, business_date
            ORDER BY created_at, id
        ) AS daily_rank
    FROM geo_query_run_job
)
UPDATE geo_query_run_job AS job
SET is_daily_slot_owner = ranked_jobs.daily_rank = 1
FROM ranked_jobs
WHERE job.id = ranked_jobs.id;

ALTER TABLE geo_query_run_job
    ALTER COLUMN is_daily_slot_owner SET DEFAULT true,
    ALTER COLUMN is_daily_slot_owner SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_geo_query_run_job_daily_slot
    ON geo_query_run_job (query_id, platform_id, business_date)
    WHERE is_daily_slot_owner = true;

COMMIT;
