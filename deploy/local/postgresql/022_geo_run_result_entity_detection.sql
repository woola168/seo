BEGIN;

CREATE TABLE IF NOT EXISTS geo_run_result_entity_detection (
    id uuid PRIMARY KEY,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    detector_version varchar(100) NOT NULL,
    status varchar(32) NOT NULL,
    error_code varchar(100),
    error_message text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz,
    CONSTRAINT ux_geo_run_result_entity_detection_version
        UNIQUE (run_result_id, detector_version)
);

CREATE TABLE IF NOT EXISTS geo_run_result_entity_detection_item (
    id uuid PRIMARY KEY,
    detection_id uuid NOT NULL REFERENCES geo_run_result_entity_detection(id) ON DELETE CASCADE,
    run_result_id uuid NOT NULL REFERENCES geo_run_result(id) ON DELETE CASCADE,
    entity_id uuid NOT NULL,
    entity_role varchar(32) NOT NULL,
    entity_name varchar(200) NOT NULL,
    mentioned boolean NOT NULL,
    first_mention_order integer,
    evidence_text text,
    matched_by varchar(32),
    matched_value text,
    match_type varchar(32),
    created_at timestamptz NOT NULL,
    CONSTRAINT ux_geo_run_result_entity_detection_item_entity
        UNIQUE (detection_id, entity_id)
);

CREATE INDEX IF NOT EXISTS ix_geo_run_result_entity_detection_completed
ON geo_run_result_entity_detection (run_result_id, updated_at DESC)
WHERE status = 'completed';

CREATE INDEX IF NOT EXISTS ix_geo_run_result_entity_detection_item_result
ON geo_run_result_entity_detection_item (run_result_id, entity_role, mentioned);

COMMIT;
