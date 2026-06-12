from uuid import UUID

import pytest

from younilab_access_control_domain import Role


def test_role_requires_name() -> None:
    with pytest.raises(ValueError, match="role name must not be empty"):
        Role(
            id=UUID("22222222-2222-4222-8222-222222222222"),
            name=" ",
        )
