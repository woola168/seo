from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from younilab_resource_catalog_application import (
    AccessDenied,
    Conflict,
    ResourceCatalogError,
    ResourceNotFound,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AccessDenied)
    async def access_denied(request: Request, exc: AccessDenied) -> JSONResponse:
        return _problem(request, 403, "Access denied")

    @app.exception_handler(ResourceNotFound)
    async def not_found(request: Request, exc: ResourceNotFound) -> JSONResponse:
        return _problem(request, 404, "Resource not found")

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict) -> JSONResponse:
        return _problem(request, 409, str(exc) or "Resource conflict")

    @app.exception_handler(ResourceCatalogError)
    async def invalid_request(
        request: Request,
        exc: ResourceCatalogError,
    ) -> JSONResponse:
        return _problem(request, 400, "Invalid request")


def _problem(request: Request, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": detail,
            "status": status_code,
            "detail": detail,
            "instance": request.url.path,
        },
    )
