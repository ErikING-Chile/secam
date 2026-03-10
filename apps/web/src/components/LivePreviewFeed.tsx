"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface LivePreviewFeedProps {
  cameraId: string;
  cameraName: string;
}

export default function LivePreviewFeed({ cameraId, cameraName }: LivePreviewFeedProps) {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    setToken(storedToken);
    setIsLoading(Boolean(storedToken));
    setError(storedToken ? null : "Sesion expirada. Inicia sesion nuevamente.");
  }, [cameraId]);

  const streamUrl = useMemo(() => {
    if (!token) {
      return null;
    }

    const params = new URLSearchParams({ token });
    return `${API_URL}/cameras/${cameraId}/stream?${params.toString()}`;
  }, [cameraId, token]);

  return (
    <div className="relative h-full w-full bg-black">
      {streamUrl && (
        <img
          key={streamUrl}
          src={streamUrl}
          alt={`Vista en vivo de ${cameraName}`}
          className="h-full w-full object-contain"
          onLoad={() => {
            setIsLoading(false);
            setError(null);
          }}
          onError={() => {
            setIsLoading(false);
            setError("No se pudo abrir el video en vivo. Verifica la conexion RTSP y el acceso de red.");
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

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/70 p-6 text-center">
          <div>
            <p className="text-sm font-medium text-white">{error}</p>
            <p className="mt-2 text-xs text-gray-300">Endpoint: `/api/v1/cameras/{cameraId}/stream`</p>
          </div>
        </div>
      )}
    </div>
  );
}
