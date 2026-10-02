from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models import User, UserRole, Technician
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.security import hash_password


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
) -> list[User]:

    statement = select(User).order_by(User.id)

    result = await db.execute(statement)

    return list(result.scalars().all())

async def validate_technician_assignment(
    db: AsyncSession,
    role: UserRole,
    technician_id: int | None,
    exclude_user_id: int | None = None,
) -> None:

    if role == UserRole.FIELD_TECHNICIAN:
        if technician_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Field Technician users must be "
                    "linked to a technician"
                ),
            )

        technician = await db.get(
            Technician,
            technician_id,
        )

        if technician is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Technician {technician_id} "
                    "does not exist"
                ),
            )

        statement = select(User).where(
            User.technician_id == technician_id
        )

        if exclude_user_id is not None:
            statement = statement.where(
                User.id != exclude_user_id
            )

        result = await db.execute(statement)

        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Technician {technician_id} "
                    "already has a user account"
                ),
            )

    elif technician_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only Field Technician users may "
                "have a technician_id"
            ),
        )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
) -> User:

    user = await db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return user


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
) -> User:

    # Prevent duplicate usernames.
    statement = select(User).where(User.username == payload.username)

    result = await db.execute(statement)

    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' already exists",
        )

    await validate_technician_assignment(
        db=db,
        role=payload.role,
        technician_id=payload.technician_id,
    )

    user = User(
        username=payload.username,
        hashed_password=hash_password(
            payload.password
        ),
        role=payload.role,
        technician_id=payload.technician_id,
        is_active=True,
    )
    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
) -> User:

    user = await db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Check that the new username isn't already owned by somebody else.
    statement = select(User).where(
        User.username == payload.username,
        User.id != user_id,
    )

    result = await db.execute(statement)

    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' already exists",
        )

    # Validate the technician relationship before mutating the user.
    await validate_technician_assignment(
        db=db,
        role=payload.role,
        technician_id=payload.technician_id,
        exclude_user_id=user_id,
    )

    user.username = payload.username
    user.role = payload.role
    user.technician_id = payload.technician_id

    # Only replace password when Admin entered a new one.
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    await db.commit()
    await db.refresh(user)

    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN)
    ),
) -> None:

    user = await db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user account",
        )

    await db.delete(user)
    await db.commit()