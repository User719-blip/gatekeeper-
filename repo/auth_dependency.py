import os
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from db.deps import get_db
from repo.admin_store import get_admin_by_username
from repo.security import ALGORITHM, SECRET_KEY

API_KEY = os.getenv("API_KEY", "my123")

def require_api_key(x_api_key: str | None = Header(default=None, alias="x-api-key")) -> None:
    """Validate x-api-key header for public endpoints."""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized"},
        )


def require_roles(*allowed_roles: str):
    """
    Creates a dependency that validates JWT access token and checks user role.
    - Validates token type is 'access' (not refresh)
    - Verifies user exists and is active in DB
    - Checks user role matches one of allowed_roles
    """
    async def _require_roles(
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> dict:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Missing or invalid authorization header"},
            )
        
        token = authorization.split(" ", 1)[1]
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid token"},
            )
        
        # Validate token type - must be access token, not refresh
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Token type must be access, not refresh"},
            )
        
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid token: missing username"},
            )
        
        # Check DB for source-of-truth role and active status
        admin = get_admin_by_username(db, username)
        if not admin or not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Admin not found or inactive"},
            )
        
        # Verify role matches one of allowed roles
        if admin.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": f"Insufficient permissions. Required: {allowed_roles}"},
            )
        
        return {"username": username, "role": admin.role}
    
    return _require_roles


def require_admin(
    credentials: dict = Depends(require_roles("admin", "superadmin")),
) -> dict:
    """Convenience dependency: requires admin or superadmin role."""
    return credentials


def require_superadmin(
    credentials: dict = Depends(require_roles("superadmin")),
) -> dict:
    """Convenience dependency: requires superadmin role only."""
    return credentials
