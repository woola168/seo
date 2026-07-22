BEGIN;

ALTER TABLE geo_run_result_analysis
    ADD COLUMN IF NOT EXISTS analyzer_request_payload jsonb,
    ADD COLUMN IF NOT EXISTS analyzer_response_payload jsonb,
    ADD COLUMN IF NOT EXISTS validation_failures jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMIT;
