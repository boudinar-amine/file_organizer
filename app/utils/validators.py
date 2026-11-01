"""Input validation utilities."""

from pathlib import Path
from typing import Any, Optional


def validate_folder_path(path_str: str) -> tuple[bool, str]:
    """Validate that a string represents an existing, accessible directory.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not path_str or not path_str.strip():
        return False, "Path cannot be empty."

    path = Path(path_str.strip())

    if not path.exists():
        return False, f"Path does not exist: {path}"

    if not path.is_dir():
        return False, f"Path is not a directory: {path}"

    try:
        list(path.iterdir())
    except PermissionError:
        return False, f"Permission denied: {path}"
    except OSError as e:
        return False, f"Cannot access path: {e}"

    return True, ""


def validate_max_pages(value: Any) -> tuple[bool, str]:
    """Validate the max-pages-to-analyze setting.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return False, "Max pages must be an integer."

    if n < 1:
        return False, "Max pages must be at least 1."
    if n > 100:
        return False, "Max pages should not exceed 100."
    return True, ""


def validate_confidence(value: Any) -> tuple[bool, str]:
    """Validate a confidence score.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False, "Confidence must be a number."

    if not (0.0 <= f <= 1.0):
        return False, "Confidence must be between 0.0 and 1.0."
    return True, ""


def sanitize_folder_name(name: str) -> str:
    """Sanitize a string for use as a folder name on Windows.

    Removes or replaces characters that are invalid in Windows file paths.
    """
    # Characters forbidden in Windows file/folder names
    forbidden = '<>:"/\\|?*'
    sanitized = "".join(c if c not in forbidden else "_" for c in name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")
    # Collapse multiple underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized or "Uncategorized"


def validate_json_classification(data: Any) -> tuple[bool, str, Optional[dict]]:
    """Validate that a classification result dict has the required fields.

    Returns:
        Tuple of (is_valid, error_message, cleaned_data).
    """
    if not isinstance(data, dict):
        return False, "Classification must be a dictionary.", None

    required_fields = ["document_type", "category", "subcategory", "confidence"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}", None

    # Validate confidence
    ok, msg = validate_confidence(data["confidence"])
    if not ok:
        return False, f"Invalid confidence: {msg}", None

    # Clean and normalize
    cleaned = {
        "document_type": str(data.get("document_type", "Unknown")).strip(),
        "category": str(data.get("category", "Unknown")).strip(),
        "subcategory": str(data.get("subcategory", "Unknown")).strip(),
        "topic": str(data.get("topic", "")).strip(),
        "organization": str(data.get("organization", "")).strip(),
        "year": str(data.get("year", "")).strip(),
        "confidence": round(float(data["confidence"]), 2),
        "reason": str(data.get("reason", "")).strip(),
    }

    return True, "", cleaned
