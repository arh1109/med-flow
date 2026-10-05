import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hospital


@pytest.mark.asyncio
async def test_database_connection(
    db_session: AsyncSession,
):
    """
    Smoke test: pytest can execute SQL against the isolated PostgreSQL database.
    """

    result = await db_session.execute(
        text("SELECT 1")
    )

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_database_can_persist_model(
    db_session: AsyncSession,
):
    """
    Proves that SQLAlchemy mappings/tables were created correctly.
    """

    hospital = Hospital(
        name="Pytest Medical Center",
        location_region="TEST-EAST",
        capacity=25,
        supervisor_id=9001,
    )

    db_session.add(hospital)
    await db_session.commit()
    await db_session.refresh(hospital)

    assert hospital.id is not None

    result = await db_session.execute(
        select(Hospital).where(
            Hospital.id == hospital.id
        )
    )

    stored_hospital = (
        result.scalar_one()
    )

    assert stored_hospital.name == (
        "Pytest Medical Center"
    )
    assert stored_hospital.capacity == 25


@pytest.mark.asyncio
async def test_database_is_clean_between_tests(
    db_session: AsyncSession,
):
    """
    The Hospital inserted by the previous test should have been rolled back.
    """

    result = await db_session.execute(
        select(Hospital).where(
            Hospital.name
            == "Pytest Medical Center"
        )
    )

    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_health_route_uses_test_client(
    client,
):
    """
    First FastAPI smoke test. This route does not require authentication.
    """

    response = await client.get(
        "/health"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok"
    }
