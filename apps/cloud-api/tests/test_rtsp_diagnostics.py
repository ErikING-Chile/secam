from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock, patch

import pytest

from app import rtsp_diagnostics
from app.routers import cameras
from app.schemas import (
    RTSPDiagnosticCategory,
    RTSPDiagnosticResponse,
    RTSPDiagnosticRuntimeContext,
    RTSPDiagnosticRuntimeMode,
    RTSPDiagnosticStatus,
    RTSPDiagnosticTarget,
)


def runtime_context(containerized: bool = False) -> RTSPDiagnosticRuntimeContext:
    return RTSPDiagnosticRuntimeContext(
        execution_mode=(RTSPDiagnosticRuntimeMode.DOCKER if containerized else RTSPDiagnosticRuntimeMode.HOST),
        containerized=containerized,
        hostname="secam-test",
    )


def test_diagnose_rtsp_url_reports_success_when_stream_opens_and_returns_frame():
    cap = Mock()
    cap.isOpened.return_value = True
    cap.read.return_value = (True, object())

    with patch.object(rtsp_diagnostics, "detect_runtime_context", return_value=runtime_context()):
        with patch.object(rtsp_diagnostics.socket, "getaddrinfo", return_value=[object()]):
            with patch.object(rtsp_diagnostics.socket, "create_connection") as create_connection:
                with patch.object(rtsp_diagnostics.cv2, "VideoCapture", return_value=cap):
                    diagnostic = rtsp_diagnostics.diagnose_rtsp_url("rtsp://user:secret@camera.local:8554/live")

    assert diagnostic.status == RTSPDiagnosticStatus.OK
    assert diagnostic.category == RTSPDiagnosticCategory.SUCCESS
    assert diagnostic.target.host == "camera.local"
    assert diagnostic.target.port == 8554
    assert diagnostic.target.has_credentials is True
    assert "secret" not in diagnostic.model_dump_json()
    create_connection.assert_called_once_with(("camera.local", 8554), 3.0)
    cap.release.assert_called_once()


def test_diagnose_rtsp_url_reports_dns_failure_before_opening_capture():
    with patch.object(rtsp_diagnostics, "detect_runtime_context", return_value=runtime_context()):
        with patch.object(rtsp_diagnostics.socket, "getaddrinfo", side_effect=rtsp_diagnostics.socket.gaierror):
            with patch.object(rtsp_diagnostics.cv2, "VideoCapture") as video_capture:
                diagnostic = rtsp_diagnostics.diagnose_rtsp_url("rtsp://camera.local/live")

    assert diagnostic.category == RTSPDiagnosticCategory.DNS_FAILURE
    assert diagnostic.status == RTSPDiagnosticStatus.FAILED
    video_capture.assert_not_called()


def test_diagnose_rtsp_url_flags_loopback_when_running_in_docker():
    with patch.object(rtsp_diagnostics, "detect_runtime_context", return_value=runtime_context(containerized=True)):
        diagnostic = rtsp_diagnostics.diagnose_rtsp_url("rtsp://127.0.0.1:554/live")

    assert diagnostic.category == RTSPDiagnosticCategory.LOOPBACK_IN_DOCKER
    assert diagnostic.runtime.containerized is True
    assert any(hint.code == "avoid-loopback" for hint in diagnostic.hints)


def test_diagnose_rtsp_url_reports_connection_refused():
    with patch.object(rtsp_diagnostics, "detect_runtime_context", return_value=runtime_context()):
        with patch.object(rtsp_diagnostics.socket, "getaddrinfo", return_value=[object()]):
            with patch.object(
                rtsp_diagnostics.socket,
                "create_connection",
                side_effect=ConnectionRefusedError,
            ):
                diagnostic = rtsp_diagnostics.diagnose_rtsp_url("rtsp://camera.local/live")

    assert diagnostic.category == RTSPDiagnosticCategory.CONNECTION_REFUSED
    assert "camera.local:554" in diagnostic.summary


def test_diagnose_rtsp_url_reports_first_frame_timeout():
    cap = Mock()
    cap.isOpened.return_value = True
    cap.read.return_value = (False, None)

    with patch.object(rtsp_diagnostics, "detect_runtime_context", return_value=runtime_context()):
        with patch.object(rtsp_diagnostics.socket, "getaddrinfo", return_value=[object()]):
            with patch.object(rtsp_diagnostics.socket, "create_connection"):
                with patch.object(rtsp_diagnostics.cv2, "VideoCapture", return_value=cap):
                    diagnostic = rtsp_diagnostics.diagnose_rtsp_url("rtsp://camera.local/live")

    assert diagnostic.category == RTSPDiagnosticCategory.FIRST_FRAME_TIMEOUT
    assert diagnostic.status == RTSPDiagnosticStatus.FAILED
    cap.release.assert_called_once()


@pytest.mark.asyncio
async def test_camera_connection_returns_structured_diagnostics_without_rtsp_url():
    camera_id = uuid4()
    tenant_id = uuid4()
    diagnostic = RTSPDiagnosticResponse(
        status=RTSPDiagnosticStatus.FAILED,
        category=RTSPDiagnosticCategory.CONNECTION_REFUSED,
        summary="El host RTSP respondio, pero rechazo la conexion en camera.local:554.",
        target=RTSPDiagnosticTarget(
            scheme="rtsp",
            host="camera.local",
            port=554,
            has_credentials=True,
            path_present=True,
            query_present=False,
        ),
        runtime=runtime_context(),
        hints=[],
    )

    camera = SimpleNamespace(
        id=camera_id,
        name="Entrada",
        tenant_id=tenant_id,
        rtsp_url_encrypted="encrypted-value",
    )
    query = Mock()
    query.filter.return_value.first.return_value = camera
    db = Mock()
    db.query.return_value = query
    current_user = SimpleNamespace(tenant_id=tenant_id)

    with patch.object(cameras, "get_fernet", return_value=object()):
        with patch.object(cameras, "decrypt_rtsp_url", return_value="rtsp://user:secret@camera.local/live"):
            with patch.object(cameras, "diagnose_rtsp_url", return_value=diagnostic):
                result = await cameras.test_camera_connection(camera_id, current_user=current_user, db=db)

    payload = result.model_dump(mode="json")

    assert payload["camera_id"] == str(camera_id)
    assert payload["camera_name"] == "Entrada"
    assert payload["category"] == RTSPDiagnosticCategory.CONNECTION_REFUSED.value
    assert "rtsp_url" not in payload
    assert "secret" not in str(payload)
