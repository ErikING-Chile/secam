from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status

from app.routers import streaming


def test_open_camera_capture_returns_503_when_rtsp_cannot_open():
    cap = Mock()
    cap.isOpened.return_value = False

    with patch.object(streaming.cv2, "VideoCapture", return_value=cap):
        with pytest.raises(HTTPException) as exc_info:
            streaming.open_camera_capture("rtsp://camera")

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.detail == "Camera stream unavailable"
    cap.release.assert_called_once()


def test_capture_initial_frame_bytes_returns_502_when_first_frame_fails():
    cap = Mock()
    cap.read.return_value = (False, None)

    with pytest.raises(HTTPException) as exc_info:
        streaming.capture_initial_frame_bytes(cap)

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc_info.value.detail == "Failed to capture initial frame"
    cap.release.assert_called_once()


def test_capture_initial_frame_bytes_releases_capture_on_encode_failure():
    cap = Mock()
    cap.read.return_value = (True, object())

    with patch.object(streaming.cv2, "imencode", return_value=(False, None)):
        with pytest.raises(HTTPException) as exc_info:
            streaming.capture_initial_frame_bytes(cap)

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc_info.value.detail == "Failed to encode camera frame"
    cap.release.assert_called_once()
