"""Shared RTSP diagnostics helpers."""
from __future__ import annotations

import os
import socket
from contextlib import closing
from urllib.parse import urlsplit

import cv2
from fastapi import HTTPException

from .config import settings
from .schemas import (
    RTSPDiagnosticCategory,
    RTSPDiagnosticHint,
    RTSPDiagnosticResponse,
    RTSPDiagnosticRuntimeContext,
    RTSPDiagnosticRuntimeMode,
    RTSPDiagnosticStatus,
    RTSPDiagnosticTarget,
)

DEFAULT_RTSP_PORT = 554
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def detect_runtime_context() -> RTSPDiagnosticRuntimeContext:
    """Detect whether the backend is running on the host or in Docker."""
    containerized = os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "1"

    return RTSPDiagnosticRuntimeContext(
        execution_mode=(
            RTSPDiagnosticRuntimeMode.DOCKER if containerized else RTSPDiagnosticRuntimeMode.HOST
        ),
        containerized=containerized,
        hostname=socket.gethostname(),
    )


def sanitize_rtsp_target(rtsp_url: str) -> RTSPDiagnosticTarget:
    """Return non-secret RTSP target facts."""
    parsed = urlsplit(rtsp_url)
    port = parsed.port or DEFAULT_RTSP_PORT

    return RTSPDiagnosticTarget(
        scheme=parsed.scheme or "rtsp",
        host=(parsed.hostname or "").strip(),
        port=port,
        has_credentials=bool(parsed.username or parsed.password),
        path_present=bool(parsed.path and parsed.path != "/"),
        query_present=bool(parsed.query),
    )


def build_diagnostic_response(
    *,
    category: RTSPDiagnosticCategory,
    target: RTSPDiagnosticTarget,
    runtime: RTSPDiagnosticRuntimeContext | None = None,
) -> RTSPDiagnosticResponse:
    """Build a normalized diagnostic payload."""
    runtime = runtime or detect_runtime_context()
    hints, summary = diagnostic_content_for(category, target, runtime)

    return RTSPDiagnosticResponse(
        status=(
            RTSPDiagnosticStatus.OK
            if category == RTSPDiagnosticCategory.SUCCESS
            else RTSPDiagnosticStatus.FAILED
        ),
        category=category,
        summary=summary,
        target=target,
        runtime=runtime,
        hints=hints,
    )


def diagnose_rtsp_preflight(rtsp_url: str) -> RTSPDiagnosticResponse:
    """Diagnose issues that can be determined before or without frame capture."""
    runtime = detect_runtime_context()
    target = sanitize_rtsp_target(rtsp_url)

    if not target.host:
        return build_diagnostic_response(
            category=RTSPDiagnosticCategory.INVALID_URL,
            target=target,
            runtime=runtime,
        )

    if runtime.containerized and target.host in LOOPBACK_HOSTS:
        return build_diagnostic_response(
            category=RTSPDiagnosticCategory.LOOPBACK_IN_DOCKER,
            target=target,
            runtime=runtime,
        )

    try:
        socket.getaddrinfo(target.host, target.port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return build_diagnostic_response(
            category=RTSPDiagnosticCategory.DNS_FAILURE,
            target=target,
            runtime=runtime,
        )

    try:
        with closing(socket.create_connection((target.host, target.port), settings.RTSP_DIAGNOSTIC_SOCKET_TIMEOUT_SECONDS)):
            return build_diagnostic_response(
                category=RTSPDiagnosticCategory.SUCCESS,
                target=target,
                runtime=runtime,
            )
    except ConnectionRefusedError:
        category = RTSPDiagnosticCategory.CONNECTION_REFUSED
    except TimeoutError:
        category = RTSPDiagnosticCategory.CONNECTION_TIMEOUT
    except OSError:
        category = RTSPDiagnosticCategory.CONNECTION_TIMEOUT

    return build_diagnostic_response(category=category, target=target, runtime=runtime)


def diagnose_rtsp_url(rtsp_url: str) -> RTSPDiagnosticResponse:
    """Perform a short RTSP probe and normalize the result."""
    preflight = diagnose_rtsp_preflight(rtsp_url)

    if preflight.category != RTSPDiagnosticCategory.SUCCESS:
        return preflight

    cap = cv2.VideoCapture(rtsp_url)
    _apply_capture_timeouts(cap)

    if not cap.isOpened():
        cap.release()
        return build_diagnostic_response(
            category=RTSPDiagnosticCategory.STREAM_OPEN_FAILED,
            target=preflight.target,
            runtime=preflight.runtime,
        )

    try:
        ret, _ = cap.read()
    finally:
        cap.release()

    if not ret:
        return build_diagnostic_response(
            category=RTSPDiagnosticCategory.FIRST_FRAME_TIMEOUT,
            target=preflight.target,
            runtime=preflight.runtime,
        )

    return preflight


def build_stream_error(rtsp_url: str, status_code: int, category: RTSPDiagnosticCategory | None = None) -> HTTPException:
    """Convert diagnostics into an HTTPException for streaming routes."""
    diagnostic = (
        build_diagnostic_response(category=category, target=sanitize_rtsp_target(rtsp_url))
        if category is not None
        else diagnose_rtsp_preflight(rtsp_url)
    )

    return HTTPException(
        status_code=status_code,
        detail={
            "status": diagnostic.status.value,
            "category": diagnostic.category.value,
            "summary": diagnostic.summary,
        },
    )


def _apply_capture_timeouts(cap: cv2.VideoCapture) -> None:
    """Apply backend-configured capture timeouts when supported by OpenCV."""
    for prop_name, value in (
        ("CAP_PROP_OPEN_TIMEOUT_MSEC", settings.RTSP_DIAGNOSTIC_OPEN_TIMEOUT_MS),
        ("CAP_PROP_READ_TIMEOUT_MSEC", settings.RTSP_DIAGNOSTIC_READ_TIMEOUT_MS),
    ):
        prop = getattr(cv2, prop_name, None)
        if prop is not None:
            cap.set(prop, value)


def diagnostic_content_for(
    category: RTSPDiagnosticCategory,
    target: RTSPDiagnosticTarget,
    runtime: RTSPDiagnosticRuntimeContext,
) -> tuple[list[RTSPDiagnosticHint], str]:
    """Return operator guidance for a diagnostic category."""
    runtime_label = "Docker" if runtime.containerized else "host"

    if category == RTSPDiagnosticCategory.SUCCESS:
        return (
            [
                RTSPDiagnosticHint(
                    code="probe-ok",
                    title="Conectividad confirmada",
                    detail=f"El backend en {runtime_label} resolvio {target.host}:{target.port} y obtuvo el primer frame.",
                )
            ],
            "El backend pudo abrir el stream RTSP y obtener un frame inicial.",
        )

    if category == RTSPDiagnosticCategory.INVALID_URL:
        return (
            [
                RTSPDiagnosticHint(
                    code="check-rtsp-url",
                    title="Revisa la URL RTSP",
                    detail="La URL guardada no tiene un host RTSP valido. Corrige la configuracion de la camara y vuelve a probar.",
                )
            ],
            "La configuracion RTSP guardada no contiene un host valido.",
        )

    if category == RTSPDiagnosticCategory.LOOPBACK_IN_DOCKER:
        return (
            [
                RTSPDiagnosticHint(
                    code="avoid-loopback",
                    title="No uses localhost dentro de Docker",
                    detail="Si el backend corre en Docker, localhost y 127.0.0.1 apuntan al contenedor, no a tu PC ni a la camara.",
                ),
                RTSPDiagnosticHint(
                    code="use-routable-host",
                    title="Usa una IP alcanzable",
                    detail="Configura la URL con la IP LAN o DNS real de la camara. Solo usa host.docker.internal si el stream realmente se expone desde tu host.",
                ),
            ],
            "El backend corre en Docker y la URL RTSP apunta a loopback, por lo que nunca llegara a la camara real.",
        )

    if category == RTSPDiagnosticCategory.DNS_FAILURE:
        return (
            [
                RTSPDiagnosticHint(
                    code="check-hostname",
                    title="Valida el host RTSP",
                    detail=f"El backend en {runtime_label} no pudo resolver {target.host}. Revisa DNS, typo o usa una IP fija.",
                )
            ],
            f"El backend no pudo resolver el host RTSP {target.host}.",
        )

    if category == RTSPDiagnosticCategory.CONNECTION_REFUSED:
        return (
            [
                RTSPDiagnosticHint(
                    code="check-port",
                    title="Revisa puerto y servicio RTSP",
                    detail=f"{target.host}:{target.port} rechazo la conexion. Verifica que la camara tenga RTSP habilitado y escuche en ese puerto.",
                )
            ],
            f"El host RTSP respondio, pero rechazo la conexion en {target.host}:{target.port}.",
        )

    if category == RTSPDiagnosticCategory.CONNECTION_TIMEOUT:
        return (
            [
                RTSPDiagnosticHint(
                    code="check-network-path",
                    title="Verifica el acceso de red",
                    detail=f"El backend en {runtime_label} no pudo abrir una conexion TCP a {target.host}:{target.port} dentro del timeout configurado.",
                )
            ],
            f"El backend no pudo conectarse a {target.host}:{target.port} dentro del tiempo esperado.",
        )

    if category == RTSPDiagnosticCategory.STREAM_OPEN_FAILED:
        return (
            [
                RTSPDiagnosticHint(
                    code="check-credentials",
                    title="Revisa credenciales y protocolo",
                    detail="El puerto RTSP responde, pero OpenCV no pudo abrir el stream. Verifica usuario, clave, path RTSP y compatibilidad del transporte del equipo.",
                )
            ],
            "La red RTSP responde, pero el backend no pudo abrir el stream en OpenCV.",
        )

    return (
        [
            RTSPDiagnosticHint(
                code="check-first-frame",
                title="El stream abre, pero no entrega video",
                detail="El backend pudo abrir la sesion RTSP, pero no llego un frame util a tiempo. Revisa codec, latencia o carga del equipo.",
            )
        ],
        "El backend pudo abrir la sesion RTSP, pero no obtuvo un primer frame util dentro del timeout.",
    )
