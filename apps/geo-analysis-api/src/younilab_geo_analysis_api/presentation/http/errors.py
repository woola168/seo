from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from younilab_seo.geo_analysis.domain import QueryRunJobStatusError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _problem(
            request,
            422,
            "Request validation failed",
            invalid_params=_invalid_params(exc),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = str(exc.detail)
        return _problem(request, exc.status_code, detail)

    @app.exception_handler(QueryRunJobStatusError)
    async def job_status_error(
        request: Request,
        exc: QueryRunJobStatusError,
    ) -> JSONResponse:
        return _problem(request, 409, str(exc) or "Invalid job status transition")


def _problem(
    request: Request,
    status_code: int,
    detail: str,
    *,
    invalid_params: list[dict[str, str]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": detail,
            "status": status_code,
            "detail": detail,
            "instance": request.url.path,
            **({"invalidParams": invalid_params} if invalid_params else {}),
        },
    )


def _invalid_params(exc: RequestValidationError) -> list[dict[str, str]]:
    return [
        {
            "name": ".".join(str(part) for part in error["loc"]),
            "reason": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
