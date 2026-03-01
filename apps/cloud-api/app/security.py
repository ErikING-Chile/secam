"""Security middleware and dependencies."""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .auth import verify_access_token, verify_refresh_token
from .db import get_db
from .models import User, Tenant
from .schemas import TokenData

# HTTP Bearer token security
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = verify_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    
    if user_id is None or tenant_id is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(
        User.id == UUID(user_id),
        User.tenant_id == UUID(tenant_id)
    ).first()
    
    if user is None:
        raise credentials_exception
    
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (alias with explicit check)."""
    if current_user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are a super admin."""
    if current_user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_current_tenant_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are a tenant admin."""
    if current_user.role.value not in ["super_admin", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin access required"
        )
    return current_user


def get_token_data(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Extract token data without database lookup (for lightweight auth)."""
    token = credentials.credentials
    payload = verify_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenData(
        user_id=payload.get("sub"),
        tenant_id=payload.get("tenant_id"),
        role=payload.get("role")
    )


async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> str:
    """Refresh access token using refresh token."""
    payload = verify_refresh_token(refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    
    if user_id is None or tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )
    
    # Verify user still exists and is active
    user = db.query(User).filter(
        User.id == UUID(user_id),
        User.tenant_id == UUID(tenant_id)
    ).first()
    
    if user is None or user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active"
        )
    
    # Create new access token
    from .auth import create_access_token
    
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role.value,
            "email": user.email
        }
    )
    
    return access_token
