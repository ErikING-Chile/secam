from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status

from app.routers import streaming
from app.schemas import RTSPDiagnosticCategory


def test_open_camera_capture_returns_503_when_rtsp_cannot_open():
    cap = Mock()
    cap.isOpened.return_value = False

    with patch.object(streaming.cv2, "VideoCapture", return_value=cap):
        with patch.object(streaming, "build_stream_error", return_value=HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "failed",
                "category": RTSPDiagnosticCategory.CONNECTION_REFUSED.value,
                "summary": "El host RTSP respondio, pero rechazo la conexion.",
            },
        )):
            with pytest.raises(HTTPException) as exc_info:
                streaming.open_camera_capture("rtsp://camera")

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.detail["category"] == RTSPDiagnosticCategory.CONNECTION_REFUSED.value
    cap.release.assert_called_once()


def test_capture_initial_frame_bytes_returns_502_when_first_frame_fails():
    cap = Mock()
    cap.read.return_value = (False, None)

    with patch.object(streaming, "build_stream_error", return_value=HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "status": "failed",
            "category": RTSPDiagnosticCategory.FIRST_FRAME_TIMEOUT.value,
            "summary": "El backend pudo abrir la sesion RTSP, pero no obtuvo un primer frame util dentro del timeout.",
        },
    )):
        with pytest.raises(HTTPException) as exc_info:
            streaming.capture_initial_frame_bytes(cap, "rtsp://camera")

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc_info.value.detail["category"] == RTSPDiagnosticCategory.FIRST_FRAME_TIMEOUT.value
    cap.release.assert_called_once()


def test_capture_initial_frame_bytes_releases_capture_on_encode_failure():
    cap = Mock()
    cap.read.return_value = (True, object())

    with patch.object(streaming.cv2, "imencode", return_value=(False, None)):
        with pytest.raises(HTTPException) as exc_info:
            streaming.capture_initial_frame_bytes(cap, "rtsp://camera")

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc_info.value.detail == "Failed to encode camera frame"
    cap.release.assert_called_once()
