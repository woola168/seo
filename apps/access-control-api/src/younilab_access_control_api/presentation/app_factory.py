from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from younilab_access_control_application import (
    AccessControlError,
    AccessManagementService,
    AccountUnavailable,
    AuthenticationService,
    AuthorizationService,
    InvalidCredentials,
    InvalidSession,
    ResourceNotFound,
)
from younilab_access_control_api.presentation.routes import (
    auth_router,
    authorization_router,
    health_router,
    management_router,
    me_router,
)
from younilab_access_control_infrastructure import (
    AccessControlSettings,
    Argon2PasswordHasher,
    MemoryAccessControlRepository,
    SystemClock,
    UuidGenerator,
    build_postgres_repository,
)


def create_app(
    *,
    repository=None,
    password_hasher=None,
    token_provider=None,
) -> FastAPI:
    settings = AccessControlSettings()
    if token_provider is None:
        token_provider = _token_provider(settings)
    password_hasher = password_hasher or Argon2PasswordHasher()
    if repository is None:
        repository = _repository(settings)
    clock = SystemClock()
    id_generator = UuidGenerator()

    app = FastAPI(title="Younilab SEO Access Control API", version="0.1.0")
    app.state.repository = repository
    app.state.token_provider = token_provider
    app.state.id_generator = id_generator
    app.state.secure_cookies = settings.is_production
    app.state.authentication = AuthenticationService(
        repository=repository,
        password_hasher=password_hasher,
        token_provider=token_provider,
        clock=clock,
        id_generator=id_generator,
    )
    app.state.authorization = AuthorizationService(repository)
    app.state.management = AccessManagementService(repository)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(authorization_router)
    app.include_router(management_router)
    _register_error_handlers(app)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentials)
    async def invalid_credentials(
        request: Request,
        exc: InvalidCredentials,
    ) -> JSONResponse:
        return _problem(
            request,
            status=401,
            title="Authentication failed",
            detail="Email or password is invalid.",
        )

    @app.exception_handler(InvalidSession)
    async def invalid_session(
        request: Request,
        exc: InvalidSession,
    ) -> JSONResponse:
        return _problem(
            request,
            status=401,
            title="Authentication required",
            detail="The session is missing, invalid, or expired.",
        )

    @app.exception_handler(AccountUnavailable)
    async def account_unavailable(
        request: Request,
        exc: AccountUnavailable,
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested operation is not allowed.",
        )

    @app.exception_handler(ResourceNotFound)
    async def resource_not_found(
        request: Request,
        exc: ResourceNotFound,
    ) -> JSONResponse:
        return _problem(
            request,
            status=404,
            title="Resource not found",
            detail="The requested resource was not found.",
        )

    @app.exception_handler(AccessControlError)
    async def access_control_error(
        request: Request,
        exc: AccessControlError,
    ) -> JSONResponse:
        return _problem(
            request,
            status=400,
            title="Invalid request",
            detail="The request could not be processed.",
        )


def _problem(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
        },
    )


def _repository(settings: AccessControlSettings):
    if settings.database_url:
        return build_postgres_repository(settings.database_url)
    if settings.is_production:
        raise RuntimeError("ACCESS_CONTROL_DATABASE_URL is required in production")
    return MemoryAccessControlRepository()


def _token_provider(settings: AccessControlSettings):
    from younilab_access_control_infrastructure import JwtTokenProvider

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


def _development_token_provider(settings: AccessControlSettings):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from younilab_access_control_infrastructure import JwtTokenProvider

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
