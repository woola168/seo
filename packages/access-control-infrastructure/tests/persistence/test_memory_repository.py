import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from younilab_access_control_application import RefreshSession
from younilab_access_control_infrastructure import MemoryAccessControlRepository


def test_replacing_refresh_session_revokes_previous_token() -> None:
    async def scenario() -> None:
        repository = MemoryAccessControlRepository()
        current = RefreshSession(
            id=UUID("11111111-1111-4111-8111-111111111111"),
            user_id=UUID("22222222-2222-4222-8222-222222222222"),
            token_digest="old",
            family_id=UUID("33333333-3333-4333-8333-333333333333"),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        replacement = RefreshSession(
            id=UUID("44444444-4444-4444-8444-444444444444"),
            user_id=current.user_id,
            token_digest="new",
            family_id=current.family_id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        await repository.save_refresh_session(current)
        await repository.replace_refresh_session(
            current_session_id=current.id,
            replacement=replacement,
            revoked_at=datetime.now(UTC),
        )

        assert repository.sessions[current.id].revoked_at is not None
        assert repository.sessions[current.id].replaced_by_id == replacement.id
        assert repository.sessions[replacement.id].revoked_at is None

    asyncio.run(scenario())
