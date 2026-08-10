CREATE TABLE IF NOT EXISTS tenant (
    id uuid PRIMARY KEY,
    code varchar(80) NOT NULL UNIQUE,
    name varchar(200) NOT NULL,
    status varchar(32) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    disabled_at timestamptz NULL
);

CREATE TABLE IF NOT EXISTS department (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    name varchar(100) NOT NULL,
    description text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz NULL,
    CONSTRAINT ux_department_tenant_name UNIQUE (tenant_id, name)
);

CREATE TABLE IF NOT EXISTS user_account (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    email varchar(320) NOT NULL UNIQUE,
    display_name varchar(200) NOT NULL,
    status varchar(32) NOT NULL,
    password_hash text NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    department_id uuid NULL REFERENCES department(id),
    auth_provider varchar(32) NOT NULL DEFAULT 'password',
    last_login_at timestamptz NULL,
    invited_at timestamptz NULL,
    deleted_at timestamptz NULL
);

CREATE TABLE IF NOT EXISTS role (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    name varchar(100) NOT NULL,
    permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
    is_system boolean NOT NULL DEFAULT false,
    has_global_resource_access boolean NOT NULL DEFAULT false,
    CONSTRAINT ux_role_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS ix_department_tenant_id
    ON department (tenant_id);

CREATE INDEX IF NOT EXISTS ix_user_account_tenant_id
    ON user_account (tenant_id);

CREATE INDEX IF NOT EXISTS ix_role_tenant_id
    ON role (tenant_id);

CREATE TABLE IF NOT EXISTS user_role (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    role_id uuid NOT NULL REFERENCES role(id) ON DELETE RESTRICT,
    CONSTRAINT ux_user_role UNIQUE (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS customer_access_grant (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    customer_id uuid NOT NULL,
    CONSTRAINT ux_tenant_user_customer_grant UNIQUE (tenant_id, user_id, customer_id)
);

CREATE TABLE IF NOT EXISTS task_access_grant (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    task_id uuid NOT NULL,
    CONSTRAINT ux_tenant_user_task_grant UNIQUE (tenant_id, user_id, task_id)
);

CREATE INDEX IF NOT EXISTS ix_customer_access_grant_tenant_id
    ON customer_access_grant (tenant_id);

CREATE INDEX IF NOT EXISTS ix_task_access_grant_tenant_id
    ON task_access_grant (tenant_id);

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
    user_id uuid NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    email varchar(320) NOT NULL,
    token_digest varchar(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    accepted_at timestamptz NULL,
    revoked_at timestamptz NULL,
    created_at timestamptz NOT NULL,
    created_by uuid NOT NULL REFERENCES user_account(id)
);

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
