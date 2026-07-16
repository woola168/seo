ALTER TABLE geo_run_request
    DROP COLUMN IF EXISTS seo_task_id;

ALTER TABLE geo_project
    DROP COLUMN IF EXISTS seo_task_id;
