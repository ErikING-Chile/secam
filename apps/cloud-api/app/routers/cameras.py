"""Camera router - CRUD operations for cameras."""
from typing import List, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cryptography.fernet import Fernet
from ..db import get_db
from ..models import Camera, User, AuditLog
from ..rtsp_diagnostics import diagnose_rtsp_url
from ..schemas import CameraCreate, CameraResponse, CameraUpdate, RTSPDiagnosticResponse
from ..security import get_current_user
from ..config import settings

router = APIRouter(prefix="/cameras", tags=["Cameras"])


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    if not settings.ENCRYPTION_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Encryption key not configured"
        )
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_rtsp_url(url: str, fernet: Fernet) -> str:
    """Encrypt RTSP URL."""
    return fernet.encrypt(url.encode()).decode()


def decrypt_rtsp_url(encrypted_url: str, fernet: Fernet) -> str:
    """Decrypt RTSP URL."""
    return fernet.decrypt(encrypted_url.encode()).decode()


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    data: CameraCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new camera.
    
    The RTSP URL will be encrypted before storage.
    """
    fernet = get_fernet()
    
    encrypted_rtsp = encrypt_rtsp_url(data.rtsp_url, fernet)
    
    camera = Camera(
        tenant_id=current_user.tenant_id,
        name=data.name,
        rtsp_url_encrypted=encrypted_rtsp,
        location=data.location,
        config_json=data.config,
        status="offline"
    )
    db.add(camera)
    
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="CAMERA_CREATED",
        resource="camera",
        action_metadata={"camera_name": data.name, "camera_id": str(camera.id)}
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(camera)
    
    return camera


@router.get("", response_model=List[CameraResponse])
async def list_cameras(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all cameras for the current tenant.
    """
    cameras = db.query(Camera).filter(
        Camera.tenant_id == current_user.tenant_id
    ).all()
    
    return cameras


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific camera by ID.
    """
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.tenant_id == current_user.tenant_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    return camera


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: UUID,
    data: CameraUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a camera.
    
    If rtsp_url is provided, it will be re-encrypted.
    """
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.tenant_id == current_user.tenant_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    if data.name is not None:
        camera.name = data.name
    
    if data.rtsp_url is not None:
        fernet = get_fernet()
        camera.rtsp_url_encrypted = encrypt_rtsp_url(data.rtsp_url, fernet)
    
    if data.location is not None:
        camera.location = data.location
    
    if data.config is not None:
        camera.config_json = data.config
    
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="CAMERA_UPDATED",
        resource="camera",
        action_metadata={"camera_name": camera.name, "camera_id": str(camera.id)}
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(camera)
    
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a camera.
    """
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.tenant_id == current_user.tenant_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="CAMERA_DELETED",
        resource="camera",
        action_metadata={"camera_name": camera.name, "camera_id": str(camera.id)}
    )
    db.add(audit_log)
    
    db.delete(camera)
    db.commit()
    
    return None


@router.post("/{camera_id}/test", response_model=RTSPDiagnosticResponse)
async def test_camera_connection(
    camera_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test camera connection and return structured diagnostics.
    """
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.tenant_id == current_user.tenant_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    fernet = get_fernet()
    rtsp_url = decrypt_rtsp_url(cast(str, camera.rtsp_url_encrypted), fernet)

    diagnostic = diagnose_rtsp_url(rtsp_url)
    diagnostic.camera_id = camera.id
    diagnostic.camera_name = camera.name

    return diagnostic
