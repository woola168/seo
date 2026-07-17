CREATE TABLE IF NOT EXISTS provider_request (
    id uuid PRIMARY KEY,
    operation_id uuid NOT NULL,
    request_number integer NOT NULL CHECK (request_number > 0),
    request_kind varchar(32) NOT NULL,
    platform_code varchar(64) NOT NULL,
    provider_code varchar(64) NOT NULL,
    provider_operation varchar(64) NOT NULL,
    use_case varchar(64) NOT NULL,
    source_service varchar(64) NOT NULL,
    model varchar(128),
    uses_grounding boolean NOT NULL DEFAULT false,
    status varchar(16) NOT NULL,
    started_at timestamptz NOT NULL,
    completed_at timestamptz,
    duration_ms integer CHECK (duration_ms >= 0),
    http_status integer,
    error_code varchar(128),
    error_type varchar(128),
    tenant_id uuid,
    project_id uuid,
    job_id uuid,
    query_id uuid,
    run_request_id uuid,
    CONSTRAINT ux_provider_request_operation_number
        UNIQUE (operation_id, request_number),
    CONSTRAINT ck_provider_request_status
        CHECK (status IN ('started', 'succeeded', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_provider_request_started_at
    ON provider_request (started_at);
CREATE INDEX IF NOT EXISTS ix_provider_request_platform_started
    ON provider_request (platform_code, started_at);
CREATE INDEX IF NOT EXISTS ix_provider_request_provider_started
    ON provider_request (provider_code, started_at);
CREATE INDEX IF NOT EXISTS ix_provider_request_use_case_started
    ON provider_request (use_case, started_at);
CREATE INDEX IF NOT EXISTS ix_provider_request_tenant_started
    ON provider_request (tenant_id, started_at);
CREATE INDEX IF NOT EXISTS ix_provider_request_job
    ON provider_request (job_id) WHERE job_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_provider_request_query
    ON provider_request (query_id) WHERE query_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_provider_request_run_request
    ON provider_request (run_request_id) WHERE run_request_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_provider_request_started_status
    ON provider_request (started_at) WHERE status = 'started';
