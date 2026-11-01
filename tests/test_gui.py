"""Headless GUI tests for MainWindow.

Verifies that PySide6 GUI initializes properly, controls exist,
and user interface actions function without a physical display.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Run Qt offscreen so no display window pops up during automated tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestMainWindowHeadless(unittest.TestCase):
    """Test MainWindow instantiation and widget states."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        # Ensure a single QApplication instance exists
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_window_initialization(self) -> None:
        from app.gui.main_window import MainWindow

        window = MainWindow()
        self.assertEqual(window.windowTitle(), "Local PDF Organizer")
        self.assertIsNotNone(window._table)
        self.assertIsNotNone(window._analyze_btn)
        self.assertIsNotNone(window._review_btn)
        self.assertIsNotNone(window._preview_btn)
        self.assertIsNotNone(window._organize_btn)
        self.assertIsNotNone(window._undo_btn)

        # Initial button states
        self.assertTrue(window._analyze_btn.isEnabled())
        self.assertFalse(window._cancel_btn.isEnabled())
        self.assertFalse(window._review_btn.isEnabled())
        self.assertFalse(window._preview_btn.isEnabled())
        self.assertFalse(window._organize_btn.isEnabled())

        # Columns
        self.assertEqual(window._table.columnCount(), 9)

        # Profile button
        self.assertIsNotNone(window._profile_btn)
        self.assertTrue(len(window._profile_btn.text()) > 0)

        window.close()

    def test_profile_and_ai_combo_interaction(self) -> None:
        from app.gui.main_window import MainWindow

        window = MainWindow()
        self.assertEqual(window._current_profile.domains[0].category, "Research")

        # Select Ollama (index 1)
        window._ai_combo.setCurrentIndex(1)
        # Should not be hidden if models missing or connected
        self.assertFalse(window._ollama_hint_label.isHidden())

        # Select Rules only (index 0)
        window._ai_combo.setCurrentIndex(0)
        self.assertTrue(window._ollama_hint_label.isHidden())

        window.close()

    def test_add_and_retrieve_document_in_table(self) -> None:
        from app.database.models import (
            ClassificationResult,
            FileStatus,
            PDFDocument,
            PDFFileInfo,
        )
        from app.gui.main_window import MainWindow

        window = MainWindow()

        doc = PDFDocument(
            file_info=PDFFileInfo(
                path=Path("C:/test/sample.pdf"),
                filename="sample.pdf",
                extension=".pdf",
                size_bytes=2048,
            ),
            classification=ClassificationResult(
                document_type="Report",
                category="Public Health",
                subcategory="WHO",
                confidence=0.94,
            ),
            status=FileStatus.ANALYZED,
        )

        window._on_document_ready(doc)

        self.assertEqual(window._table.rowCount(), 1)
        retrieved = window._get_document_for_row(0)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.file_info.filename, "sample.pdf")
        self.assertEqual(retrieved.classification.category, "Public Health")

        window.close()


if __name__ == "__main__":
    unittest.main()
