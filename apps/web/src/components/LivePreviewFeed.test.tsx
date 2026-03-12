import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import LivePreviewFeed from "./LivePreviewFeed";

const AUTH_EXPIRED_MESSAGE = "Sesion expirada. Inicia sesion nuevamente.";
const STREAM_UNAVAILABLE_MESSAGE = "No se pudo abrir el video en vivo. Verifica la conexion RTSP y el acceso de red.";

const fetchMock = vi.fn();

describe("LivePreviewFeed", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("builds the MJPEG stream URL when a token is present", async () => {
    window.localStorage.setItem("access_token", "token with spaces");

    render(<LivePreviewFeed cameraId="camera-123" cameraName="Entrada" />);

    const image = await screen.findByAltText("Vista en vivo de Entrada");

    expect(image).toHaveAttribute(
      "src",
      "http://localhost:8000/api/v1/cameras/camera-123/stream?token=token+with+spaces"
    );
    expect(screen.queryByText(AUTH_EXPIRED_MESSAGE)).not.toBeInTheDocument();
  });

  it("shows the auth-expired state when no access token is available", async () => {
    render(<LivePreviewFeed cameraId="camera-123" cameraName="Entrada" />);

    expect(await screen.findByText(AUTH_EXPIRED_MESSAGE)).toBeInTheDocument();
    expect(screen.queryByAltText("Vista en vivo de Entrada")).not.toBeInTheDocument();
  });

  it("loads RTSP diagnostics when the image fails to load", async () => {
    window.localStorage.setItem("access_token", "camera-token");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "failed",
        category: "loopback_in_docker",
        summary: "El backend corre en Docker y la URL RTSP apunta a loopback, por lo que nunca llegara a la camara real.",
        target: {
          host: "127.0.0.1",
          port: 554,
        },
        runtime: {
          execution_mode: "docker",
          hostname: "secam-api-1",
        },
        hints: [
          {
            code: "avoid-loopback",
            title: "No uses localhost dentro de Docker",
            detail: "Si el backend corre en Docker, localhost y 127.0.0.1 apuntan al contenedor, no a tu PC ni a la camara.",
          },
        ],
      }),
    });

    render(<LivePreviewFeed cameraId="camera-123" cameraName="Entrada" />);

    const image = await screen.findByAltText("Vista en vivo de Entrada");
    fireEvent.error(image);

    expect(
      await screen.findByText(
        "El backend corre en Docker y la URL RTSP apunta a loopback, por lo que nunca llegara a la camara real."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Endpoint: `/api/v1/cameras/camera-123/stream`")).toBeInTheDocument();
    expect(screen.getByText("Backend: docker (secam-api-1)")).toBeInTheDocument();
    expect(screen.getByText("Target: 127.0.0.1:554")).toBeInTheDocument();
    expect(screen.getByText(/No uses localhost dentro de Docker/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/cameras/camera-123/test", {
      method: "POST",
      headers: {
        Authorization: "Bearer camera-token",
      },
    });
  });

  it("falls back to the generic message when diagnostics cannot be loaded", async () => {
    window.localStorage.setItem("access_token", "camera-token");
    fetchMock.mockRejectedValue(new Error("network"));

    render(<LivePreviewFeed cameraId="camera-123" cameraName="Entrada" />);

    const image = await screen.findByAltText("Vista en vivo de Entrada");
    fireEvent.error(image);

    expect(await screen.findByText(STREAM_UNAVAILABLE_MESSAGE)).toBeInTheDocument();
  });
});
