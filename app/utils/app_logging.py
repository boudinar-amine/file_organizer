"""Application logging configuration.

Named app_logging to avoid shadowing the stdlib logging module.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from app.utils.paths import get_log_dir


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the application logger.

    Logs go to both a file and stderr. File logs include timestamps
    and module names. Confidential document content must NEVER be logged.

    Args:
        level: The logging level (default: INFO).

    Returns:
        Configured root application logger.
    """
    logger = logging.getLogger("pdf_organizer")
    if logger.handlers:
        # Already configured
        return logger

    logger.setLevel(level)

    # --- File handler ---
    log_dir = get_log_dir()
    log_file = log_dir / f"organizer_{datetime.now():%Y%m%d}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # --- Console handler ---
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_fmt = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the application root.

    Args:
        name: Dot-separated logger name (e.g. 'scanner', 'extraction').

    Returns:
        A child logger instance.
    """
    return logging.getLogger(f"pdf_organizer.{name}")
