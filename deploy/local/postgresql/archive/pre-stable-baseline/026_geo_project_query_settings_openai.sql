BEGIN;

ALTER TABLE geo_project_query_settings
    DROP CONSTRAINT IF EXISTS ck_geo_project_query_settings_research_provider,
    ADD CONSTRAINT ck_geo_project_query_settings_research_provider
        CHECK (research_provider IN ('gemini', 'openai'));

COMMIT;
