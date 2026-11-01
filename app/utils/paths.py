"""Path utilities for safe, cross-platform path handling."""

import os
from pathlib import Path
from typing import Optional


def get_app_data_dir() -> Path:
    """Return the application data directory, creating it if needed.

    Priority:
    1. Environment variable PDF_ORGANIZER_DATA_DIR (if set)
    2. %LOCALAPPDATA%/LocalPDFOrganizer (standard Windows)
    3. %APPDATA%/LocalPDFOrganizer
    4. ~/.pdf_organizer (standard Linux/macOS)
    5. Fallback to project-local data directory or tempdir if access is restricted
    """
    override = os.environ.get("PDF_ORGANIZER_DATA_DIR")
    if override:
        p = Path(override)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except (PermissionError, OSError):
            pass

    candidates: list[Path] = []

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "LocalPDFOrganizer")

    app_data = os.environ.get("APPDATA")
    if app_data:
        candidates.append(Path(app_data) / "LocalPDFOrganizer")

    try:
        candidates.append(Path.home() / ".pdf_organizer")
    except Exception:
        pass

    candidates.append(Path(__file__).resolve().parent.parent.parent / ".data")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_test"
            test_file.touch()
            test_file.unlink(missing_ok=True)
            return candidate
        except (PermissionError, OSError):
            continue

    import tempfile
    fallback = Path(tempfile.gettempdir()) / "LocalPDFOrganizer"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_db_path() -> Path:
    """Return the path to the SQLite database file."""
    return get_app_data_dir() / "organizer.db"


def get_log_dir() -> Path:
    """Return the path to the log directory, creating it if needed."""
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_config_path() -> Path:
    """Return the path to the configuration file."""
    return get_app_data_dir() / "config.json"


def safe_relative_path(base: Path, target: Path) -> Optional[Path]:
    """Return the relative path of target from base, or None if not relative."""
    try:
        return target.resolve().relative_to(base.resolve())
    except ValueError:
        return None


def is_protected_directory(path: Path) -> bool:
    """Check if a path is a protected system directory that should not be
    recursively reorganized.

    This is a safety check, not a complete blocklist.
    """
    home = Path.home()
    protected = {
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "OneDrive",
        home / "AppData",
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
    }
    resolved = path.resolve()
    return any(resolved == p.resolve() for p in protected)


def normalize_path(path: Path) -> Path:
    """Normalize a path for consistent comparison."""
    return path.resolve()
