from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models import RefreshToken, User, UserRole
from app.schemas.user import (
    LogoutRequest,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserRead,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_expiry,
    hash_password,
    hash_refresh_token,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


async def issue_token_pair(
    user: User,
    db: AsyncSession,
    *,
    chain_id=None,
) -> Token:
    """
    Create a short-lived access token plus a new opaque refresh token.

    Only the refresh token's hash is persisted.
    """
    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role.value,
        }
    )

    raw_refresh_token = create_refresh_token()

    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh_token),
        chain_id=chain_id or uuid4(),
        expires_at=get_refresh_token_expiry(),
        revoked=False,
    )

    db.add(refresh_row)

    return Token(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
    )


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    result = await db.execute(
        select(User).where(
            User.username == form_data.username
        )
    )

    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.is_active
        or not verify_password(
            form_data.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = await issue_token_pair(user, db)

    # Persist the new refresh-token row.
    await db.commit()

    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Rotate a refresh token.

    This endpoint intentionally does NOT depend on get_current_user because
    the caller's access token is expected to be expired.

    SELECT ... FOR UPDATE ensures one refresh token cannot be successfully
    consumed twice by two concurrent requests.
    """
    presented_hash = hash_refresh_token(
        payload.refresh_token
    )

    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.token_hash == presented_hash
        )
        .with_for_update()
    )

    stored_token = result.scalar_one_or_none()

    # Malformed/unrecognized token.
    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    now = datetime.now(timezone.utc)

    # If an already-revoked token is presented, assume token theft/reuse.
    # Revoke every token in this rotation chain, including a newer replacement.
    if stored_token.revoked:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.chain_id
                == stored_token.chain_id
            )
            .values(revoked=True)
        )

        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected",
        )

    if stored_token.expires_at <= now:
        stored_token.revoked = True
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    user = await db.get(
        User,
        stored_token.user_id,
    )

    if user is None or not user.is_active:
        stored_token.revoked = True
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token user is invalid",
        )

    # Rotation: the presented token can never be accepted again.
    stored_token.revoked = True

    replacement = await issue_token_pair(
        user,
        db,
        chain_id=stored_token.chain_id,
    )

    await db.commit()

    return replacement


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Revoke this browser/session's current refresh token.

    A valid access token is deliberately not required here. That lets logout
    still invalidate the session even when the access token has just expired.
    """
    presented_hash = hash_refresh_token(
        payload.refresh_token
    )

    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.token_hash == presented_hash
        )
        .with_for_update()
    )

    stored_token = result.scalar_one_or_none()

    if stored_token is not None and not stored_token.revoked:
        stored_token.revoked = True
        await db.commit()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> User:
    existing = await db.execute(
        select(User).where(
            User.username == payload.username
        )
    )

    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Username '{payload.username}' "
                "is already taken"
            ),
        )

    user = User(
        username=payload.username,
        hashed_password=hash_password(
            payload.password
        ),
        role=payload.role,
        technician_id=payload.technician_id,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
