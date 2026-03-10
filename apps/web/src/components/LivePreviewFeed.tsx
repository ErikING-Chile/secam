"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const AUTH_EXPIRED_MESSAGE = "Sesion expirada. Inicia sesion nuevamente.";
const STREAM_UNAVAILABLE_MESSAGE = "No se pudo abrir el video en vivo. Verifica la conexion RTSP y el acceso de red.";
const GENERIC_FAILURE_MESSAGE = "No se pudo preparar la vista en vivo. Recarga la pagina e intenta nuevamente.";

type LivePreviewStatus =
  | "bootstrapping"
  | "connecting"
  | "ready"
  | "auth-expired"
  | "stream-unavailable"
  | "error";

interface LivePreviewState {
  status: LivePreviewStatus;
  token: string | null;
  message: string | null;
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
  });

  useEffect(() => {
    setState({ status: "bootstrapping", token: null, message: null });

    try {
      const storedToken = window.localStorage.getItem("access_token");

      if (!storedToken) {
        setState({
          status: "auth-expired",
          token: null,
          message: AUTH_EXPIRED_MESSAGE,
        });
        return;
      }

      setState({ status: "connecting", token: storedToken, message: null });
    } catch {
      setState({
        status: "error",
        token: null,
        message: GENERIC_FAILURE_MESSAGE,
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

  const isLoading = state.status === "bootstrapping" || state.status === "connecting";
  const showImage = Boolean(streamUrl) && state.status !== "auth-expired" && state.status !== "error";

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
            }));
          }}
          onError={() => {
            setState((current) => ({
              ...current,
              status: "stream-unavailable",
              message: STREAM_UNAVAILABLE_MESSAGE,
            }));
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
          <div>
            <p className="text-sm font-medium text-white">{state.message}</p>
            <p className="mt-2 text-xs text-gray-300">Endpoint: `/api/v1/cameras/{cameraId}/stream`</p>
          </div>
        </div>
      )}
    </div>
  );
}
