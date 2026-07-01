-- Local test accounts:
-- admin@example.com / DemoPassword123!
-- specialist@example.com / DemoPassword123!
-- Do not apply this seed to production environments.

BEGIN;

INSERT INTO tenant (
    id,
    code,
    name,
    status,
    created_at,
    updated_at
)
VALUES (
    '00000000-0000-4000-8000-000000000001',
    'default',
    'Default Tenant',
    'active',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO role (
    id,
    tenant_id,
    name,
    permissions,
    is_system,
    has_global_resource_access
)
VALUES
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    '00000000-0000-4000-8000-000000000001',
    'admin',
    '[
        "access-grants.manage",
        "access-grants.read",
        "audit-events.read",
        "authorization.evaluate",
        "customers.create",
        "customers.delete",
        "customers.read",
        "customers.update",
        "departments.manage",
        "departments.read",
        "permissions.read",
        "roles.manage",
        "roles.read",
        "tasks.create",
        "tasks.delete",
        "tasks.read",
        "tasks.update",
        "users.manage",
        "users.read"
    ]'::jsonb,
    true,
    true
),
(
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    '00000000-0000-4000-8000-000000000001',
    'seo-specialist',
    '[
        "customers.read",
        "tasks.read",
        "tasks.update"
    ]'::jsonb,
    true,
    false
)
ON CONFLICT (id) DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    name = EXCLUDED.name,
    permissions = EXCLUDED.permissions,
    is_system = EXCLUDED.is_system,
    has_global_resource_access = EXCLUDED.has_global_resource_access;

INSERT INTO user_account (
    id,
    tenant_id,
    email,
    display_name,
    status,
    password_hash,
    created_at,
    updated_at
)
VALUES
(
    '11111111-1111-4111-8111-111111111111',
    '00000000-0000-4000-8000-000000000001',
    'admin@example.com',
    'SEO Admin',
    'active',
    '$argon2id$v=19$m=65536,t=3,p=4$WOYRLzu8IKst3hH4OK9mEw$Mf7toPYK6IED9vy8AbBB6tG2HVDs/gJc3feB+BIR35g',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '22222222-2222-4222-8222-222222222222',
    '00000000-0000-4000-8000-000000000001',
    'specialist@example.com',
    'SEO Specialist',
    'active',
    '$argon2id$v=19$m=65536,t=3,p=4$WOYRLzu8IKst3hH4OK9mEw$Mf7toPYK6IED9vy8AbBB6tG2HVDs/gJc3feB+BIR35g',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    email = EXCLUDED.email,
    display_name = EXCLUDED.display_name,
    status = EXCLUDED.status,
    password_hash = EXCLUDED.password_hash,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO user_role (id, user_id, role_id)
VALUES
(
    'cccccccc-cccc-4ccc-8ccc-ccccccccccc1',
    '11111111-1111-4111-8111-111111111111',
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
),
(
    'cccccccc-cccc-4ccc-8ccc-ccccccccccc2',
    '22222222-2222-4222-8222-222222222222',
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
)
ON CONFLICT (user_id, role_id) DO NOTHING;

INSERT INTO customer_access_grant (id, tenant_id, user_id, customer_id)
VALUES
(
    'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
    '00000000-0000-4000-8000-000000000001',
    '22222222-2222-4222-8222-222222222222',
    '33333333-3333-4333-8333-333333333333'
)
ON CONFLICT (tenant_id, user_id, customer_id) DO NOTHING;

INSERT INTO task_access_grant (id, tenant_id, user_id, task_id)
VALUES
(
    'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    '00000000-0000-4000-8000-000000000001',
    '22222222-2222-4222-8222-222222222222',
    '44444444-4444-4444-8444-444444444444'
)
ON CONFLICT (tenant_id, user_id, task_id) DO NOTHING;

COMMIT;
