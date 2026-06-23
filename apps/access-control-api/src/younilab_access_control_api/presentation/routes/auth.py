from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from younilab_access_control_api.presentation.dependencies import (
    CurrentPrincipal,
    bearer_scheme,
    current_principal,
)
from younilab_access_control_api.presentation.dtos import (
    AcceptInvitationRequest,
    LoginRequest,
    PasswordResetRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from younilab_access_control_api.presentation.request_parsing import (
    access_token_from_credentials,
    refresh_token_from_cookie,
)


router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/password-reset-requests", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
) -> None:
    await request.app.state.account_recovery.request_reset(str(payload.email))


@router.post("/password-resets", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
) -> None:
    await request.app.state.account_recovery.reset_password(
        token=payload.token,
        new_password=payload.new_password,
    )


@router.post("/user-invitations/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_invitation(
    payload: AcceptInvitationRequest,
    request: Request,
) -> None:
    await request.app.state.invitations.accept(
        token=payload.token,
        new_password=payload.new_password,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    tokens = await request.app.state.authentication.login(
        email=str(payload.email),
        password=payload.password,
    )
    _set_refresh_cookie(
        response,
        tokens.refresh_token,
        tokens.refresh_token_expires_at,
        secure=request.app.state.secure_cookies,
    )
    return TokenResponse.from_tokens(tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refreshToken"),
) -> TokenResponse:
    tokens = await request.app.state.authentication.refresh(
        refresh_token_from_cookie(refresh_token)
    )
    _set_refresh_cookie(
        response,
        tokens.refresh_token,
        tokens.refresh_token_expires_at,
        secure=request.app.state.secure_cookies,
    )
    return TokenResponse.from_tokens(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    _: CurrentPrincipal = Depends(current_principal),
) -> None:
    await request.app.state.authentication.logout(
        access_token_from_credentials(credentials)
    )
    response.delete_cookie("refreshToken", path="/api/auth")


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    _: CurrentPrincipal = Depends(current_principal),
) -> None:
    await request.app.state.authentication.logout_all(
        access_token_from_credentials(credentials)
    )
    response.delete_cookie("refreshToken", path="/api/auth")


def _set_refresh_cookie(
    response: Response,
    token: str,
    expires_at,
    *,
    secure: bool,
) -> None:
    response.set_cookie(
        key="refreshToken",
        value=token,
        expires=expires_at,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/auth",
    )
