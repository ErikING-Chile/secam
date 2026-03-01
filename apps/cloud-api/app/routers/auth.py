"""Authentication router - login, register, refresh, logout."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import create_access_token, create_refresh_token, get_password_hash, verify_password
from ..db import get_db
from ..models import User, Tenant, AuditLog, UserRole, UserStatus, TenantStatus, PlanType
from ..schemas import (
    UserLogin,
    UserRegister,
    Token,
    UserResponse,
    MeResponse,
)
from ..security import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new tenant and admin user.
    
    **Note:** In production, this should be restricted to super admins only
    or disabled with manual tenant creation.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if slug already exists
    existing_tenant = db.query(Tenant).filter(Tenant.slug == data.tenant_slug).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant slug already taken"
        )
    
    # Create tenant
    tenant = Tenant(
        name=data.tenant_name,
        slug=data.tenant_slug,
        plan=PlanType.FREE,
        status=TenantStatus.ACTIVE
    )
    db.add(tenant)
    db.flush()  # Get tenant ID
    
    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=data.role,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    
    # Create audit log
    audit_log = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action="TENANT_CREATED",
        resource="tenant",
        action_metadata={"tenant_name": data.tenant_name, "email": data.email}
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns access token and refresh token.
    """
    # Find user by email
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check user status
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    
    # Check tenant status
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or tenant.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is not active"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role.value,
            "email": user.email
        }
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id)
        }
    )
    
    # Log login
    audit_log = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="USER_LOGIN",
        resource="auth",
        action_metadata={"email": user.email}
    )
    db.add(audit_log)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    from ..auth import verify_refresh_token
    
    payload = verify_refresh_token(refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )
    
    # Verify user still exists and is active
    user = db.query(User).filter(
        User.id == UUID(user_id),
        User.tenant_id == UUID(tenant_id)
    ).first()
    
    if not user or user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active"
        )
    
    # Create new tokens
    new_access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role.value,
            "email": user.email
        }
    )
    
    new_refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id)
        }
    )
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user.
    
    In a production system with token blacklist, you would add the token
    to a blacklist in Redis. For now, this is a no-op since JWTs are stateless.
    """
    # Log logout
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="USER_LOGOUT",
        resource="auth",
        metadata={"email": current_user.email}
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information.
    """
    # Get tenant info
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return MeResponse(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        role=current_user.role,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        tenant_plan=tenant.plan
    )
