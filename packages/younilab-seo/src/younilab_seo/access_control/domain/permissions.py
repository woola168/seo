PERMISSIONS = frozenset(
    {
        "users.read",
        "users.manage",
        "roles.read",
        "roles.manage",
        "permissions.read",
        "access-grants.read",
        "access-grants.manage",
        "departments.read",
        "departments.manage",
        "customers.read",
        "customers.create",
        "customers.update",
        "customers.delete",
        "tasks.read",
        "tasks.create",
        "tasks.update",
        "tasks.delete",
        "geo.admin.access",
        "geo.projects.read",
        "geo.projects.create",
        "geo.projects.update",
        "geo.projects.delete",
        "geo.queries.manage",
        "geo.jobs.read",
        "geo.jobs.run",
        "geo.jobs.cancel",
        "authorization.evaluate",
        "audit-events.read",
    }
)

INTERNAL_PERMISSIONS = frozenset({"geo.admin.access"})
ASSIGNABLE_PERMISSIONS = PERMISSIONS - INTERNAL_PERMISSIONS
