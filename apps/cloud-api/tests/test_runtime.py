from types import SimpleNamespace

import pytest

from app import runtime
from app.db import validate_database_url


def test_validate_python_version_accepts_supported_minor():
    runtime.validate_python_version(SimpleNamespace(major=3, minor=11))


def test_validate_python_version_rejects_unsupported_minor():
    with pytest.raises(runtime.RuntimeAlignmentError) as exc_info:
        runtime.validate_python_version(SimpleNamespace(major=3, minor=13))

    assert "Python 3.11.x" in str(exc_info.value)
    assert "virtualenv" in str(exc_info.value)


def test_validate_required_modules_reports_missing_packages(monkeypatch: pytest.MonkeyPatch):
    def fake_find_spec(module_name: str):
        return None if module_name in {"psycopg", "aiortc"} else object()

    monkeypatch.setattr(runtime, "find_spec", fake_find_spec)

    with pytest.raises(runtime.RuntimeAlignmentError) as exc_info:
        runtime.validate_required_modules()

    message = str(exc_info.value)
    assert "psycopg, aiortc" in message
    assert "psycopg[binary], aiortc" in message
    assert "requirements.txt" in message


def test_validate_runtime_runs_both_checks(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    monkeypatch.setattr(runtime, "validate_python_version", lambda: calls.append("python"))
    monkeypatch.setattr(runtime, "validate_required_modules", lambda: calls.append("modules"))

    runtime.validate_runtime()

    assert calls == ["python", "modules"]


def test_validate_database_url_rejects_legacy_postgresql_scheme():
    with pytest.raises(RuntimeError) as exc_info:
        validate_database_url("postgresql://secam:password@localhost:5432/secam")

    assert "postgresql+psycopg://" in str(exc_info.value)


def test_validate_database_url_accepts_psycopg_scheme():
    database_url = "postgresql+psycopg://secam:password@localhost:5432/secam"

    assert validate_database_url(database_url) == database_url
