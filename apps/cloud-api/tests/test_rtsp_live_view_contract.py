from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_PAGE = REPO_ROOT / "apps" / "web" / "src" / "app" / "dashboard" / "page.tsx"
API_MAIN = REPO_ROOT / "apps" / "cloud-api" / "app" / "main.py"
FOLLOW_UPS = REPO_ROOT / "docs" / "rtsp-live-view-followups.md"


def test_dashboard_live_view_modal_stays_on_live_preview_feed():
    source = DASHBOARD_PAGE.read_text(encoding="utf-8")

    assert 'import LivePreviewFeed from "@/components/LivePreviewFeed";' in source
    assert 'import WebRTCFeed from "@/components/WebRTCFeed";' not in source
    assert "<LivePreviewFeed" in source


def test_api_main_keeps_streaming_router_under_api_v1():
    source = API_MAIN.read_text(encoding="utf-8")

    assert 'app.include_router(streaming.router, prefix="/api/v1")' in source


def test_webrtc_cleanup_is_captured_as_follow_up_work():
    source = FOLLOW_UPS.read_text(encoding="utf-8")

    assert "apps/cloud-api/app/routers/webrtc.py" in source
    assert "deferred" in source.lower()
    assert "WebRTCFeed" in source
