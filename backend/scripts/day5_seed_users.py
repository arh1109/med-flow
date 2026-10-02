import asyncio

from app.database import AsyncSessionLocal
from app.models import User, UserRole
from app.security import hash_password


async def seed_users() -> None:
    async with AsyncSessionLocal() as session:
        session.add_all([
            User(
                username="admin",
                hashed_password=hash_password("AdminPass123!"),
                role=UserRole.CLINICAL_ADMIN,
                technician_id=None,
            ),
            User(
                username="operator",
                hashed_password=hash_password("OperatorPass123!"),
                role=UserRole.FIELD_TECHNICIAN,
                technician_id=201,
            ),
            User(
                username="operator2",
                hashed_password=hash_password("Operator2Pass123!"),
                role=UserRole.FIELD_TECHNICIAN,
                technician_id=202,
            ),
            User(
                username="auditor",
                hashed_password=hash_password("AuditorPass123!"),
                role=UserRole.AUDITOR,
                technician_id=None,
            ),
        ])

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed_users())
