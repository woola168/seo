from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from younilab_access_control_application import (
    AccessControlRepository,
    AccessControlError,
    AccountUnavailable,
    Clock,
    IdGenerator,
    InvalidCredentials,
    InvalidSession,
    PasswordHasher,
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
from younilab_access_control_infrastructure import AccessControlSettings


def create_app(
    *,
    settings: AccessControlSettings | None = None,
    repository: AccessControlRepository | None = None,
    password_hasher: PasswordHasher | None = None,
    token_provider: TokenProvider | None = None,
    clock: Clock | None = None,
    id_generator: IdGenerator | None = None,
) -> FastAPI:
    dependencies = build_dependencies(
        settings=settings,
        repository=repository,
        password_hasher=password_hasher,
        token_provider=token_provider,
        clock=clock,
        id_generator=id_generator,
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
