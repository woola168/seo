ALTER TABLE geo_project
    ALTER COLUMN customer_id DROP NOT NULL;

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

CREATE INDEX IF NOT EXISTS ix_geo_query_research_run_project_created
    ON geo_query_research_run (project_id, created_at DESC);

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

CREATE INDEX IF NOT EXISTS ix_geo_query_generation_run_project_created
    ON geo_query_generation_run (project_id, created_at DESC);

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

CREATE INDEX IF NOT EXISTS ix_geo_query_draft_generation_run
    ON geo_query_draft (generation_run_id, created_at);

CREATE INDEX IF NOT EXISTS ix_geo_query_draft_project
    ON geo_query_draft (project_id);

CREATE TABLE IF NOT EXISTS geo_query_draft_selection (
    id uuid PRIMARY KEY,
    draft_id uuid NOT NULL REFERENCES geo_query_draft(id) ON DELETE CASCADE,
    selection_status varchar(32) NOT NULL,
    query_id uuid REFERENCES geo_query(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_geo_query_draft_selection_draft_created
    ON geo_query_draft_selection (draft_id, created_at);
