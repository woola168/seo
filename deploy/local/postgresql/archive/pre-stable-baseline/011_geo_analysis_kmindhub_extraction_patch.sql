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
