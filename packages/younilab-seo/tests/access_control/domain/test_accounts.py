from uuid import UUID

from younilab_seo.access_control.domain import AccountStatus, UserAccount


def test_user_account_normalizes_email() -> None:
    user = UserAccount(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        email=" User@Example.com ",
        display_name="SEO User",
        status=AccountStatus.ACTIVE,
    )

    assert user.email == "user@example.com"
