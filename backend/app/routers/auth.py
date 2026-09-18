"""Auth router: register, login, refresh, logout, current user."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AuditLog, RefreshToken, User, UserRole
from app.schemas import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserOut

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["auth"])


def _error(code: str, message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        _error("EMAIL_TAKEN", "Email already registered", 409)

    user = User(
        id=uuid.uuid4(),
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        role=UserRole.clinician,
    )
    db.add(user)
    db.add(AuditLog(id=uuid.uuid4(), user_id=user.id, action="user.register", resource_type="user", resource_id=str(user.id), details={"email": user.email}))
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower().strip()))
    user = result.scalar_one_or_none()
    # Generic error - don't reveal which field is wrong
    if user is None or not verify_password(body.password, user.hashed_password) or not user.is_active:
        _error("INVALID_CREDENTIALS", "Invalid email or password", 401)

    settings = get_settings()
    access_token = create_access_token(str(user.id), user.role.value)
    raw_refresh, hashed_refresh = create_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    rt = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        hashed_token=hashed_refresh,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(rt)
    db.add(AuditLog(id=uuid.uuid4(), user_id=user.id, action="user.login", resource_type="user", resource_id=str(user.id), details={}))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed = hash_refresh_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.hashed_token == hashed, RefreshToken.revoked.is_(False))
    )
    rt = result.scalar_one_or_none()
    if rt is None or rt.expires_at < datetime.now(UTC):
        _error("INVALID_TOKEN", "Refresh token invalid or expired", 401)

    # Revoke old token
    rt.revoked = True

    result2 = await db.execute(select(User).where(User.id == rt.user_id, User.is_active.is_(True)))
    user = result2.scalar_one_or_none()
    if user is None:
        _error("USER_NOT_FOUND", "User not found", 401)

    settings = get_settings()
    access_token = create_access_token(str(user.id), user.role.value)
    raw_refresh, hashed_refresh = create_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_rt = RefreshToken(id=uuid.uuid4(), user_id=user.id, hashed_token=hashed_refresh, expires_at=expires_at)
    db.add(new_rt)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/auth/logout", status_code=204)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed = hash_refresh_token(body.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.hashed_token == hashed))
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()


@router.get("/users/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
