from dataclasses import dataclass

from younilab_seo.access_control.application import (
    AccountRecoveryService,
    AccessControlRepository,
    AccessManagementService,
    AuthenticationService,
    AuthorizationService,
    Clock,
    IdGenerator,
    InvitationService,
    NotificationPublisher,
    PasswordHasher,
    RecoveryTokenProvider,
    ResourceGrantVerifier,
    TokenProvider,
)
from younilab_seo.access_control.infrastructure import (
    AccessControlSettings,
    Argon2PasswordHasher,
    JwtTokenProvider,
    MemoryAccessControlRepository,
    MemoryNotificationPublisher,
    PostgresOutboxPublisher,
    ResourceCatalogHttpGrantVerifier,
    SecureRecoveryTokenProvider,
    SystemClock,
    UuidGenerator,
    build_postgres_repository,
    build_postgres_session_factory,
)


@dataclass(frozen=True)
class AccessControlApiDependencies:
    repository: AccessControlRepository
    token_provider: TokenProvider
    clock: Clock
    id_generator: IdGenerator
    authentication: AuthenticationService
    authorization: AuthorizationService
    management: AccessManagementService
    account_recovery: AccountRecoveryService
    invitations: InvitationService
    notifications: NotificationPublisher
    secure_cookies: bool


def build_dependencies(
    *,
    settings: AccessControlSettings | None = None,
    repository: AccessControlRepository | None = None,
    password_hasher: PasswordHasher | None = None,
    token_provider: TokenProvider | None = None,
    clock: Clock | None = None,
    id_generator: IdGenerator | None = None,
    recovery_token_provider: RecoveryTokenProvider | None = None,
    notifications: NotificationPublisher | None = None,
    resource_grant_verifier: ResourceGrantVerifier | None = None,
) -> AccessControlApiDependencies:
    resolved_settings = settings if settings is not None else AccessControlSettings()
    resolved_repository = (
        repository if repository is not None else _repository(resolved_settings)
    )
    resolved_password_hasher = (
        password_hasher if password_hasher is not None else Argon2PasswordHasher()
    )
    resolved_token_provider = (
        token_provider
        if token_provider is not None
        else _token_provider(resolved_settings)
    )
    resolved_clock = clock if clock is not None else SystemClock()
    resolved_id_generator = (
        id_generator if id_generator is not None else UuidGenerator()
    )
    resolved_recovery_token_provider = (
        recovery_token_provider
        if recovery_token_provider is not None
        else SecureRecoveryTokenProvider()
    )
    resolved_notifications = (
        notifications
        if notifications is not None
        else _notifications(resolved_settings)
    )
    resolved_resource_grant_verifier = (
        resource_grant_verifier
        if resource_grant_verifier is not None
        else ResourceCatalogHttpGrantVerifier(resolved_settings.resource_catalog_url)
    )

    return AccessControlApiDependencies(
        repository=resolved_repository,
        token_provider=resolved_token_provider,
        clock=resolved_clock,
        id_generator=resolved_id_generator,
        authentication=AuthenticationService(
            repository=resolved_repository,
            password_hasher=resolved_password_hasher,
            token_provider=resolved_token_provider,
            clock=resolved_clock,
            id_generator=resolved_id_generator,
        ),
        authorization=AuthorizationService(resolved_repository),
        management=AccessManagementService(
            resolved_repository,
            clock=resolved_clock,
            resource_grant_verifier=resolved_resource_grant_verifier,
        ),
        account_recovery=AccountRecoveryService(
            repository=resolved_repository,
            password_hasher=resolved_password_hasher,
            token_provider=resolved_recovery_token_provider,
            notifications=resolved_notifications,
            clock=resolved_clock,
            id_generator=resolved_id_generator,
            portal_url=resolved_settings.portal_url,
        ),
        invitations=InvitationService(
            repository=resolved_repository,
            password_hasher=resolved_password_hasher,
            token_provider=resolved_recovery_token_provider,
            notifications=resolved_notifications,
            clock=resolved_clock,
            id_generator=resolved_id_generator,
            portal_url=resolved_settings.portal_url,
            resource_grant_verifier=resolved_resource_grant_verifier,
        ),
        notifications=resolved_notifications,
        secure_cookies=resolved_settings.is_production,
    )


def _repository(settings: AccessControlSettings) -> AccessControlRepository:
    if settings.database_url:
        return build_postgres_repository(settings.database_url)
    if settings.is_production:
        raise RuntimeError("ACCESS_CONTROL_DATABASE_URL is required in production")
    return MemoryAccessControlRepository()


def _notifications(settings: AccessControlSettings) -> NotificationPublisher:
    if settings.database_url:
        return PostgresOutboxPublisher(
            build_postgres_session_factory(settings.database_url)
        )
    if settings.is_production:
        raise RuntimeError("ACCESS_CONTROL_DATABASE_URL is required in production")
    return MemoryNotificationPublisher()


def _token_provider(settings: AccessControlSettings) -> TokenProvider:
    if settings.jwt_private_key and settings.jwt_public_key:
        return JwtTokenProvider(
            signing_key=settings.jwt_private_key.replace("\\n", "\n"),
            verification_key=settings.jwt_public_key.replace("\\n", "\n"),
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            access_token_minutes=settings.access_token_minutes,
            refresh_token_days=settings.refresh_token_days,
        )
    if settings.is_production:
        raise RuntimeError(
            "ACCESS_CONTROL_JWT_PRIVATE_KEY and ACCESS_CONTROL_JWT_PUBLIC_KEY "
            "are required in production"
        )
    return _development_token_provider(settings)


def _development_token_provider(
    settings: AccessControlSettings,
) -> JwtTokenProvider:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return JwtTokenProvider(
        signing_key=private_pem,
        verification_key=public_pem,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        access_token_minutes=settings.access_token_minutes,
        refresh_token_days=settings.refresh_token_days,
    )
