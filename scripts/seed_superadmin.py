import asyncio
import getpass
import os
import sys

from app.common.enums import UserRole
from app.core.security import hash_password
from app.db.base import import_models
from app.db.session import get_engine, get_session_factory
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


def _prompt_if_missing(env_key: str, prompt_text: str, *, secret: bool = False) -> str:
    """Read value from environment variable or prompt interactively."""
    value = os.getenv(env_key, "").strip()
    if value:
        return value
    if secret:
        return getpass.getpass(prompt_text).strip()
    return input(prompt_text).strip()


async def seed_superadmin() -> int:
    """Create the initial Super Admin account if it does not already exist."""
    import_models()

    full_name = _prompt_if_missing("SEED_SUPERADMIN_FULL_NAME", "To'liq ism: ")
    email = _prompt_if_missing("SEED_SUPERADMIN_EMAIL", "Email: ").lower()
    password = _prompt_if_missing(
        "SEED_SUPERADMIN_PASSWORD",
        "Parol (kamida 8 belgi): ",
        secret=True,
    )

    if not full_name or not email or "@" not in email:
        print("Xato: to'liq ism va yaroqli email kiritilishi shart.")
        return 1

    if len(password) < 8:
        print("Xato: parol kamida 8 ta belgidan iborat bo'lishi kerak.")
        return 1

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(email)
        if existing is not None:
            print(f"Foydalanuvchi allaqachon mavjud: {existing.email} (rol: {existing.role.value})")
            return 0

        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        await repo.add(user)
        await session.commit()
        print(f"Super Admin muvaffaqiyatli yaratildi: {user.email} (id={user.id})")
        return 0


def main() -> int:
    """Run the async seed command and dispose engine cleanly."""

    async def _runner() -> int:
        try:
            return await seed_superadmin()
        finally:
            await get_engine().dispose()

    return asyncio.run(_runner())


if __name__ == "__main__":
    sys.exit(main())
