from uuid import UUID

from younilab_seo.access_control.contracts import AuthorizationRequest


def test_authorization_request_uses_camel_case_contract() -> None:
    request = AuthorizationRequest.model_validate(
        {
            "userId": "11111111-1111-4111-8111-111111111111",
            "permission": "tasks.read",
        }
    )

    assert request.user_id == UUID("11111111-1111-4111-8111-111111111111")
    assert request.model_dump(by_alias=True, mode="json")["userId"] == str(
        request.user_id
    )
