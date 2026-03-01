"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface WebRTCFeedProps {
  cameraId: string;
}

export default function WebRTCFeed({ cameraId }: WebRTCFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(true);
  const pcRef = useRef<RTCPeerConnection | null>(null);

  useEffect(() => {
    let mounted = true;

    const connect = async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token || !mounted) return;

        const pc = new RTCPeerConnection({
          iceServers: [
            { urls: "stun:stun.l.google.com:19302" },
            { urls: "stun:stun1.l.google.com:19302" }
          ]
        });

        pcRef.current = pc;

        pc.ontrack = (event) => {
          if (videoRef.current && mounted) {
            videoRef.current.srcObject = event.streams[0];
            setConnecting(false);
          }
        };

        pc.oniceconnectionstatechange = () => {
          if (pc.iceConnectionState === "failed" || pc.iceConnectionState === "disconnected") {
            setError("Conexión perdida. Reconectando...");
            setConnecting(true);
            setTimeout(connect, 2000);
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch(
          `${API_URL}/cameras/${cameraId}/webrtc/answer`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
              sdp: pc.localDescription?.sdp,
              type: pc.localDescription?.type
            })
          }
        );

        if (!response.ok) {
          throw new Error("Failed to get WebRTC answer");
        }

        const answer = await response.json();
        await pc.setRemoteDescription(new RTCSessionDescription(answer));

      } catch (err) {
        if (mounted) {
          console.error("WebRTC error:", err);
          setError("Error al conectar con la cámara");
          setConnecting(false);
        }
      }
    };

    connect();

    return () => {
      mounted = false;
      if (pcRef.current) {
        pcRef.current.close();
      }
    };
  }, [cameraId]);

  return (
    <div className="relative w-full h-full bg-black">
      {connecting && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="text-white text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
            <p>Conectando...</p>
          </div>
        </div>
      )}
      
      {error && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="text-red-400 text-center p-4">
            <p>{error}</p>
          </div>
        </div>
      )}
      
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-contain"
      />
    </div>
  );
}
