from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from repo.rate_limiter import get_login_rate_limit, limiter
from db.deps import get_db
from repo.admin_store import (
    count_admins,
    count_superadmins,
    create_admin,
    delete_admin_by_username,
    get_admin_by_username,
    get_refresh_token,
    revoke_refresh_token,
    save_refresh_token,
)
from repo.auth_dependency import require_api_key, require_superadmin
from repo.security import (
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from schema.admin_schema import (
    AdminCreate,
    AdminLogin,
    RefreshTokenRequest,
    TokenPairResponse,
    TokenResponse,
)

admin_router = APIRouter(prefix="/admin", tags=["admin-auth"])


@admin_router.post("/register")
async def register_admin(
    payload: AdminCreate,
    _: None = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    existing = get_admin_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    role = "superadmin" if count_admins(db) == 0 else "admin"
    try:
        create_admin(db, payload.username, hash_password(payload.password), role=role)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Admin already exists or invalid admin data")

    return {"message": f"Admin created as {role}"}

@admin_router.post("/login", response_model=TokenPairResponse)
@limiter.limit(get_login_rate_limit())
async def login_admin(request: Request, payload: AdminLogin, db: Session = Depends(get_db)):
    admin = get_admin_by_username(db, payload.username)
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(admin.username, admin.role)
    refresh_token = create_refresh_token(admin.username)
    refresh_hash = hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    save_refresh_token(db, admin.username, refresh_hash, expires_at)

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@admin_router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    refresh_hash = hash_token(payload.refresh_token)
    stored = get_refresh_token(db, refresh_hash)

    if not stored or stored.is_revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Ensure expires_at is timezone-aware for comparison
    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    try:
        token_payload = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if token_payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    username = token_payload.get("sub")
    admin = get_admin_by_username(db, username)
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive or missing admin")

    access_token = create_access_token(admin.username, admin.role)
    return TokenResponse(access_token=access_token, token_type="bearer")


@admin_router.post("/logout")
async def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    refresh_hash = hash_token(payload.refresh_token)
    stored = get_refresh_token(db, refresh_hash)

    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    revoke_refresh_token(db, refresh_hash)
    return {"message": "Logged out successfully"}


@admin_router.post("/promote/{username}")
async def promote_admin(
    username: str,
    _: dict = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    admin = get_admin_by_username(db, username)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    admin.role = "superadmin"
    db.commit()
    db.refresh(admin)
    return {"message": f"{username} promoted to superadmin"}


@admin_router.delete("/remove/{username}")
async def remove_admin(
    username: str,
    _: dict = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    admin = get_admin_by_username(db, username)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if admin.role == "superadmin" and count_superadmins(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last superadmin")

    delete_admin_by_username(db, username)
    return {"message": f"{username} removed"}