"""Local PDF Organizer — Application entry point.

Usage:
    python main.py
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `app.*` imports work
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.utils.app_logging import setup_logging


def main() -> None:
    """Launch the Local PDF Organizer desktop application."""
    logger = setup_logging()
    logger.info("Starting Local PDF Organizer v0.1.0")

    try:
        from PySide6.QtWidgets import QApplication
        from app.gui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("Local PDF Organizer")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("LocalPDFOrganizer")

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        print(f"Error: Missing dependency — {e}")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
