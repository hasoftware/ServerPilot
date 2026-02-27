"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_auth, require_setup_complete
from app.auth.services import (
    authenticate_user,
    get_password_hash,
    create_access_token,
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
    get_user_by_username,
)
from app.database.database import get_db
from app.database.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class Setup2FARequest(BaseModel):
    totp_code: str


# Pydantic models for responses
class AuthResponse(BaseModel):
    token: str
    must_change_password: bool
    totp_required: bool


class Setup2FAResponse(BaseModel):
    secret: str
    uri: str
    qr_placeholder: str  # Base64 QR or placeholder


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login and get token."""
    user = await authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(data={"sub": user.username})
    req.session["token"] = token
    req.session["username"] = user.username

    return AuthResponse(
        token=token,
        must_change_password=user.must_change_password,
        totp_required=not user.totp_verified,
    )


@router.post("/logout")
async def logout(request: Request):
    """Logout - clear session."""
    request.session.clear()
    return {"message": "Logged out"}


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Change password (required on first login)."""
    from app.auth.services import verify_password

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = get_password_hash(data.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.get("/setup-2fa", response_model=Setup2FAResponse)
async def setup_2fa(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get 2FA setup data (secret + URI for QR)."""
    if current_user.totp_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled",
        )

    secret = current_user.totp_secret or generate_totp_secret()
    if not current_user.totp_secret:
        current_user.totp_secret = secret
        db.add(current_user)
        await db.commit()

    uri = get_totp_uri(secret, current_user.username)
    return Setup2FAResponse(secret=secret, uri=uri, qr_placeholder=uri)


@router.post("/verify-2fa")
async def verify_2fa(
    data: Setup2FARequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Verify and enable 2FA."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not initialized. Call setup-2fa first.",
        )

    if not verify_totp(current_user.totp_secret, data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )

    current_user.totp_verified = True
    db.add(current_user)
    await db.commit()

    return {"message": "2FA enabled successfully"}


@router.get("/me")
async def get_me(current_user: User = Depends(require_setup_complete)):
    """Get current user info (requires full setup)."""
    return {
        "username": current_user.username,
        "must_change_password": current_user.must_change_password,
        "totp_verified": current_user.totp_verified,
    }
