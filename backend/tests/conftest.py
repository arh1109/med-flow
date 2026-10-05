from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings
from app.dependencies import get_db
from app.main import app as fastapi_app
from app.models.base import Base

# Makes sure all ORM models are registered with Base.metadata.
# The alias prevents this import from overwriting fastapi_app.
from app import models as _models  # noqa: F401
from app.models import User, UserRole
from app.security import hash_password


def build_test_database_url() -> str:
    configured_test_url = getattr(
        settings,
        "test_database_url",
        None,
    )

    if configured_test_url:
        url = make_url(configured_test_url)

    else:
        url = make_url(settings.database_url)

        current_database = url.database

        if not current_database:
            raise RuntimeError(
                "DATABASE_URL must contain a database name."
            )

        if current_database.endswith("_test"):
            test_database = current_database
        else:
            test_database = f"{current_database}_test"

        url = url.set(
            database=test_database
        )

    if (
        not url.database
        or not url.database.endswith("_test")
    ):
        raise RuntimeError(
            "Refusing to run pytest against a "
            "non-test database. "
            f"Resolved database: {url.database!r}"
        )

    return url.render_as_string(
        hide_password=False
    )


TEST_DATABASE_URL = build_test_database_url()


test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,

    # Important for pytest + asyncpg.
    # Prevent connections created on one asyncio loop
    # from being reused on another loop.
    poolclass=NullPool,
)


@pytest_asyncio.fixture(
    scope="session",
    autouse=True,
)
async def prepare_test_database():
    """
    Create a clean schema before the test session
    and remove it afterward.
    """

    async with test_engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.drop_all
        )

        await connection.run_sync(
            Base.metadata.create_all
        )

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.drop_all
        )

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    prepare_test_database,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Each test runs inside an outer transaction.

    Code inside the app can call session.commit(),
    but the test transaction is rolled back afterward.
    """

    async with test_engine.connect() as connection:

        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session

        finally:
            await session.close()

            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client whose FastAPI get_db dependency
    points at the isolated pytest database session.
    """

    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = (
        override_get_db
    )

    transport = ASGITransport(
        app=fastapi_app
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:

        yield test_client

    fastapi_app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_user(
    db_session: AsyncSession,
):
    user = User(
        username="pytest_admin",
        hashed_password=hash_password(
            "TestPassword123!"
        ),
        role=UserRole.CLINICAL_ADMIN,
        is_active=True,
        technician_id=None,
    )

    db_session.add(user)

    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
def auth_credentials():
    return {
        "username": "pytest_admin",
        "password": "TestPassword123!",
    }

@pytest_asyncio.fixture
async def rbac_users(
    db_session: AsyncSession,
):
    """
    Create one user for each MedFlow role.

    The Field Technician needs a Technician row first because users.technician_id
    is a real foreign key.
    """

    from app.models import (
        Technician,
        User,
        UserRole,
    )
    from app.security import hash_password

    technician = Technician(
        id=901,
        name="Pytest Technician",
        hospital_id=None,
    )

    db_session.add(technician)
    await db_session.flush()

    password = "TestPassword123!"

    admin = User(
        username="rbac_admin",
        hashed_password=hash_password(password),
        role=UserRole.CLINICAL_ADMIN,
        is_active=True,
        technician_id=None,
    )

    auditor = User(
        username="rbac_auditor",
        hashed_password=hash_password(password),
        role=UserRole.AUDITOR,
        is_active=True,
        technician_id=None,
    )

    technician_user = User(
        username="rbac_technician",
        hashed_password=hash_password(password),
        role=UserRole.FIELD_TECHNICIAN,
        is_active=True,
        technician_id=technician.id,
    )

    db_session.add_all([
        admin,
        auditor,
        technician_user,
    ])

    await db_session.commit()

    await db_session.refresh(admin)
    await db_session.refresh(auditor)
    await db_session.refresh(technician_user)

    return {
        "admin": admin,
        "auditor": auditor,
        "technician": technician_user,
        "password": password,
    }


@pytest_asyncio.fixture
async def rbac_headers(
    client,
    rbac_users,
):
    """
    Log in all three roles through the real /auth/token endpoint and return
    Authorization headers ready for route tests.
    """

    async def login_headers(username: str):
        response = await client.post(
            "/auth/token",
            data={
                "username": username,
                "password": rbac_users["password"],
            },
        )

        assert response.status_code == 200

        access_token = response.json()["access_token"]

        return {
            "Authorization": f"Bearer {access_token}"
        }

    return {
        "admin": await login_headers(
            rbac_users["admin"].username
        ),
        "auditor": await login_headers(
            rbac_users["auditor"].username
        ),
        "technician": await login_headers(
            rbac_users["technician"].username
        ),
    }
