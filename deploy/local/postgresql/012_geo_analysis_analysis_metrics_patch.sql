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
