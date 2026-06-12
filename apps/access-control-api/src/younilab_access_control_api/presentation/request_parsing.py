from fastapi.security import HTTPAuthorizationCredentials

from younilab_access_control_application import InvalidSession


def access_token_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidSession

    token = credentials.credentials.strip()
    if not token:
        raise InvalidSession
    return token


def refresh_token_from_cookie(refresh_token: str | None) -> str:
    if refresh_token is None:
        raise InvalidSession

    token = refresh_token.strip()
    if not token:
        raise InvalidSession
    return token
