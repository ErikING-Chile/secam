"""Pydantic schemas for request/response validation."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from .models import TenantStatus, PlanType, UserRole, UserStatus


# ============================================
# AUTH SCHEMAS
# ============================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    role: Optional[str] = None


class UserLogin(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """Register request (Super Admin only)."""
    tenant_name: str = Field(..., min_length=2, max_length=255)
    tenant_slug: str = Field(..., min_length=2, max_length=100, pattern="^[a-z0-9-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.TENANT_ADMIN


class UserResponse(BaseModel):
    """User response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime


class UserUpdate(BaseModel):
    """Update user request."""
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class MeResponse(BaseModel):
    """Current user info response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    email: str
    role: UserRole
    tenant_name: str
    tenant_slug: str
    tenant_plan: PlanType


# ============================================
# TENANT SCHEMAS
# ============================================

class TenantResponse(BaseModel):
    """Tenant response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    slug: str
    plan: PlanType
    status: TenantStatus
    created_at: datetime


class TenantUpdate(BaseModel):
    """Tenant update request."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    plan: Optional[PlanType] = None
    status: Optional[TenantStatus] = None


# ============================================
# CAMERA SCHEMAS (Phase 2)
# ============================================

class CameraCreate(BaseModel):
    """Create camera request."""
    name: str = Field(..., min_length=1, max_length=255)
    rtsp_url: str = Field(..., min_length=1)
    location: Optional[str] = None
    config: Optional[dict] = None


class CameraResponse(BaseModel):
    """Camera response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    name: str
    status: str
    location: Optional[str]
    created_at: datetime


class CameraUpdate(BaseModel):
    """Update camera request."""
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    location: Optional[str] = None
    config: Optional[dict] = None


# ============================================
# PERSON SCHEMAS (Phase 4)
# ============================================

class PersonCreate(BaseModel):
    """Create person request."""
    name: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None


class PersonResponse(BaseModel):
    """Person response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    name: str
    notes: Optional[str]
    status: str
    created_at: datetime


class PersonUpdate(BaseModel):
    """Update person request."""
    name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class FaceEmbeddingResponse(BaseModel):
    """Face embedding response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    person_id: UUID
    source_image_path: Optional[str]
    created_at: datetime


# ============================================
# EVENT SCHEMAS (Phase 3)
# ============================================

class EventType(str, Enum):
    """Event type options."""
    UNKNOWN_FACE = "unknown_face"
    KNOWN_FACE = "known_face"
    CAMERA_OFFLINE = "camera_offline"
    MOTION_DETECTED = "motion_detected"


class EventResponse(BaseModel):
    """Event response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    camera_id: Optional[UUID]
    type: str
    confidence: Optional[float]
    snapshot_path: Optional[str]
    created_at: datetime


class EventCreate(BaseModel):
    """Create event request."""
    camera_id: Optional[UUID] = None
    type: str
    confidence: Optional[float] = None
    snapshot_path: Optional[str] = None
    metadata: Optional[dict] = None


# ============================================
# AUDIT LOG SCHEMAS
# ============================================

class AuditLogResponse(BaseModel):
    """Audit log response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID]
    action: str
    resource: Optional[str]
    created_at: datetime


# ============================================
# HEALTH CHECK
# ============================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str
    database: str
    redis: str
    timestamp: datetime


# ============================================
# ADMIN SCHEMAS (Phase 6)
# ============================================

class AdminStatsResponse(BaseModel):
    """Admin statistics response."""
    total_tenants: int
    active_tenants: int
    total_users: int
    total_cameras: int
    total_persons: int
    total_events: int
    tenants_by_plan: dict
