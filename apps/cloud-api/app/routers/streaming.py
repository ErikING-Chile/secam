"""Streaming router - MJPEG video streaming for cameras."""
from uuid import UUID
from typing import Generator

import cv2
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Camera, User
from ..security import get_current_user_for_media
from ..config import settings
from cryptography.fernet import Fernet

router = APIRouter(prefix="/cameras", tags=["Streaming"])


def get_fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Encryption key not configured"
        )
    return Fernet(settings.ENCRYPTION_KEY.encode())


def decrypt_rtsp_url(encrypted_url: str, fernet: Fernet) -> str:
    return fernet.decrypt(encrypted_url.encode()).decode()


def get_camera_for_user(db: Session, camera_id: UUID, user: User) -> Camera:
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.tenant_id == user.tenant_id
    ).first()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )

    return camera


def open_camera_capture(rtsp_url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        cap.release()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera stream unavailable"
        )

    return cap


def capture_frame(cap: cv2.VideoCapture, error_detail: str):
    ret, frame = cap.read()

    if not ret:
        cap.release()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail
        )

    return frame


def encode_frame(frame) -> bytes:
    ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to encode camera frame"
        )

    return buffer.tobytes()


def capture_initial_frame_bytes(cap: cv2.VideoCapture) -> bytes:
    frame = capture_frame(cap, "Failed to capture initial frame")

    try:
        return encode_frame(frame)
    except HTTPException:
        cap.release()
        raise


def generate_frames(cap: cv2.VideoCapture, first_frame: bytes) -> Generator[bytes, None, None]:
    """Generate MJPEG frames from an open RTSP stream."""
    yield (b"--frame\r\n"
           b"Content-Type: image/jpeg\r\n\r\n" + first_frame + b"\r\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_bytes = encode_frame(frame)

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
    finally:
        cap.release()


@router.get("/{camera_id}/snapshot")
async def get_snapshot(
    camera_id: UUID,
    current_user: User = Depends(get_current_user_for_media),
    db: Session = Depends(get_db)
):
    """
    Get a single snapshot from the camera.
    Accepts browser-compatible authentication for media requests.
    """
    camera = get_camera_for_user(db, camera_id, current_user)

    fernet = get_fernet()
    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, fernet)

    cap = open_camera_capture(rtsp_url)

    frame = capture_frame(cap, "Failed to capture frame")
    cap.release()

    return Response(
        content=encode_frame(frame),
        media_type="image/jpeg"
    )


@router.get("/{camera_id}/stream")
async def stream_camera(
    camera_id: UUID,
    current_user: User = Depends(get_current_user_for_media),
    db: Session = Depends(get_db)
):
    """
    Stream camera video as MJPEG.
    
    Returns a continuous JPEG stream that can be displayed in an img tag.
    """
    camera = get_camera_for_user(db, camera_id, current_user)

    fernet = get_fernet()
    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, fernet)

    cap = open_camera_capture(rtsp_url)
    first_frame = capture_initial_frame_bytes(cap)

    response = StreamingResponse(
        generate_frames(cap, first_frame),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"

    return response
