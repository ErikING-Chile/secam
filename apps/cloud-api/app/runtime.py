"""Backend runtime alignment checks."""

from importlib.util import find_spec
from pathlib import Path
import sys
from typing import Any


SUPPORTED_PYTHON = (3, 11)
REQUIRED_MODULES = {
    "fastapi": "fastapi",
    "redis": "redis",
    "sqlalchemy": "sqlalchemy",
    "psycopg": "psycopg[binary]",
    "cv2": "opencv-python-headless",
    "aiortc": "aiortc",
    "av": "av",
}


class RuntimeAlignmentError(RuntimeError):
    """Raised when the backend runtime does not match the supported contract."""


def supported_python_label() -> str:
    """Return the supported Python runtime label."""
    return f"{SUPPORTED_PYTHON[0]}.{SUPPORTED_PYTHON[1]}"


def backend_root() -> Path:
    """Return the backend root directory."""
    return Path(__file__).resolve().parents[1]


def validate_python_version(version_info: Any = None) -> None:
    """Reject unsupported Python runtimes with actionable guidance."""
    current_version = version_info or sys.version_info
    current = (current_version.major, current_version.minor)
    if current == SUPPORTED_PYTHON:
        return

    raise RuntimeAlignmentError(
        "Unsupported Python runtime "
        f"{current_version.major}.{current_version.minor}. "
        f"apps/cloud-api supports Python {supported_python_label()}.x to match the Docker baseline. "
        "Create or activate a Python 3.11 virtualenv and reinstall dependencies with "
        f"`python -m pip install -r {backend_root() / 'requirements.txt'}`."
    )


def find_missing_modules(required_modules: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Return required imports that are missing from the environment."""
    modules = required_modules or REQUIRED_MODULES
    return [
        (module_name, package_name)
        for module_name, package_name in modules.items()
        if find_spec(module_name) is None
    ]


def validate_required_modules(required_modules: dict[str, str] | None = None) -> None:
    """Reject incomplete backend environments with actionable guidance."""
    missing_modules = find_missing_modules(required_modules)
    if not missing_modules:
        return

    missing_packages = ", ".join(package_name for _, package_name in missing_modules)
    missing_imports = ", ".join(module_name for module_name, _ in missing_modules)
    raise RuntimeAlignmentError(
        "Backend runtime is missing required imports: "
        f"{missing_imports}. Install the checked-in backend dependencies with "
        f"`python -m pip install -r {backend_root() / 'requirements.txt'}` "
        f"so packages like {missing_packages} are available."
    )


def validate_runtime() -> None:
    """Validate backend runtime compatibility."""
    validate_python_version()
    validate_required_modules()
