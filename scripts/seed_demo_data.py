import asyncio
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.common.enums import UserRole
from app.core.security import hash_password
from app.db.base import import_models
from app.db.session import get_engine, get_session_factory
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.visitors.models import Visitor
from app.modules.visitors.repository import VisitorRepository
from app.modules.visits.models import Visit

_DEMO_PASSWORD = "DemoPass123!"

_DEMO_USERS: tuple[dict[str, object], ...] = (
    {
        "full_name": "Javohir Karimov",
        "email": "superadmin@aqlliolam.uz",
        "phone": "+998901000001",
        "role": UserRole.SUPER_ADMIN,
    },
    {
        "full_name": "Dilnoza Rahimova",
        "email": "admin@aqlliolam.uz",
        "phone": "+998901000002",
        "role": UserRole.ADMIN,
    },
    {
        "full_name": "Sardor Toshmatov",
        "email": "operator1@aqlliolam.uz",
        "phone": "+998901000003",
        "role": UserRole.OPERATOR,
    },
    {
        "full_name": "Madina Aliyeva",
        "email": "operator2@aqlliolam.uz",
        "phone": "+998901000004",
        "role": UserRole.OPERATOR,
    },
    {
        "full_name": "Bobur Qodirov",
        "email": "operator3@aqlliolam.uz",
        "phone": "+998901000005",
        "role": UserRole.OPERATOR,
    },
)

_DEMO_VISITORS: tuple[dict[str, str], ...] = (
    {
        "full_name": "Alisher Usmonov",
        "phone": "+998901112233",
        "document_number": "AA1234567",
        "organization": "TechSoft MChJ",
        "notes": "Doimiy hamkor",
    },
    {
        "full_name": "Zarina Mahmudova",
        "phone": "+998912223344",
        "document_number": "AB7654321",
        "organization": "O'zTelekom",
        "notes": "Shartnoma bo'yicha uchrashuv",
    },
    {
        "full_name": "Jasur Abdullayev",
        "phone": "+998933334455",
        "document_number": "AC9876543",
        "organization": "AgroBank",
        "notes": "Hujjatlar almashinuvi",
    },
    {
        "full_name": "Nilufar Tursunova",
        "phone": "+998944445566",
        "document_number": "AD4567890",
        "organization": "SilkRoad Logistics",
        "notes": "Kuryer / yetkazib berish",
    },
    {
        "full_name": "Otabek Saidov",
        "phone": "+998975556677",
        "document_number": "AE1122334",
        "organization": "NextGen Solutions",
        "notes": "Texnik audit",
    },
)


async def seed_demo_data() -> int:
    """Populate PostgreSQL with 5 demo users, 5 visitors, and 5 visits idempotently."""
    import_models()
    session_factory = get_session_factory()

    async with session_factory() as session:
        user_repo = UserRepository(session)
        visitor_repo = VisitorRepository(session)
        password_hash = hash_password(_DEMO_PASSWORD)

        users_by_email: dict[str, User] = {}
        created_users = 0
        for item in _DEMO_USERS:
            email = str(item["email"])
            existing = await user_repo.get_by_email(email)
            if existing is None:
                user = User(
                    full_name=str(item["full_name"]),
                    email=email,
                    phone=str(item["phone"]),
                    password_hash=password_hash,
                    role=UserRole(item["role"]),
                    is_active=True,
                )
                await user_repo.add(user)
                users_by_email[email] = user
                created_users += 1
            else:
                users_by_email[email] = existing

        operator_1 = users_by_email["operator1@aqlliolam.uz"]
        operator_2 = users_by_email["operator2@aqlliolam.uz"]

        visitors: list[Visitor] = []
        created_visitors = 0
        for item in _DEMO_VISITORS:
            existing_visitor = await visitor_repo.get_active_by_phone(item["phone"])
            if existing_visitor is None:
                visitor = Visitor(
                    full_name=item["full_name"],
                    phone=item["phone"],
                    document_number=item["document_number"],
                    organization=item["organization"],
                    notes=item["notes"],
                    created_by=operator_1.id,
                )
                await visitor_repo.add(visitor)
                visitors.append(visitor)
                created_visitors += 1
            else:
                visitors.append(existing_visitor)

        visits_count = int(
            (await session.execute(select(func.count(Visit.id)))).scalar_one()
        )
        created_visits = 0
        if visits_count == 0:
            now = datetime.now(UTC)
            demo_visits = (
                Visit(
                    visitor_id=visitors[0].id,
                    checked_in_by=operator_1.id,
                    purpose="Loyiha muhokamasi",
                    host_name="IT bo'limi",
                    badge_number="B-01",
                    checked_in_at=now - timedelta(hours=2),
                    checked_out_at=None,
                    notes="2-qavat majlislar xonasi",
                ),
                Visit(
                    visitor_id=visitors[1].id,
                    checked_in_by=operator_2.id,
                    purpose="Shartnoma imzolash",
                    host_name="Direktor qabulxonasi",
                    badge_number="B-02",
                    checked_in_at=now - timedelta(minutes=40),
                    checked_out_at=None,
                    notes="Original hujjatlar bilan",
                ),
                Visit(
                    visitor_id=visitors[2].id,
                    checked_in_by=operator_1.id,
                    checked_out_by=operator_1.id,
                    purpose="Hujjat topshirish",
                    host_name="Buxgalteriya",
                    badge_number="B-03",
                    checked_in_at=now - timedelta(hours=5),
                    checked_out_at=now - timedelta(hours=3, minutes=15),
                    notes="Qabul qilindi",
                ),
                Visit(
                    visitor_id=visitors[3].id,
                    checked_in_by=operator_2.id,
                    checked_out_by=operator_2.id,
                    purpose="Yetkazib berish",
                    host_name="Omborxona",
                    badge_number="B-04",
                    checked_in_at=now - timedelta(days=2, hours=4),
                    checked_out_at=now - timedelta(days=2, hours=2, minutes=30),
                    notes="Yuk topshirildi",
                ),
                Visit(
                    visitor_id=visitors[4].id,
                    checked_in_by=operator_1.id,
                    checked_out_by=operator_2.id,
                    purpose="Texnik ko'rik",
                    host_name="Xavfsizlik bo'limi",
                    badge_number="B-05",
                    checked_in_at=now - timedelta(days=10, hours=3),
                    checked_out_at=now - timedelta(days=10, hours=1, minutes=20),
                    notes="Server xonasi tekshiruvi",
                ),
            )
            session.add_all(demo_visits)
            created_visits = len(demo_visits)

        await session.commit()
        print(
            f"Demo data tayyor: users+{created_users}, "
            f"visitors+{created_visitors}, visits+{created_visits}"
        )
        return 0


def main() -> int:
    """Run the demo seeder and dispose engine."""

    async def _runner() -> int:
        try:
            return await seed_demo_data()
        finally:
            await get_engine().dispose()

    return asyncio.run(_runner())


if __name__ == "__main__":
    sys.exit(main())
