"""Streaming router - MJPEG video streaming for cameras."""
import threading
from uuid import UUID
from typing import Dict, Optional

import cv2
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse

from ..db import get_db
from ..models import Camera, User
from ..security import get_current_user
from ..config import settings
from cryptography.fernet import Fernet

router = APIRouter(prefix="/cameras", tags=["Streaming"])

stream_cache: Dict[str, dict] = {}
stream_lock = threading.Lock()


def get_fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Encryption key not configured"
        )
    return Fernet(settings.ENCRYPTION_KEY.encode())


def decrypt_rtsp_url(encrypted_url: str, fernet: Fernet) -> str:
    return fernet.decrypt(encrypted_url.encode()).decode()


def generate_frames(rtsp_url: str, camera_id: str):
    """Generate MJPEG frames from RTSP stream."""
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        yield b"--frame\r\nContent-Type: text/plain\r\n\r\nStream unavailable\r\n"
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()
            
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
    except Exception as e:
        yield (b"--frame\r\n"
               b"Content-Type: text/plain\r\n\r\n".encode() + 
               f"Stream error: {str(e)}".encode() + b"\r\n")
    finally:
        cap.release()


@router.get("/{camera_id}/snapshot")
async def get_snapshot(
    camera_id: UUID,
    token: Optional[str] = None,
    db = Depends(get_db)
):
    """
    Get a single snapshot from the camera.
    Accepts token as query parameter for browser compatibility.
    """
    from ..security import verify_access_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required"
        )
    
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.tenant_id == user.tenant_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    fernet = get_fernet()
    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, fernet)
    
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera stream unavailable"
        )
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to capture frame"
        )
    
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    
    return Response(
        content=buffer.tobytes(),
        media_type="image/jpeg"
    )


@router.get("/{camera_id}/stream")
async def stream_camera(
    camera_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Stream camera video as MJPEG.
    
    Returns a continuous JPEG stream that can be displayed in an img tag.
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
    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, fernet)
    
    response = StreamingResponse(
        generate_frames(rtsp_url, str(camera_id)),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
    
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response
