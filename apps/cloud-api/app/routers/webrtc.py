"""WebRTC streaming for cameras using aiortc."""
import asyncio
import json
import threading
from uuid import UUID
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import cv2
from av import VideoFrame

from ..db import get_db
from ..models import Camera, User
from ..security import get_current_user
from ..config import settings
from cryptography.fernet import Fernet

router = APIRouter(prefix="/cameras", tags=["WebRTC"])

pcs: dict = {}
fernet = None


def get_fernet() -> Fernet:
    global fernet
    global fernet
    if fernet is None:
        if not settings.ENCRYPTION_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Encryption key not configured"
            )
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return fernet


def decrypt_rtsp_url(encrypted_url: str) -> str:
    f = get_fernet()
    return f.decrypt(encrypted_url.encode()).decode()


class CameraVideoTrack(VideoStreamTrack):
    """Video track that reads frames from RTSP stream."""
    
    def __init__(self, rtsp_url: str):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.cap = None
        self._opened = False
    
    def _open(self):
        if not self._opened:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            if not self.cap.isOpened():
                raise Exception(f"Failed to open RTSP stream: {self.rtsp_url}")
            self._opened = True
    
    async def recv(self):
        self._open()
        
        if self.cap is None or not self.cap.isOpened():
            await asyncio.sleep(0.1)
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            self.cap.release()
            self.cap = None
            self._opened = False
            await asyncio.sleep(0.1)
            return None
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = 0
        video_frame.time_base = "1/30"
        
        return video_frame
    
    def stop(self):
        if self.cap:
            self.cap.release()
            self.cap = None
            self._opened = False


async def consume_video(pc: RTCPeerConnection, rtsp_url: str):
    """Consume video from RTSP and send via WebRTC."""
    try:
        video_track = CameraVideoTrack(rtsp_url)
        pc.addTrack(video_track)
    except Exception as e:
        print(f"Error consuming video: {e}")


@router.post("/{camera_id}/webrtc")
async def webrtc_offer(
    camera_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    WebRTC signaling endpoint.
    Accepts SDP offer and returns SDP answer.
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
    
    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted)
    
    pc = RTCPeerConnection(
        configuration={
            "iceServers": [
                {"urls": "stun:stun.l.google.com:19302"},
                {"urls": "stun:stun1.l.google.com:19302"}
            ]
        }
    )
    
    pc_id = f"{camera_id}"
    pcs[pc_id] = pc
    
    @pc.on("iceconnectionstatechange")
    async def on_ice_connection_state_change():
        print(f"ICE connection state for {pc_id}: {pc.iceConnectionState}")
        if pc.iceConnectionState == "failed" or pc.iceConnectionState == "closed":
            await pc.close()
            if pc_id in pcs:
                del pcs[pc_id]
    
    await consume_video(pc, rtsp_url)
    
    return {"status": "waiting_for_sdp"}


@router.post("/{camera_id}/webrtc/answer")
async def webrtc_answer(
    camera_id: UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Handle SDP offer from client and return SDP answer."""
    
    if "sdp" not in body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing SDP in body"
        )
    
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.tenant_id == current_user.tenant_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted)
    
    pc = RTCPeerConnection()
    
    video_track = CameraVideoTrack(rtsp_url)
    pc.addTrack(video_track)
    
    sdp = body["sdp"]
    
    try:
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
    except Exception as e:
        print(f"Error setting remote description: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid SDP: {str(e)}"
        )
    
    try:
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
    except Exception as e:
        print(f"Error creating answer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create answer: {str(e)}"
        )
    
    response = JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    
    return response
