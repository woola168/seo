from younilab_access_control_application import (
    AccessControlRepository,
    AccessGrantRepository,
    AccessManagementRepository,
    AuthenticationRepository,
    AuthorizationRepository,
    RefreshSessionRepository,
    RoleRepository,
    UserRepository,
)


def test_repository_protocols_are_public() -> None:
    assert AccessControlRepository is not None
    assert AccessGrantRepository is not None
    assert AccessManagementRepository is not None
    assert AuthenticationRepository is not None
    assert AuthorizationRepository is not None
    assert RefreshSessionRepository is not None
    assert RoleRepository is not None
    assert UserRepository is not None
