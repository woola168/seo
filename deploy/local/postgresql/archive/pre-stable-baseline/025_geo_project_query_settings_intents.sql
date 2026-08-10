BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM geo_project_query_settings
        WHERE lower(btrim(intent_category)) NOT IN (
            '導航', '導航型', 'navigational',
            '資訊', '資訊型', 'informational',
            '商業', '商業評估', 'commercial', 'commercial_investigation',
            '交易', '交易型', 'transactional'
        )
    ) THEN
        RAISE EXCEPTION
            'geo_project_query_settings contains unsupported intent categories';
    END IF;
END $$;

ALTER TABLE geo_project_query_settings
    ADD COLUMN intents jsonb;

UPDATE geo_project_query_settings
SET intents = jsonb_build_array(
    jsonb_build_object(
        'category',
        CASE lower(btrim(intent_category))
            WHEN '導航' THEN 'navigational'
            WHEN '導航型' THEN 'navigational'
            WHEN 'navigational' THEN 'navigational'
            WHEN '資訊' THEN 'informational'
            WHEN '資訊型' THEN 'informational'
            WHEN 'informational' THEN 'informational'
            WHEN '商業' THEN 'commercial_investigation'
            WHEN '商業評估' THEN 'commercial_investigation'
            WHEN 'commercial' THEN 'commercial_investigation'
            WHEN 'commercial_investigation' THEN 'commercial_investigation'
            WHEN '交易' THEN 'transactional'
            WHEN '交易型' THEN 'transactional'
            WHEN 'transactional' THEN 'transactional'
        END,
        'description', btrim(intent_description)
    )
);

ALTER TABLE geo_project_query_settings
    ALTER COLUMN intents SET NOT NULL,
    DROP CONSTRAINT ck_geo_project_query_settings_intent_category,
    DROP CONSTRAINT ck_geo_project_query_settings_intent_description,
    DROP COLUMN intent_category,
    DROP COLUMN intent_description,
    ADD CONSTRAINT ck_geo_project_query_settings_intents
        CHECK (jsonb_typeof(intents) = 'array'
            AND jsonb_array_length(intents) BETWEEN 1 AND 4
            AND max_queries >= jsonb_array_length(intents));

COMMIT;
