import pytest
from fastapi.security import HTTPAuthorizationCredentials

from younilab_access_control_api.presentation.request_parsing import (
    access_token_from_credentials,
    refresh_token_from_cookie,
)
from younilab_seo.access_control.application import InvalidSession


def test_access_token_from_credentials_returns_bearer_token() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="access-token",
    )

    assert access_token_from_credentials(credentials) == "access-token"


@pytest.mark.parametrize(
    "credentials",
    [
        None,
        HTTPAuthorizationCredentials(scheme="Basic", credentials="access-token"),
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=" "),
    ],
)
def test_access_token_from_credentials_rejects_invalid_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    with pytest.raises(InvalidSession):
        access_token_from_credentials(credentials)


def test_refresh_token_from_cookie_returns_normalized_token() -> None:
    assert refresh_token_from_cookie(" refresh-token ") == "refresh-token"


@pytest.mark.parametrize("token", [None, "", " "])
def test_refresh_token_from_cookie_rejects_missing_token(token: str | None) -> None:
    with pytest.raises(InvalidSession):
        refresh_token_from_cookie(token)
