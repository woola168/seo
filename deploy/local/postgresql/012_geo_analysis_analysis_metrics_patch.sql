ALTER TABLE geo_run_result_analysis
    ADD COLUMN IF NOT EXISTS analyzer varchar(64),
    ADD COLUMN IF NOT EXISTS analyzer_version varchar(100);

ALTER TABLE geo_run_result_entity_mention
    ADD COLUMN IF NOT EXISTS entity_role varchar(32),
    ADD COLUMN IF NOT EXISTS mentioned boolean,
    ADD COLUMN IF NOT EXISTS first_mention_order integer,
    ADD COLUMN IF NOT EXISTS confidence numeric(5, 4);

ALTER TABLE geo_run_result_statement
    ADD COLUMN IF NOT EXISTS entity_id uuid,
    ADD COLUMN IF NOT EXISTS entity_role varchar(32),
    ADD COLUMN IF NOT EXISTS entity_name varchar(200),
    ADD COLUMN IF NOT EXISTS confidence numeric(5, 4);

CREATE TABLE IF NOT EXISTS geo_response_semantic_fact (
    id uuid PRIMARY KEY,
    analysis_id uuid NOT NULL REFERENCES geo_run_result_analysis(id) ON DELETE CASCADE,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    fact_type varchar(32) NOT NULL,
    value text NOT NULL,
    evidence_text text,
    confidence numeric(5, 4),
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_geo_response_semantic_fact_result
ON geo_response_semantic_fact (run_result_id, fact_type);

CREATE INDEX IF NOT EXISTS ix_geo_response_semantic_fact_analysis
ON geo_response_semantic_fact (analysis_id);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_entity_mention_semantic
ON geo_run_result_entity_mention (run_result_id, entity_role, mentioned);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_entity_mention_analysis
ON geo_run_result_entity_mention (analysis_id);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_statement_semantic
ON geo_run_result_statement (run_result_id, entity_id, sentiment);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_statement_analysis
ON geo_run_result_statement (analysis_id);

CREATE TABLE IF NOT EXISTS geo_run_result_citation_normalization (
    id uuid PRIMARY KEY,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    project_id uuid NOT NULL REFERENCES geo_project(id) ON DELETE CASCADE,
    normalizer_version varchar(100) NOT NULL,
    status varchar(32) NOT NULL,
    error_code varchar(100),
    error_message text,
    skipped_reference_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz,
    CONSTRAINT ux_geo_run_result_citation_normalization_version
        UNIQUE (run_result_id, normalizer_version)
);

CREATE TABLE IF NOT EXISTS geo_run_result_citation (
    id uuid PRIMARY KEY,
    normalization_id uuid NOT NULL REFERENCES geo_run_result_citation_normalization(id) ON DELETE CASCADE,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    reference_id uuid NOT NULL REFERENCES geo_run_result_reference(id) ON DELETE CASCADE,
    url text NOT NULL,
    domain varchar(255) NOT NULL,
    title text,
    position integer NOT NULL,
    ownership varchar(32) NOT NULL,
    source_type varchar(32) NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_citation_normalization_result
ON geo_run_result_citation_normalization (run_result_id, normalizer_version);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_citation_result
ON geo_run_result_citation (run_result_id);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_citation_reference
ON geo_run_result_citation (reference_id);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_citation_domain
ON geo_run_result_citation (domain);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_citation_ownership
ON geo_run_result_citation (ownership);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_citation_source_type
ON geo_run_result_citation (source_type);
