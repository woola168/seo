BEGIN;

CREATE TABLE IF NOT EXISTS geo_project_query_settings (
    project_id uuid PRIMARY KEY REFERENCES geo_project(id) ON DELETE CASCADE,
    research_provider varchar(64) NOT NULL,
    run_provider varchar(64) NOT NULL,
    keywords jsonb NOT NULL DEFAULT '[]'::jsonb,
    market_type varchar(32) NOT NULL,
    max_queries integer NOT NULL,
    audience_name varchar(200) NOT NULL,
    audience_description text NOT NULL,
    intent_category varchar(100) NOT NULL,
    intent_description text NOT NULL,
    should_mention_own_brand boolean NOT NULL,
    should_mention_competitor boolean NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_geo_project_query_settings_research_provider
        CHECK (research_provider IN ('gemini')),
    CONSTRAINT ck_geo_project_query_settings_run_provider
        CHECK (run_provider IN ('gemini')),
    CONSTRAINT ck_geo_project_query_settings_keywords
        CHECK (jsonb_typeof(keywords) = 'array' AND jsonb_array_length(keywords) <= 10),
    CONSTRAINT ck_geo_project_query_settings_market_type
        CHECK (market_type IN ('b2c', 'b2b_procurement')),
    CONSTRAINT ck_geo_project_query_settings_max_queries
        CHECK (max_queries BETWEEN 1 AND 40),
    CONSTRAINT ck_geo_project_query_settings_audience_name
        CHECK (btrim(audience_name) <> ''),
    CONSTRAINT ck_geo_project_query_settings_audience_description
        CHECK (btrim(audience_description) <> '' AND length(audience_description) <= 2000),
    CONSTRAINT ck_geo_project_query_settings_intent_category
        CHECK (btrim(intent_category) <> ''),
    CONSTRAINT ck_geo_project_query_settings_intent_description
        CHECK (btrim(intent_description) <> '' AND length(intent_description) <= 2000)
);

COMMIT;
