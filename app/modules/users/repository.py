import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.validators import escape_like
from app.modules.users.models import User


class UserRepository:
    """Data access layer for User entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user by primary key UUID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by case-insensitive email address."""
        normalized_email = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self,
        *,
        offset: int,
        limit: int,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        """Return paginated users matching optional role, status, and search filters."""
        conditions = []
        if role is not None:
            conditions.append(User.role == role)
        if is_active is not None:
            conditions.append(User.is_active.is_(is_active))
        if search and search.strip():
            pattern = f"%{escape_like(search.strip())}%"
            conditions.append(
                or_(
                    User.full_name.ilike(pattern, escape="\\"),
                    User.email.ilike(pattern, escape="\\"),
                )
            )

        count_stmt = select(func.count(User.id)).where(*conditions)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        items_stmt = (
            select(User)
            .where(*conditions)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return items, total

    async def add(self, user: User) -> User:
        """Stage a new User instance in the current session and flush."""
        self.session.add(user)
        await self.session.flush()
        return user

    async def save(self, user: User) -> User:
        """Flush pending changes for an existing User instance."""
        await self.session.flush()
        return user
