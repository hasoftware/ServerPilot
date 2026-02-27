"""Auth dependencies for FastAPI."""
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services import decode_token
from app.database.database import get_db
from app.database.models import User
from app.database.database import async_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)] = None,
) -> Optional[User]:
    """Get current user from session or Bearer token."""
    # Try session cookie first (for web UI)
    session_token = request.session.get("token")
    token = token or (credentials.credentials if credentials else None) or session_token

    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    async with async_session() as db:
        from app.auth.services import get_user_by_username
        user = await get_user_by_username(db, username)
        return user


async def require_auth(current_user: Annotated[Optional[User], Depends(get_current_user)]) -> User:
    """Require authenticated user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_setup_complete(current_user: Annotated[User, Depends(require_auth)]) -> User:
    """Require user to have completed setup (password change + 2FA)."""
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="must_change_password",
        )
    if not current_user.totp_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="totp_required",
        )
    return current_user
