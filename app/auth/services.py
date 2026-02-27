"""Authentication services."""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SECRET_KEY
from app.database.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password."""
    user = await get_user_by_username(db, username)
    if user and verify_password(password, user.password_hash):
        return user
    return None


def generate_totp_secret() -> str:
    """Generate new TOTP secret for 2FA."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str, issuer: str = "ControlServer") -> str:
    """Get provisioning URI for Google Authenticator."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, token: str) -> bool:
    """Verify TOTP token."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)
