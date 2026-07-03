import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from younilab_seo.access_control.application import (
    AccessControlRepository,
    AccessControlError,
    AccountUnavailable,
    Clock,
    Conflict,
    IdGenerator,
    InvalidRecoveryToken,
    InvalidCredentials,
    InvalidSession,
    NotificationPublisher,
    OperationNotAllowed,
    PasswordHasher,
    RecoveryTokenProvider,
    ResourceGrantVerifier,
    ResourceNotFound,
    TokenProvider,
)
from younilab_access_control_api.presentation.composition import build_dependencies
from younilab_access_control_api.presentation.routes import (
    auth_router,
    authorization_router,
    health_router,
    management_router,
    me_router,
)
from younilab_seo.access_control.infrastructure import AccessControlSettings

logger = logging.getLogger("younilab.access_control.http")


def create_app(
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
) -> FastAPI:
    dependencies = build_dependencies(
        settings=settings,
        repository=repository,
        password_hasher=password_hasher,
        token_provider=token_provider,
        clock=clock,
        id_generator=id_generator,
        recovery_token_provider=recovery_token_provider,
        notifications=notifications,
        resource_grant_verifier=resource_grant_verifier,
    )

    app = FastAPI(title="Younilab SEO Access Control API", version="0.1.0")
    app.state.repository = dependencies.repository
    app.state.token_provider = dependencies.token_provider
    app.state.clock = dependencies.clock
    app.state.id_generator = dependencies.id_generator
    app.state.secure_cookies = dependencies.secure_cookies
    app.state.authentication = dependencies.authentication
    app.state.authorization = dependencies.authorization
    app.state.management = dependencies.management
    app.state.account_recovery = dependencies.account_recovery
    app.state.invitations = dependencies.invitations
    app.state.notifications = dependencies.notifications
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(authorization_router)
    app.include_router(management_router)
    _register_error_handlers(app)
    _register_timing_middleware(app)
    return app


def _register_timing_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.exception(
                "%s %s 500 %.2fms",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


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

    @app.exception_handler(InvalidRecoveryToken)
    async def invalid_recovery_token(
        request: Request,
        exc: InvalidRecoveryToken,
    ) -> JSONResponse:
        return _problem(
            request,
            status=400,
            title="Invalid recovery token",
            detail="The recovery token is invalid or expired.",
            code="RECOVERY_TOKEN_INVALID",
        )

    @app.exception_handler(Conflict)
    async def conflict(
        request: Request,
        exc: Conflict,
    ) -> JSONResponse:
        return _problem(
            request,
            status=409,
            title="Resource conflict",
            detail=str(exc) or "The operation conflicts with current state.",
            code="RESOURCE_CONFLICT",
        )

    @app.exception_handler(OperationNotAllowed)
    async def operation_not_allowed(
        request: Request,
        exc: OperationNotAllowed,
    ) -> JSONResponse:
        return _problem(
            request,
            status=409,
            title="Operation not allowed",
            detail=str(exc),
            code="OPERATION_NOT_ALLOWED",
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
    code: str | None = None,
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
            **({"code": code} if code else {}),
        },
    )
