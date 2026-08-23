import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token,
)
from app.core.config import get_settings
from app.models.user import User
from app.schemas.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    base = body.email.split("@")[0].lower()[:90]
    username = base
    suffix = 1
    while db.query(User).filter(User.username == username).first():
        suffix += 1
        username = f"{base}{suffix}"
    user = User(email=body.email, username=username, password_hash=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    payload = {"sub": str(user.id)}
    return TokenResponse(access_token=create_access_token(payload), refresh_token=create_refresh_token(payload))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    payload = {"sub": str(user.id)}
    return TokenResponse(access_token=create_access_token(payload), refresh_token=create_refresh_token(payload))


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token, settings.REFRESH_SECRET_KEY)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    new_payload = {"sub": payload["sub"]}
    return TokenResponse(access_token=create_access_token(new_payload), refresh_token=create_refresh_token(new_payload))


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}


@router.post("/reset-password/request")
def reset_password_request(email: str, db: Session = Depends(get_db)):
    # Always return the same public response to avoid account enumeration.
    user = db.query(User).filter(User.email == email).first()
    response = {"message": "If that email exists, a reset link has been generated."}
    if not user:
        return response

    raw_token = secrets.token_urlsafe(48)
    user.reset_token_hash = _hash_reset_token(raw_token)
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()

    # Local-development delivery: the link is returned only in dev mode so the
    # feature can be tested without an SMTP provider. Production should wire
    # this token into an email service.
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={quote(raw_token)}"
    response["reset_link"] = reset_link
    return response


@router.post("/reset-password/confirm")
def reset_password_confirm(token: str, new_password: str, db: Session = Depends(get_db)):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    token_hash = _hash_reset_token(token)
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()
    if not user or not user.reset_token_expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    expires = user.reset_token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        user.reset_token_hash = None
        user.reset_token_expires_at = None
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    user.password_hash = hash_password(new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.commit()
    return {"message": "Password reset successful. You can now sign in."}
