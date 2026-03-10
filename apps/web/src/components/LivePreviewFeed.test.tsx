import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import LivePreviewFeed from "./LivePreviewFeed";

const AUTH_EXPIRED_MESSAGE = "Sesion expirada. Inicia sesion nuevamente.";
const STREAM_UNAVAILABLE_MESSAGE = "No se pudo abrir el video en vivo. Verifica la conexion RTSP y el acceso de red.";

describe("LivePreviewFeed", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
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

  it("surfaces the stream-unavailable state when the image fails to load", async () => {
    window.localStorage.setItem("access_token", "camera-token");

    render(<LivePreviewFeed cameraId="camera-123" cameraName="Entrada" />);

    const image = await screen.findByAltText("Vista en vivo de Entrada");
    fireEvent.error(image);

    expect(await screen.findByText(STREAM_UNAVAILABLE_MESSAGE)).toBeInTheDocument();
    expect(screen.getByText("Endpoint: `/api/v1/cameras/camera-123/stream`")).toBeInTheDocument();
  });
});
