"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const AUTH_EXPIRED_MESSAGE = "Sesion expirada. Inicia sesion nuevamente.";
const STREAM_UNAVAILABLE_MESSAGE = "No se pudo abrir el video en vivo. Verifica la conexion RTSP y el acceso de red.";
const GENERIC_FAILURE_MESSAGE = "No se pudo preparar la vista en vivo. Recarga la pagina e intenta nuevamente.";
const DIAGNOSTIC_LOADING_MESSAGE = "No se pudo abrir el video en vivo. Recolectando diagnostico RTSP...";

type LivePreviewStatus =
  | "bootstrapping"
  | "connecting"
  | "diagnosing"
  | "ready"
  | "auth-expired"
  | "stream-unavailable"
  | "error";

interface DiagnosticHint {
  code: string;
  title: string;
  detail: string;
}

interface DiagnosticPayload {
  status: "ok" | "failed";
  category: string;
  summary: string;
  target: {
    host: string;
    port: number;
  };
  runtime: {
    execution_mode: "host" | "docker";
    hostname: string;
  };
  hints: DiagnosticHint[];
}

interface LivePreviewState {
  status: LivePreviewStatus;
  token: string | null;
  message: string | null;
  diagnostic: DiagnosticPayload | null;
}

interface LivePreviewFeedProps {
  cameraId: string;
  cameraName: string;
}

export default function LivePreviewFeed({ cameraId, cameraName }: LivePreviewFeedProps) {
  const [state, setState] = useState<LivePreviewState>({
    status: "bootstrapping",
    token: null,
    message: null,
    diagnostic: null,
  });
  const diagnosticsRequestedRef = useRef<string | null>(null);

  useEffect(() => {
    diagnosticsRequestedRef.current = null;
    setState({ status: "bootstrapping", token: null, message: null, diagnostic: null });

    try {
      const storedToken = window.localStorage.getItem("access_token");

      if (!storedToken) {
        setState({
          status: "auth-expired",
          token: null,
          message: AUTH_EXPIRED_MESSAGE,
          diagnostic: null,
        });
        return;
      }

      setState({ status: "connecting", token: storedToken, message: null, diagnostic: null });
    } catch {
      setState({
        status: "error",
        token: null,
        message: GENERIC_FAILURE_MESSAGE,
        diagnostic: null,
      });
    }
  }, [cameraId]);

  const streamUrl = useMemo(() => {
    if (!state.token) {
      return null;
    }

    const params = new URLSearchParams({ token: state.token });
    return `${API_URL}/cameras/${cameraId}/stream?${params.toString()}`;
  }, [cameraId, state.token]);

  const isLoading =
    state.status === "bootstrapping" ||
    state.status === "connecting" ||
    state.status === "diagnosing";
  const showImage = Boolean(streamUrl) && state.status !== "auth-expired" && state.status !== "error";

  const loadDiagnostics = async () => {
    if (!state.token || diagnosticsRequestedRef.current === streamUrl) {
      return;
    }

    diagnosticsRequestedRef.current = streamUrl;
    setState((current) => ({
      ...current,
      status: "diagnosing",
      message: DIAGNOSTIC_LOADING_MESSAGE,
      diagnostic: null,
    }));

    try {
      const response = await fetch(`${API_URL}/cameras/${cameraId}/test`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${state.token}`,
        },
      });

      if (response.status === 401) {
        setState((current) => ({
          ...current,
          status: "auth-expired",
          message: AUTH_EXPIRED_MESSAGE,
          diagnostic: null,
        }));
        return;
      }

      if (!response.ok) {
        throw new Error("diagnostic-request-failed");
      }

      const diagnostic = (await response.json()) as DiagnosticPayload;

      setState((current) => ({
        ...current,
        status: "stream-unavailable",
        message: diagnostic.summary,
        diagnostic,
      }));
    } catch {
      setState((current) => ({
        ...current,
        status: "stream-unavailable",
        message: STREAM_UNAVAILABLE_MESSAGE,
        diagnostic: null,
      }));
    }
  };

  return (
    <div className="relative h-full w-full bg-black">
      {showImage && streamUrl && (
        /* eslint-disable-next-line @next/next/no-img-element -- MJPEG streams need a native img element to render multipart/x-mixed-replace frames. */
        <img
          key={streamUrl}
          src={streamUrl}
          alt={`Vista en vivo de ${cameraName}`}
          className={`h-full w-full object-contain transition-opacity duration-200 ${
            state.status === "ready" ? "opacity-100" : "opacity-0"
          }`}
          onLoad={() => {
            setState((current) => ({
              ...current,
              status: "ready",
              message: null,
              diagnostic: null,
            }));
          }}
          onError={() => {
            void loadDiagnostics();
          }}
        />
      )}

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="text-center text-white">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-b-2 border-white"></div>
            <p className="text-sm">Conectando video en vivo...</p>
          </div>
        </div>
      )}

      {state.message && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/70 p-6 text-center">
          <div className="max-w-md space-y-3">
            <p className="text-sm font-medium text-white">{state.message}</p>
            <p className="mt-2 text-xs text-gray-300">Endpoint: `/api/v1/cameras/{cameraId}/stream`</p>
            {state.diagnostic && (
              <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-left text-xs text-gray-200">
                <p>
                  Backend: {state.diagnostic.runtime.execution_mode} ({state.diagnostic.runtime.hostname})
                </p>
                <p>
                  Target: {state.diagnostic.target.host}:{state.diagnostic.target.port}
                </p>
                <p>Categoria: {state.diagnostic.category}</p>
                {state.diagnostic.hints.map((hint) => (
                  <p key={hint.code} className="mt-2">
                    <span className="font-semibold text-white">{hint.title}:</span> {hint.detail}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
