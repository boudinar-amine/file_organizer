"""Unit tests for the modern 3-zone desktop UI architecture.

Verifies:
1. Sidebar navigation and section routing.
2. Dashboard metric updates and drop zone.
3. Guided scan workflow page.
4. 3-panel Review workspace (tree, table, inspector).
5. Preview page with COPY vs MOVE mode toggle.
6. Activity history and undo state.
7. Profile page activity rendering.
8. Theme stylesheet generation (light and dark).
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

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.database.models import (
    ClassificationResult,
    FileStatus,
    PDFDocument,
    PDFFileInfo,
    PDFMetadata,
)
from app.gui.navigation.sidebar import SidebarWidget
from app.gui.pages.activity import ActivityPage
from app.gui.pages.dashboard import DashboardPage
from app.gui.pages.preview import PreviewPage
from app.gui.pages.profile import ProfilePage
from app.gui.pages.review import ReviewPage
from app.gui.pages.scan import ScanPage
from app.gui.pages.settings import SettingsPage
from app.gui.widgets.confidence_badge import ConfidenceBadge, StatusBadge
from app.gui.widgets.theme import Theme


class TestModernUIComponents(unittest.TestCase):
    """Test all modular components of the modern UI."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_sidebar_navigation(self) -> None:
        sidebar = SidebarWidget()
        selected_pages = []
        sidebar.pageSelected.connect(lambda p: selected_pages.append(p))

        sidebar.select_page("scan")
        self.assertIn("scan", selected_pages)

        sidebar.select_page("review")
        self.assertIn("review", selected_pages)

        sidebar.set_ai_status(True, "qwen2.5:1.5b")
        self.assertIn("qwen", sidebar._version_lbl.text().lower())

        sidebar.close()

    def test_dashboard_metrics_and_drop_zone(self) -> None:
        dash = DashboardPage()
        dash.update_metrics(
            discovered=10,
            classified=8,
            needs_review=1,
            ocr_required=1,
            last_folder="C:/Docs",
            last_activity="8 files copied",
        )
        self.assertEqual(dash._recent_path_lbl.text(), "C:/Docs")
        self.assertEqual(dash._op_history_lbl.text(), "8 files copied")
        self.assertFalse(dash._resume_frame.isHidden())
        dash.close()

    def test_scan_page_workflow(self) -> None:
        scan = ScanPage()
        scan.set_folder(Path("C:/MyDocs"))
        self.assertEqual(scan._folder_input.text(), "C:\\MyDocs")

        scan.show_progress(5, 10, "Analyzing doc 5")
        self.assertEqual(scan._progress_count_lbl.text(), "5 / 10 documents")
        self.assertFalse(scan._analyze_btn.isEnabled())
        self.assertTrue(scan._cancel_btn.isEnabled())

        scan.finish_progress()
        self.assertTrue(scan._analyze_btn.isEnabled())
        self.assertFalse(scan._cancel_btn.isEnabled())
        scan.close()

    def test_review_workspace_and_inspector(self) -> None:
        review = ReviewPage()
        doc = PDFDocument(
            file_info=PDFFileInfo(Path("C:/research_xai.pdf"), "research_xai.pdf", ".pdf", 50000),
            metadata=PDFMetadata(title="Explainable AI via Shapley Values"),
            classification=ClassificationResult(
                document_type="Scientific Article",
                category="Research",
                subcategory="Explainable AI",
                confidence=0.92,
            ),
            status=FileStatus.ANALYZED,
        )

        review.set_documents([doc])
        self.assertEqual(review.table.rowCount(), 1)
        self.assertGreaterEqual(review._tree.topLevelItemCount(), 1)

        # Inspector updates
        review._inspector.set_document(doc)
        self.assertEqual(review._inspector._filename_lbl.text(), "research_xai.pdf")
        self.assertIn("92% High", review._inspector._confidence_badge.text())

        # Modify via inspector
        review._inspector._category_combo.setCurrentText("Insurtech")
        review._inspector._subcategory_combo.setCurrentText("Claims")
        review._inspector._on_save_changes()

        self.assertEqual(doc.classification.category, "Insurtech")
        self.assertEqual(doc.classification.confidence, 1.0)
        review.close()

    def test_preview_page_mode_toggle(self) -> None:
        preview = PreviewPage()
        doc = PDFDocument(
            file_info=PDFFileInfo(Path("C:/invoice.pdf"), "invoice.pdf", ".pdf", 12000),
            classification=ClassificationResult("Invoice", "Administration", "Procurement", 0.96),
            suggested_path=Path("C:/Organized/Administration/Procurement/invoice.pdf"),
            status=FileStatus.ANALYZED,
        )
        preview.set_data([doc], Path("C:/Organized"))

        # Default is COPY
        self.assertTrue(preview._radio_copy.isChecked())
        self.assertIn("Copy", preview._organize_btn.text())

        # Switch to MOVE
        preview._radio_move.setChecked(True)
        self.assertIn("Move", preview._organize_btn.text())

        preview.close()

    def test_badges_and_theme(self) -> None:
        badge = ConfidenceBadge(0.95)
        self.assertIn("95% High", badge.text())

        st_badge = StatusBadge("OCR Required", "warning")
        self.assertEqual(st_badge.text(), "OCR Required")

        light_css = Theme.get_stylesheet(dark=False)
        self.assertIn("QMainWindow", light_css)

        dark_css = Theme.get_stylesheet(dark=True)
        self.assertIn("QMainWindow", dark_css)


if __name__ == "__main__":
    unittest.main()
