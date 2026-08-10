BEGIN;

CREATE TABLE IF NOT EXISTS department (
    id uuid PRIMARY KEY,
    name varchar(100) NOT NULL UNIQUE,
    description text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz NULL
);

ALTER TABLE user_account
    ADD COLUMN IF NOT EXISTS department_id uuid NULL REFERENCES department(id),
    ADD COLUMN IF NOT EXISTS auth_provider varchar(32) NOT NULL DEFAULT 'password',
    ADD COLUMN IF NOT EXISTS last_login_at timestamptz NULL,
    ADD COLUMN IF NOT EXISTS invited_at timestamptz NULL,
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz NULL;

ALTER TABLE invitation
    ADD COLUMN IF NOT EXISTS user_id uuid NULL REFERENCES user_account(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS password_reset (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    token_digest varchar(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL,
    used_at timestamptz NULL,
    revoked_at timestamptz NULL
);

CREATE TABLE IF NOT EXISTS notification_outbox (
    id uuid PRIMARY KEY,
    recipient varchar(320) NOT NULL,
    template varchar(100) NOT NULL,
    payload_ciphertext text NOT NULL,
    status varchar(32) NOT NULL,
    attempts integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL,
    sent_at timestamptz NULL,
    last_error text NULL
);

CREATE INDEX IF NOT EXISTS ix_notification_outbox_pending
    ON notification_outbox (status, created_at);

COMMIT;
