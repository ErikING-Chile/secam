# RTSP live view follow-ups

This note keeps deferred cleanup out of the current MJPEG release while making the pending WebRTC work explicit.

## Deferred items

- `apps/cloud-api/app/routers/webrtc.py`: collapse the split `/webrtc` and `/webrtc/answer` flow into one consistent signaling contract before any dashboard transport switch.
- `apps/cloud-api/app/routers/webrtc.py`: tighten peer lifecycle cleanup so `pcs` entries and RTSP capture resources are released on failure and disconnect.
- `apps/cloud-api/app/routers/webrtc.py` plus `apps/web/src/components/WebRTCFeed.tsx`: only revisit frontend wiring after the backend signaling contract is stable and intentionally replaces the current MJPEG modal path.
