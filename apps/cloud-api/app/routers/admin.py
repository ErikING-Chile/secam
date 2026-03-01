"""Admin router - Super Admin panel operations."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import get_db
from ..models import Tenant, User, Camera, Event, Person, AuditLog, UserRole, TenantStatus
from ..schemas import (
    TenantResponse, TenantUpdate,
    UserResponse, UserUpdate,
    AdminStatsResponse,
)
from ..security import get_current_super_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get global statistics for the admin dashboard.
    """
    total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
    active_tenants = db.query(func.count(Tenant.id)).filter(
        Tenant.status == TenantStatus.ACTIVE
    ).scalar() or 0
    
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_cameras = db.query(func.count(Camera.id)).scalar() or 0
    total_persons = db.query(func.count(Person.id)).scalar() or 0
    total_events = db.query(func.count(Event.id)).scalar() or 0
    
    tenants_by_plan = db.query(
        Tenant.plan,
        func.count(Tenant.id)
    ).group_by(Tenant.plan).all()
    
    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "total_users": total_users,
        "total_cameras": total_cameras,
        "total_persons": total_persons,
        "total_events": total_events,
        "tenants_by_plan": {plan.value: count for plan, count in tenants_by_plan}
    }


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: Optional[TenantStatus] = None,
):
    """
    List all tenants (Super Admin only).
    """
    query = db.query(Tenant)
    
    if status_filter:
        query = query.filter(Tenant.status == status_filter)
    
    tenants = query.offset(offset).limit(limit).all()
    return tenants


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get tenant details (Super Admin only).
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update tenant (Super Admin only).
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if data.name is not None:
        tenant.name = data.name
    
    if data.plan is not None:
        tenant.plan = data.plan
    
    if data.status is not None:
        tenant.status = data.status
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.get("/tenants/{tenant_id}/users", response_model=List[UserResponse])
async def list_tenant_users(
    tenant_id: UUID,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """
    List all users for a specific tenant (Super Admin only).
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    users = db.query(User).filter(User.tenant_id == tenant_id).all()
    return users


@router.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: UUID,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a specific tenant (Super Admin only).
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 0
    camera_count = db.query(func.count(Camera.id)).filter(Camera.tenant_id == tenant_id).scalar() or 0
    person_count = db.query(func.count(Person.id)).filter(Person.tenant_id == tenant_id).scalar() or 0
    event_count = db.query(func.count(Event.id)).filter(Event.tenant_id == tenant_id).scalar() or 0
    
    return {
        "tenant_id": str(tenant_id),
        "tenant_name": tenant.name,
        "user_count": user_count,
        "camera_count": camera_count,
        "person_count": person_count,
        "event_count": event_count,
    }


@router.get("/audit-logs")
async def list_audit_logs(
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List audit logs (Super Admin only).
    """
    logs = db.query(AuditLog).order_by(
        AuditLog.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return logs
