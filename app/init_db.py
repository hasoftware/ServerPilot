"""Initialize database with default user (Admin/Admin)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services import get_password_hash
from app.database.database import async_session
from app.database.models import User


async def ensure_default_user() -> None:
    """Create default Admin user if not exists."""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == "Admin"))
        if result.scalar_one_or_none():
            return

        user = User(
            username="Admin",
            password_hash=get_password_hash("Admin"),
            must_change_password=True,
            totp_verified=False,
        )
        db.add(user)
        await db.commit()
