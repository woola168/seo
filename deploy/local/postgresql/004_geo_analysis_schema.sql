CREATE TABLE IF NOT EXISTS geo_project (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    customer_id uuid,
    seo_task_id uuid,
    name varchar(200) NOT NULL,
    default_region varchar(16) NOT NULL DEFAULT 'TW',
    default_language varchar(16) NOT NULL DEFAULT 'zh-TW',
    status varchar(32) NOT NULL,
    daily_run_budget integer NOT NULL DEFAULT 0,
    daily_cost_budget numeric(12, 6),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz
);

CREATE INDEX IF NOT EXISTS ix_geo_project_tenant_id
    ON geo_project (tenant_id);

CREATE INDEX IF NOT EXISTS ix_geo_project_customer_id
    ON geo_project (customer_id);

CREATE INDEX IF NOT EXISTS ix_geo_project_status
    ON geo_project (status);

CREATE TABLE IF NOT EXISTS tenant_kmindhub_workspace_mapping (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    display_name varchar(200) NOT NULL,
    provisioning_mode varchar(32) NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_tenant_kmindhub_workspace_mapping_tenant UNIQUE (tenant_id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_kmindhub_workspace_mapping_tenant_id
    ON tenant_kmindhub_workspace_mapping (tenant_id);

CREATE INDEX IF NOT EXISTS ix_tenant_kmindhub_workspace_mapping_status
    ON tenant_kmindhub_workspace_mapping (status);

CREATE TABLE IF NOT EXISTS tenant_kmindhub_extraction_task_mapping (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    task_key varchar(100) NOT NULL,
    schema_version integer NOT NULL,
    kmindhub_task_id uuid NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_tenant_kmindhub_extraction_task_mapping_version
        UNIQUE (tenant_id, task_key, schema_version)
);

CREATE INDEX IF NOT EXISTS ix_tenant_kmindhub_extraction_task_mapping_tenant
    ON tenant_kmindhub_extraction_task_mapping (tenant_id);

CREATE INDEX IF NOT EXISTS ix_tenant_kmindhub_extraction_task_mapping_status
    ON tenant_kmindhub_extraction_task_mapping (status);

CREATE TABLE IF NOT EXISTS geo_market (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    region varchar(16) NOT NULL,
    language varchar(16) NOT NULL,
    market_name varchar(100) NOT NULL,
    prompt_locale_hint text NOT NULL DEFAULT '',
    serp_gl varchar(16),
    serp_hl varchar(16),
    serp_location varchar(200),
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_market_scope UNIQUE (project_id, region, language)
);

CREATE TABLE IF NOT EXISTS geo_entity (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    entity_type varchar(32) NOT NULL,
    name varchar(200) NOT NULL,
    website_url text,
    description text NOT NULL DEFAULT '',
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_entity_scope_type_name UNIQUE (project_id, entity_type, name)
);

CREATE TABLE IF NOT EXISTS geo_entity_alias (
    id uuid PRIMARY KEY,
    entity_id uuid NOT NULL REFERENCES geo_entity(id) ON DELETE CASCADE,
    alias varchar(200) NOT NULL,
    match_type varchar(32) NOT NULL DEFAULT 'exact',
    created_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_entity_alias UNIQUE (entity_id, alias)
);

CREATE TABLE IF NOT EXISTS geo_topic (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    name varchar(200) NOT NULL,
    description text NOT NULL DEFAULT '',
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_topic_scope_name UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS geo_query (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    topic_id uuid REFERENCES geo_topic(id) ON DELETE SET NULL,
    query_text text NOT NULL,
    region varchar(16) NOT NULL,
    language varchar(16) NOT NULL,
    market_type varchar(32) NOT NULL DEFAULT 'b2b_procurement',
    intent varchar(32),
    buyer_stage varchar(32),
    is_branded boolean NOT NULL DEFAULT false,
    priority varchar(32) NOT NULL DEFAULT 'normal',
    status varchar(32) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz
);

ALTER TABLE geo_query
    ADD COLUMN IF NOT EXISTS market_type varchar(32) NOT NULL DEFAULT 'b2b_procurement';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_geo_query_market_type'
    ) THEN
        ALTER TABLE geo_query
            ADD CONSTRAINT ck_geo_query_market_type
            CHECK (market_type IN ('b2c', 'b2b_procurement'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_geo_query_project_status
    ON geo_query (project_id, status);

CREATE INDEX IF NOT EXISTS ix_geo_query_topic_id
    ON geo_query (topic_id);

CREATE INDEX IF NOT EXISTS ix_geo_query_region_language
    ON geo_query (region, language);

CREATE TABLE IF NOT EXISTS geo_query_keyword (
    id uuid PRIMARY KEY,
    query_id uuid NOT NULL REFERENCES geo_query(id) ON DELETE CASCADE,
    keyword varchar(200) NOT NULL,
    search_volume integer,
    region varchar(16) NOT NULL,
    language varchar(16) NOT NULL,
    source varchar(64) NOT NULL DEFAULT 'manual',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_query_research_run (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    provider varchar(64) NOT NULL,
    status varchar(32) NOT NULL,
    request_payload jsonb NOT NULL,
    research_context text,
    searched_keywords jsonb NOT NULL DEFAULT '[]'::jsonb,
    source_urls jsonb NOT NULL DEFAULT '[]'::jsonb,
    error_code varchar(100),
    error_message text,
    created_at timestamptz NOT NULL,
    completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS geo_query_generation_run (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    provider varchar(64) NOT NULL,
    status varchar(32) NOT NULL,
    request_payload jsonb NOT NULL,
    error_code varchar(100),
    error_message text,
    created_at timestamptz NOT NULL,
    completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS geo_query_draft (
    id uuid PRIMARY KEY,
    generation_run_id uuid NOT NULL REFERENCES geo_query_generation_run(id) ON DELETE CASCADE,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    topic_id uuid REFERENCES geo_topic(id) ON DELETE SET NULL,
    topic_name varchar(200) NOT NULL DEFAULT '',
    query_text text NOT NULL,
    keywords jsonb NOT NULL DEFAULT '[]'::jsonb,
    region varchar(16) NOT NULL,
    language varchar(16) NOT NULL,
    market_type varchar(32) NOT NULL,
    intent varchar(32),
    is_branded boolean NOT NULL DEFAULT false,
    status varchar(32) NOT NULL DEFAULT 'draft',
    selection_status varchar(32),
    accepted_query_id uuid REFERENCES geo_query(id) ON DELETE SET NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_query_draft_selection (
    id uuid PRIMARY KEY,
    draft_id uuid NOT NULL REFERENCES geo_query_draft(id) ON DELETE CASCADE,
    selection_status varchar(32) NOT NULL,
    query_id uuid REFERENCES geo_query(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_ai_platform (
    id uuid PRIMARY KEY,
    code varchar(64) NOT NULL UNIQUE,
    display_name varchar(100) NOT NULL,
    provider_type varchar(32) NOT NULL,
    default_model varchar(100),
    supports_citations boolean NOT NULL DEFAULT false,
    supports_grounding boolean NOT NULL DEFAULT false,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_query_platform (
    id uuid PRIMARY KEY,
    query_id uuid NOT NULL REFERENCES geo_query(id) ON DELETE CASCADE,
    platform_id uuid NOT NULL REFERENCES geo_ai_platform(id) ON DELETE RESTRICT,
    model varchar(100),
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_query_platform UNIQUE (query_id, platform_id)
);

CREATE TABLE IF NOT EXISTS geo_query_schedule (
    id uuid PRIMARY KEY,
    query_id uuid NOT NULL REFERENCES geo_query(id) ON DELETE CASCADE,
    platform_id uuid NOT NULL REFERENCES geo_ai_platform(id) ON DELETE RESTRICT,
    frequency varchar(32) NOT NULL,
    priority varchar(32) NOT NULL DEFAULT 'normal',
    timezone varchar(64) NOT NULL DEFAULT 'Asia/Taipei',
    next_run_at timestamptz,
    last_scheduled_at timestamptz,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_query_schedule UNIQUE (query_id, platform_id)
);

CREATE INDEX IF NOT EXISTS ix_geo_query_schedule_due
    ON geo_query_schedule (status, next_run_at, priority);

CREATE TABLE IF NOT EXISTS geo_query_run_job (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    query_id uuid NOT NULL REFERENCES geo_query(id) ON DELETE CASCADE,
    platform_id uuid NOT NULL REFERENCES geo_ai_platform(id) ON DELETE RESTRICT,
    schedule_id uuid REFERENCES geo_query_schedule(id) ON DELETE SET NULL,
    job_type varchar(32) NOT NULL DEFAULT 'scheduled_run',
    priority varchar(32) NOT NULL DEFAULT 'normal',
    scheduled_for timestamptz NOT NULL,
    status varchar(32) NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 3,
    next_retry_at timestamptz,
    dedupe_key varchar(200) NOT NULL UNIQUE,
    dispatch_backend varchar(32),
    dispatch_message_id varchar(200),
    external_run_id varchar(200),
    last_error_code varchar(100),
    last_error_message text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_geo_query_run_job_pickup
    ON geo_query_run_job (status, scheduled_for, priority);

CREATE INDEX IF NOT EXISTS ix_geo_query_run_job_query_platform
    ON geo_query_run_job (query_id, platform_id);

CREATE TABLE IF NOT EXISTS geo_message_dispatch_log (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES geo_query_run_job(id) ON DELETE CASCADE,
    message_backend varchar(32) NOT NULL,
    destination varchar(200) NOT NULL,
    message_id varchar(200),
    payload jsonb NOT NULL,
    publish_status varchar(32) NOT NULL,
    published_at timestamptz,
    error_message text,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_worker_lease (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES geo_query_run_job(id) ON DELETE CASCADE,
    worker_id varchar(100) NOT NULL,
    leased_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    released_at timestamptz,
    release_reason varchar(64)
);

CREATE TABLE IF NOT EXISTS geo_job_dispatch_event (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES geo_query_run_job(id) ON DELETE CASCADE,
    event_type varchar(64) NOT NULL,
    occurred_at timestamptz NOT NULL,
    actor varchar(100) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS geo_external_run_reference (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES geo_query_run_job(id) ON DELETE CASCADE,
    external_system varchar(100) NOT NULL,
    external_run_id varchar(200) NOT NULL,
    external_status varchar(64) NOT NULL,
    callback_received_at timestamptz,
    result_location text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_run_request (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES geo_query_run_job(id) ON DELETE CASCADE,
    tracking_run_request_id varchar(200) NOT NULL,
    seo_task_id uuid,
    provider varchar(64) NOT NULL,
    timing varchar(32) NOT NULL,
    status varchar(32) NOT NULL,
    error_code varchar(100),
    error_message text,
    request_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS geo_run_result (
    id uuid PRIMARY KEY,
    run_request_id uuid NOT NULL REFERENCES geo_run_request(id) ON DELETE CASCADE,
    job_id uuid NOT NULL REFERENCES geo_query_run_job(id) ON DELETE CASCADE,
    tracking_result_id varchar(200) NOT NULL,
    query_id uuid NOT NULL REFERENCES geo_query(id) ON DELETE CASCADE,
    provider varchar(64) NOT NULL,
    surface varchar(100) NOT NULL,
    model varchar(100) NOT NULL,
    region varchar(16) NOT NULL,
    language varchar(16) NOT NULL,
    status varchar(32) NOT NULL,
    raw_response text NOT NULL DEFAULT '',
    error text,
    run_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_run_result_reference (
    id uuid PRIMARY KEY,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    url text NOT NULL,
    title text,
    domain varchar(255),
    position integer NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_geo_run_request_job_id
ON geo_run_request (job_id);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_job_run_at
ON geo_run_result (job_id, run_at DESC);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_query_run_at
ON geo_run_result (query_id, run_at DESC);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_reference_result
ON geo_run_result_reference (run_result_id, position);

CREATE TABLE IF NOT EXISTS geo_run_result_analysis (
    id uuid PRIMARY KEY,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    task_key varchar(100) NOT NULL,
    schema_version integer NOT NULL,
    status varchar(32) NOT NULL,
    summary text,
    overall_sentiment varchar(32),
    theme varchar(200),
    kmindhub_commit_batch_id varchar(200),
    kmindhub_item_id varchar(200),
    error_code varchar(100),
    error_message text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz,
    CONSTRAINT ux_geo_run_result_analysis_version
        UNIQUE (run_result_id, task_key, schema_version)
);

CREATE TABLE IF NOT EXISTS geo_run_result_entity_mention (
    id uuid PRIMARY KEY,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    analysis_id uuid NOT NULL REFERENCES geo_run_result_analysis(id) ON DELETE CASCADE,
    entity_id uuid,
    entity_name varchar(200) NOT NULL,
    entity_type varchar(32) NOT NULL,
    mention_count integer NOT NULL,
    sentiment varchar(32) NOT NULL,
    evidence_text text NOT NULL DEFAULT '',
    kmindhub_item_id varchar(200),
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_run_result_statement (
    id uuid PRIMARY KEY,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    analysis_id uuid NOT NULL REFERENCES geo_run_result_analysis(id) ON DELETE CASCADE,
    statement_text text NOT NULL,
    theme varchar(200) NOT NULL DEFAULT '',
    sentiment varchar(32) NOT NULL,
    subject_entity_name varchar(200),
    evidence_text text NOT NULL DEFAULT '',
    kmindhub_item_id varchar(200),
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS geo_run_result_citation_classification (
    id uuid PRIMARY KEY,
    run_result_reference_id uuid NOT NULL REFERENCES geo_run_result_reference(id) ON DELETE CASCADE,
    analysis_id uuid NOT NULL REFERENCES geo_run_result_analysis(id) ON DELETE CASCADE,
    classification varchar(32) NOT NULL,
    matched_entity_id uuid,
    matched_domain varchar(255),
    confidence numeric(5, 4),
    source varchar(64) NOT NULL DEFAULT 'rule_based',
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_analysis_result
ON geo_run_result_analysis (run_result_id, status);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_entity_mention_result
ON geo_run_result_entity_mention (run_result_id, entity_type, entity_name);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_statement_result
ON geo_run_result_statement (run_result_id);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_citation_classification_reference
ON geo_run_result_citation_classification (run_result_reference_id, classification);
