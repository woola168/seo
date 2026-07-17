import argparse
import asyncio
from datetime import UTC, datetime
from getpass import getpass
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import select

from younilab_seo.access_control.domain import (
    DEFAULT_TENANT_CODE,
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
    PERMISSIONS,
)
from younilab_seo.access_control.infrastructure import (
    AccessControlSettings,
    Argon2PasswordHasher,
    build_postgres_session_factory,
)
from younilab_seo.access_control.infrastructure.persistence import (
    RoleRow,
    TenantRow,
    UserRoleRow,
    UserRow,
)


ADMIN_ROLE_ID = uuid5(NAMESPACE_URL, "younilab-seo:role:admin")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the initial SEO access control administrator."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()
    password = getpass("Initial administrator password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    asyncio.run(
        bootstrap_admin(
            email=args.email,
            display_name=args.display_name,
            password=password,
        )
    )


async def bootstrap_admin(
    *,
    email: str,
    display_name: str,
    password: str,
) -> None:
    settings = AccessControlSettings()
    if not settings.database_url:
        raise SystemExit("ACCESS_CONTROL_DATABASE_URL is required.")
    session_factory = build_postgres_session_factory(settings.database_url)
    password_hash = Argon2PasswordHasher().hash(password)
    normalized_email = email.strip().lower()
    now = datetime.now(UTC)

    async with session_factory() as session:
        tenant = await session.get(TenantRow, DEFAULT_TENANT_ID)
        if tenant is None:
            tenant = TenantRow(
                id=DEFAULT_TENANT_ID,
                code=DEFAULT_TENANT_CODE,
                name=DEFAULT_TENANT_NAME,
                status="active",
                created_at=now,
                updated_at=now,
            )
            session.add(tenant)

        role = await session.get(RoleRow, ADMIN_ROLE_ID)
        if role is None:
            role = RoleRow(
                id=ADMIN_ROLE_ID,
                tenant_id=DEFAULT_TENANT_ID,
                name="admin",
                permissions=sorted(PERMISSIONS),
                is_system=True,
                has_global_resource_access=True,
            )
            session.add(role)
        else:
            role.permissions = sorted(set(role.permissions) | PERMISSIONS)
            role.is_system = True
            role.has_global_resource_access = True

        user = await session.scalar(
            select(UserRow).where(UserRow.email == normalized_email)
        )
        if user is None:
            user = UserRow(
                id=uuid4(),
                tenant_id=DEFAULT_TENANT_ID,
                email=normalized_email,
                display_name=display_name.strip(),
                status="active",
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            await session.flush()

        assignment = await session.scalar(
            select(UserRoleRow).where(
                UserRoleRow.user_id == user.id,
                UserRoleRow.role_id == ADMIN_ROLE_ID,
            )
        )
        if assignment is None:
            session.add(UserRoleRow(user_id=user.id, role_id=ADMIN_ROLE_ID))
        await session.commit()
        print(f"Administrator ready: {normalized_email}")


if __name__ == "__main__":
    main()
