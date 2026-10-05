from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken
from app.security import (
    decode_access_token,
    hash_refresh_token,
)


async def login(client, credentials):
    """
    OAuth2PasswordRequestForm expects form data, not JSON.
    """

    return await client.post(
        "/auth/token",
        data={
            "username": credentials["username"],
            "password": credentials["password"],
        },
    )


@pytest.mark.asyncio
async def test_login_returns_access_and_refresh_tokens(
    client,
    auth_user,
    auth_credentials,
):
    response = await login(
        client,
        auth_credentials,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"

    assert body["access_token"] != body["refresh_token"]


@pytest.mark.asyncio
async def test_login_access_token_contains_username_and_role(
    client,
    auth_user,
    auth_credentials,
):
    response = await login(
        client,
        auth_credentials,
    )

    assert response.status_code == 200

    payload = decode_access_token(
        response.json()["access_token"]
    )

    assert payload["sub"] == auth_user.username
    assert payload["role"] == auth_user.role.value
    assert "exp" in payload


@pytest.mark.asyncio
async def test_login_rejects_incorrect_password(
    client,
    auth_user,
    auth_credentials,
):
    response = await client.post(
        "/auth/token",
        data={
            "username": auth_credentials["username"],
            "password": "DefinitelyWrongPassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Incorrect username or password"
    )


@pytest.mark.asyncio
async def test_login_rejects_unknown_username(
    client,
    auth_credentials,
):
    response = await client.post(
        "/auth/token",
        data={
            "username": "does_not_exist",
            "password": auth_credentials["password"],
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_stores_only_hash_of_refresh_token(
    client,
    auth_user,
    auth_credentials,
    db_session: AsyncSession,
):
    response = await login(
        client,
        auth_credentials,
    )

    assert response.status_code == 200

    raw_refresh_token = (
        response.json()["refresh_token"]
    )

    expected_hash = hash_refresh_token(
        raw_refresh_token
    )

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == expected_hash
        )
    )

    stored_token = result.scalar_one()

    assert stored_token.user_id == auth_user.id
    assert stored_token.revoked is False

    # The opaque token sent to the browser must never be stored directly.
    assert stored_token.token_hash != raw_refresh_token


@pytest.mark.asyncio
async def test_refresh_rotates_refresh_token(
    client,
    auth_user,
    auth_credentials,
    db_session: AsyncSession,
):
    login_response = await login(
        client,
        auth_credentials,
    )

    original = login_response.json()
    original_refresh = original["refresh_token"]

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": original_refresh,
        },
    )

    assert refresh_response.status_code == 200

    replacement = refresh_response.json()

    assert replacement["access_token"]
    assert replacement["refresh_token"]
    assert replacement["token_type"] == "bearer"

    assert (
        replacement["refresh_token"]
        != original_refresh
    )

    old_result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(
                original_refresh
            )
        )
    )

    old_row = old_result.scalar_one()

    new_result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(
                replacement["refresh_token"]
            )
        )
    )

    new_row = new_result.scalar_one()

    assert old_row.revoked is True
    assert new_row.revoked is False

    # Rotation should stay in the same token family/chain.
    assert new_row.chain_id == old_row.chain_id

    payload = decode_access_token(
        replacement["access_token"]
    )

    assert payload["sub"] == auth_user.username
    assert payload["role"] == auth_user.role.value


@pytest.mark.asyncio
async def test_reusing_old_refresh_token_invalidates_chain(
    client,
    auth_user,
    auth_credentials,
):
    login_response = await login(
        client,
        auth_credentials,
    )

    original_refresh = (
        login_response.json()["refresh_token"]
    )

    first_refresh = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": original_refresh,
        },
    )

    assert first_refresh.status_code == 200

    replacement_refresh = (
        first_refresh.json()["refresh_token"]
    )

    # Reusing the already-consumed token is the suspicious event.
    reuse_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": original_refresh,
        },
    )

    assert reuse_response.status_code == 401

    # The replacement belongs to the same chain and should now also be dead.
    replacement_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": replacement_refresh,
        },
    )

    assert replacement_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(
    client,
    auth_user,
    auth_credentials,
    db_session: AsyncSession,
):
    login_response = await login(
        client,
        auth_credentials,
    )

    refresh_token = (
        login_response.json()["refresh_token"]
    )

    logout_response = await client.post(
        "/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 204

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(
                refresh_token
            )
        )
    )

    stored_token = result.scalar_one()

    assert stored_token.revoked is True

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_unknown_token(
    client,
):
    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token":
                "this-is-not-a-real-refresh-token",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_refresh_token_is_rejected(
    client,
    auth_user,
    auth_credentials,
    db_session: AsyncSession,
):
    login_response = await login(
        client,
        auth_credentials,
    )

    refresh_token = (
        login_response.json()["refresh_token"]
    )

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(
                refresh_token
            )
        )
    )

    stored_token = result.scalar_one()

    stored_token.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(minutes=1)
    )

    await db_session.commit()

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401

    await db_session.refresh(stored_token)

    assert stored_token.revoked is True


@pytest.mark.asyncio
async def test_refresh_endpoint_does_not_require_access_token(
    client,
    auth_user,
    auth_credentials,
):
    login_response = await login(
        client,
        auth_credentials,
    )

    refresh_token = (
        login_response.json()["refresh_token"]
    )

    # Deliberately do NOT send an Authorization header.
    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_is_one_time_use(
    client,
    auth_user,
    auth_credentials,
):
    login_response = await login(
        client,
        auth_credentials,
    )

    refresh_token = (
        login_response.json()["refresh_token"]
    )

    first = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert first.status_code == 200

    second = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert second.status_code == 401
