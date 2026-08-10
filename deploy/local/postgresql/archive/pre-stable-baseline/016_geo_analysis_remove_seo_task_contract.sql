BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM geo_project
        WHERE seo_task_id IS NOT NULL
          AND customer_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'geo_project customer_id must be backfilled before removing seo_task_id';
    END IF;
END $$;

ALTER TABLE geo_run_request
    DROP COLUMN IF EXISTS seo_task_id;

ALTER TABLE geo_project
    DROP COLUMN IF EXISTS seo_task_id;

COMMIT;
