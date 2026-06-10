CREATE TABLE IF NOT EXISTS user_account (
    id uuid PRIMARY KEY,
    email varchar(320) NOT NULL UNIQUE,
    display_name varchar(200) NOT NULL,
    status varchar(32) NOT NULL,
    password_hash text NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS role (
    id uuid PRIMARY KEY,
    name varchar(100) NOT NULL UNIQUE,
    permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
    is_system boolean NOT NULL DEFAULT false,
    has_global_resource_access boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS user_role (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    role_id uuid NOT NULL REFERENCES role(id) ON DELETE RESTRICT,
    CONSTRAINT ux_user_role UNIQUE (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS customer_access_grant (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    customer_id uuid NOT NULL,
    CONSTRAINT ux_user_customer_grant UNIQUE (user_id, customer_id)
);

CREATE TABLE IF NOT EXISTS task_access_grant (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    task_id uuid NOT NULL,
    CONSTRAINT ux_user_task_grant UNIQUE (user_id, task_id)
);

CREATE TABLE IF NOT EXISTS refresh_session (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    token_digest varchar(64) NOT NULL UNIQUE,
    family_id uuid NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz NULL,
    replaced_by_id uuid NULL
);

CREATE INDEX IF NOT EXISTS ix_refresh_session_family_id
    ON refresh_session (family_id);

CREATE TABLE IF NOT EXISTS invitation (
    id uuid PRIMARY KEY,
    email varchar(320) NOT NULL,
    token_digest varchar(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    accepted_at timestamptz NULL,
    revoked_at timestamptz NULL,
    created_at timestamptz NOT NULL,
    created_by uuid NOT NULL REFERENCES user_account(id)
);

CREATE TABLE IF NOT EXISTS security_audit_event (
    id uuid PRIMARY KEY,
    event_type varchar(100) NOT NULL,
    actor_user_id uuid NULL,
    subject_user_id uuid NULL,
    occurred_at timestamptz NOT NULL,
    outcome varchar(32) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_security_audit_event_occurred_at
    ON security_audit_event (occurred_at DESC);
