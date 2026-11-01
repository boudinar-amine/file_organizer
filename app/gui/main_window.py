"""Main application window for Local PDF Organizer.

Coordinates the persistent 3-zone desktop layout:
- Left: Modern Navigation Sidebar (Organize, Knowledge, System)
- Center/Right: Stacked Pages (Dashboard, Scan, Review Workspace, Preview, Activity, Profile, AI, Settings)
- Bottom: Status and Privacy indicators

Maintains 100% backward compatibility with automated test suites while delivering
a modern PowerToys / Windows 11 desktop experience.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from app.classification.classifier import Classifier
from app.classification.profile_discovery import DiscoveredEntity, ProfileDiscoveryEngine
from app.classification.user_profile import UserProfile, get_default_profile
from app.database.database import DatabaseManager
from app.database.models import (
    FileStatus,
    OperationType,
    PDFDocument,
    PDFFileInfo,
)
from app.extraction.pdf_extractor import PDFExtractor
from app.gui.navigation.sidebar import SidebarWidget
from app.gui.pages.activity import ActivityPage
from app.gui.pages.dashboard import DashboardPage
from app.gui.pages.local_ai import LocalAIPage
from app.gui.pages.preview import PreviewPage
from app.gui.pages.profile import ProfilePage
from app.gui.pages.review import ReviewPage
from app.gui.pages.scan import ScanPage
from app.gui.pages.settings import SettingsPage
from app.gui.widgets.theme import Theme
from app.organizer.file_mover import ConflictResolution, FileMover
from app.organizer.planner import OrganizationPlanner
from app.organizer.undo_manager import UndoManager
from app.scanner.pdf_scanner import PDFScanner
from app.utils.app_logging import get_logger

logger = get_logger("gui.main_window")


# ======================================================================
# Background Analysis Worker & Signals
# ======================================================================

class AnalysisSignals(QObject):
    """Signals for background analysis execution."""
    progress = Signal(int, int, str)  # current, total, message
    document_ready = Signal(object)   # PDFDocument
    finished = Signal(list)           # list[PDFDocument]
    error = Signal(str)               # error message
    cancelled = Signal()


class AnalysisWorker(QRunnable):
    """Background worker that scans, extracts, and classifies PDFs without blocking GUI."""

    def __init__(
        self,
        folder: Path,
        include_subfolders: bool,
        max_pages: int,
        use_ollama: bool,
        ollama_model: str,
        user_profile: Optional[UserProfile] = None,
    ) -> None:
        super().__init__()
        self.folder = folder
        self.include_subfolders = include_subfolders
        self.max_pages = max_pages
        self.use_ollama = use_ollama
        self.ollama_model = ollama_model
        self.user_profile = user_profile
        self.signals = AnalysisSignals()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        try:
            self.signals.progress.emit(0, 0, "Scanning for PDFs...")
            scanner = PDFScanner(self.folder, self.include_subfolders)
            file_infos = scanner.scan()

            if not file_infos:
                self.signals.progress.emit(0, 0, "No PDF files found.")
                self.signals.finished.emit([])
                return

            total = len(file_infos)
            self.signals.progress.emit(0, total, f"Found {total} PDF(s). Analyzing...")

            extractor = PDFExtractor(max_pages=self.max_pages)
            classifier = Classifier(
                use_ollama=self.use_ollama,
                ollama_model=self.ollama_model,
                user_profile=self.user_profile,
            )

            documents: list[PDFDocument] = []

            for i, file_info in enumerate(file_infos):
                if self._cancelled:
                    self.signals.cancelled.emit()
                    return

                self.signals.progress.emit(
                    i + 1, total, f"Analyzing: {file_info.filename} ({i + 1}/{total})"
                )

                doc = PDFDocument(file_info=file_info)
                try:
                    metadata, content = extractor.extract_all(file_info.path)
                    doc.metadata = metadata
                    doc.content = content
                    classification = classifier.classify(file_info, metadata, content)
                    doc.classification = classification

                    if content.extraction_error:
                        doc.status = FileStatus.ERROR
                        doc.error_message = content.extraction_error
                    elif content.is_scanned:
                        doc.status = FileStatus.OCR_REQUIRED
                    elif classification.needs_review:
                        doc.status = FileStatus.NEEDS_REVIEW
                    else:
                        doc.status = FileStatus.ANALYZED
                except Exception as e:
                    logger.warning("Error analyzing %s: %s", file_info.filename, e)
                    doc.status = FileStatus.ERROR
                    doc.error_message = str(e)

                documents.append(doc)
                self.signals.document_ready.emit(doc)

            self.signals.finished.emit(documents)
        except Exception as e:
            logger.exception("Analysis worker fatal error: %s", e)
            self.signals.error.emit(str(e))


# ======================================================================
# Main Window
# ======================================================================

class MainWindow(QMainWindow):
    """Desktop application window featuring a persistent 3-zone architecture."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Local PDF Organizer")
        self.setMinimumSize(1100, 680)
        self.resize(1360, 840)

        # Core State
        self._documents: list[PDFDocument] = []
        self._worker: Optional[AnalysisWorker] = None
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(1)

        self._db = DatabaseManager()
        self._undo_manager = UndoManager(self._db)
        self._current_profile: UserProfile = get_default_profile()
        self._discovered_entities: list[DiscoveredEntity] = []

        self._load_config()
        self._build_ui()
        self._setup_shortcuts()
        self._update_button_states()

        # Apply default theme (Dark Mode)
        self.setStyleSheet(Theme.get_stylesheet(dark=True))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        self._config: dict = {
            "max_pages_to_analyze": 2,
            "use_ollama": False,
            "ollama_model": "qwen2.5:1.5b",
            "include_subfolders": True,
            "last_selected_folder": "",
            "organization_root": "",
            "test_mode": True,
        }
        cfg_path = Path(__file__).resolve().parent.parent / "config" / "config.json"
        if cfg_path.is_file():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    self._config.update(json.load(f))
            except Exception as e:
                logger.warning("Could not load config.json: %s", e)

    def _save_config(self) -> None:
        cfg_path = Path(__file__).resolve().parent.parent / "config" / "config.json"
        try:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            logger.warning("Could not save config.json: %s", e)

    # ------------------------------------------------------------------
    # UI Layout (Persistent 3-Zone Architecture)
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ZONE 1: Left Navigation Sidebar
        self._sidebar = SidebarWidget()
        self._sidebar.pageSelected.connect(self._on_navigate_page)
        main_layout.addWidget(self._sidebar)

        # ZONE 2 & 3: Main Stacked Content Pages
        self._stack = QStackedWidget()

        # Create Pages
        self._dashboard_page = DashboardPage()
        self._scan_page = ScanPage()
        self._review_page = ReviewPage()
        self._preview_page = PreviewPage()
        self._activity_page = ActivityPage(self._undo_manager)
        self._profile_page = ProfilePage(self._current_profile)
        self._local_ai_page = LocalAIPage()
        self._settings_page = SettingsPage(self._config)

        # Register pages in stacked widget
        self._stack.addWidget(self._dashboard_page)  # index 0: dashboard
        self._stack.addWidget(self._scan_page)       # index 1: scan
        self._stack.addWidget(self._review_page)     # index 2: review
        self._stack.addWidget(self._preview_page)    # index 3: preview
        self._stack.addWidget(self._activity_page)   # index 4: activity
        self._stack.addWidget(self._profile_page)    # index 5: profile
        self._stack.addWidget(self._local_ai_page)   # index 6: local_ai
        self._stack.addWidget(self._settings_page)   # index 7: settings

        self._page_map = {
            "dashboard": 0,
            "scan": 1,
            "review": 2,
            "preview": 3,
            "organized": 3,
            "activity": 4,
            "profile": 5,
            "rules": 5,
            "local_ai": 6,
            "settings": 7,
        }

        main_layout.addWidget(self._stack, 1)

        # Status Bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready • 100% Offline")

        # Connect Inter-Page Signals
        self._dashboard_page.folderSelected.connect(self._on_dashboard_folder_selected)
        self._dashboard_page.resumeReviewRequested.connect(lambda: self._sidebar.select_page("review"))
        self._dashboard_page.viewHistoryRequested.connect(lambda: self._sidebar.select_page("activity"))

        self._scan_page.analyzeRequested.connect(self._on_start_analysis)
        self._scan_page.cancelRequested.connect(self._on_cancel_analysis)

        self._review_page.previewRequested.connect(self._on_proceed_to_preview)
        self._review_page.documentsChanged.connect(self._on_documents_modified)

        self._preview_page.goBackRequested.connect(lambda: self._sidebar.select_page("review"))
        self._preview_page.organizeRequested.connect(self._on_execute_organization)

        self._activity_page.undoRequested.connect(self._on_undo_operation)

        self._profile_page.profileSaved.connect(self._on_profile_saved)
        self._settings_page.themeChanged.connect(self._on_theme_changed)
        self._settings_page.configSaved.connect(self._on_config_saved)

        # Restore last folder in scan page if configured
        if self._config.get("last_selected_folder"):
            self._scan_page.set_folder(Path(self._config["last_selected_folder"]))

    # ------------------------------------------------------------------
    # Backward Compatibility Properties for automated test suite
    # ------------------------------------------------------------------

    @property
    def _table(self):
        return self._review_page.table

    @property
    def _analyze_btn(self):
        return self._scan_page._analyze_btn

    @property
    def _cancel_btn(self):
        return self._scan_page._cancel_btn

    @property
    def _review_btn(self):
        return self._review_page.review_btn

    @property
    def _preview_btn(self):
        return self._review_page.preview_btn

    @property
    def _organize_btn(self):
        return self._preview_page.organize_btn

    @property
    def _undo_btn(self):
        return self._activity_page.undo_btn

    @property
    def _profile_btn(self):
        return self._profile_page.profile_btn

    @property
    def _ai_combo(self):
        return self._scan_page._ai_combo

    @property
    def _ollama_hint_label(self):
        return self._scan_page._ollama_hint_label

    def _get_document_for_row(self, row: int) -> Optional[PDFDocument]:
        if 0 <= row < len(self._review_page._filtered_docs):
            return self._review_page._filtered_docs[row]
        if 0 <= row < len(self._documents):
            return self._documents[row]
        return None

    def _on_document_ready(self, doc: PDFDocument) -> None:
        self._documents.append(doc)
        self._review_page.add_document(doc)
        self._update_button_states()

    # ------------------------------------------------------------------
    # Keyboard Shortcuts (Section 26)
    # ------------------------------------------------------------------

    def _setup_shortcuts(self) -> None:
        act_scan = QAction(self)
        act_scan.setShortcut(QKeySequence("Ctrl+O"))
        act_scan.triggered.connect(lambda: self._sidebar.select_page("scan"))
        self.addAction(act_scan)

        act_search = QAction(self)
        act_search.setShortcut(QKeySequence("Ctrl+F"))
        act_search.triggered.connect(self._focus_search)
        self.addAction(act_search)

        act_undo = QAction(self)
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        act_undo.triggered.connect(self._on_undo_operation)
        self.addAction(act_undo)

        act_settings = QAction(self)
        act_settings.setShortcut(QKeySequence("Ctrl+,"))
        act_settings.triggered.connect(lambda: self._sidebar.select_page("settings"))
        self.addAction(act_settings)

    def _focus_search(self) -> None:
        self._sidebar.select_page("review")
        self._review_page._search_bar._input.setFocus()

    # ------------------------------------------------------------------
    # Workflow Handlers
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_navigate_page(self, key: str) -> None:
        idx = self._page_map.get(key, 0)
        self._stack.setCurrentIndex(idx)
        if key == "activity":
            self._activity_page.refresh()
        elif key == "local_ai":
            self._local_ai_page.refresh()

    @Slot(Path)
    def _on_dashboard_folder_selected(self, folder: Path) -> None:
        self._scan_page.set_folder(folder)
        self._sidebar.select_page("scan")

    @Slot(Path, bool, int, bool, str)
    def _on_start_analysis(
        self, folder: Path, subfolders: bool, pages: int, use_ollama: bool, model: str
    ) -> None:
        self._documents.clear()
        self._review_page.set_documents([])
        self._config["last_selected_folder"] = str(folder)
        self._save_config()

        self._status_bar.showMessage(f"Scanning folder: {folder}...")
        self._worker = AnalysisWorker(
            folder=folder,
            include_subfolders=subfolders,
            max_pages=pages,
            use_ollama=use_ollama,
            ollama_model=model,
            user_profile=self._current_profile,
        )
        self._worker.signals.progress.connect(self._on_worker_progress)
        self._worker.signals.document_ready.connect(self._on_worker_document_ready)
        self._worker.signals.finished.connect(self._on_worker_finished)
        self._worker.signals.error.connect(self._on_worker_error)
        self._worker.signals.cancelled.connect(self._on_worker_cancelled)

        self._update_button_states()
        self._thread_pool.start(self._worker)

    @Slot()
    def _on_cancel_analysis(self) -> None:
        if self._worker:
            self._worker.cancel()
            self._status_bar.showMessage("Cancelling scan...")

    @Slot(int, int, str)
    def _on_worker_progress(self, current: int, total: int, msg: str) -> None:
        self._scan_page.show_progress(current, total, msg)
        self._status_bar.showMessage(msg)

    @Slot(object)
    def _on_worker_document_ready(self, doc: PDFDocument) -> None:
        self._documents.append(doc)
        self._review_page.add_document(doc)

    @Slot(list)
    def _on_worker_finished(self, documents: list[PDFDocument]) -> None:
        self._documents = documents
        self._worker = None
        self._scan_page.finish_progress()

        # Phase 4: Plan organization paths
        if documents:
            folder_text = self._config.get("last_selected_folder", "")
            folder = Path(folder_text) if folder_text else Path(".")
            planner = OrganizationPlanner(folder)
            planner.plan(self._documents)

            # Discover recurring entities (Section 17)
            try:
                engine = ProfileDiscoveryEngine()
                self._discovered_entities = engine.discover(self._documents)
                self._profile_page.set_discovered_entities(self._discovered_entities)
            except Exception as e:
                logger.warning("Profile discovery error: %s", e)

            # Update Dashboard metrics
            ready = sum(1 for d in documents if d.status == FileStatus.ANALYZED)
            review = sum(1 for d in documents if d.status == FileStatus.NEEDS_REVIEW)
            scanned = sum(1 for d in documents if d.status == FileStatus.OCR_REQUIRED)
            self._dashboard_page.update_metrics(
                discovered=len(documents),
                classified=ready,
                needs_review=review,
                ocr_required=scanned,
                last_folder=str(folder),
            )

            # Pass planned files to preview page
            dest_root = folder.parent / "Organized"
            self._preview_page.set_data(self._documents, dest_root)

            # Navigate to review workspace
            self._sidebar.select_page("review")
            self._status_bar.showMessage(f"Analysis complete: {len(documents)} document(s) categorized.")
        else:
            self._status_bar.showMessage("No documents found to analyze.")

        self._update_button_states()

    @Slot(str)
    def _on_worker_error(self, err: str) -> None:
        self._worker = None
        self._scan_page.finish_progress()
        self._status_bar.showMessage(f"Error: {err}")
        QMessageBox.critical(self, "Analysis Error", f"An error occurred while analyzing:\n{err}")
        self._update_button_states()

    @Slot()
    def _on_worker_cancelled(self) -> None:
        self._worker = None
        self._scan_page.finish_progress()
        self._status_bar.showMessage("Scan cancelled by user.")
        self._update_button_states()

    @Slot()
    def _on_proceed_to_preview(self) -> None:
        folder_text = self._config.get("last_selected_folder", "")
        folder = Path(folder_text) if folder_text else Path(".")
        dest_root = folder.parent / "Organized"
        self._preview_page.set_data(self._documents, dest_root)
        self._sidebar.select_page("preview")

    @Slot(list)
    def _on_documents_modified(self, docs: list[PDFDocument]) -> None:
        self._documents = docs
        folder_text = self._config.get("last_selected_folder", "")
        folder = Path(folder_text) if folder_text else Path(".")
        dest_root = folder.parent / "Organized"
        self._preview_page.set_data(self._documents, dest_root)

    @Slot(bool, bool)
    def _on_execute_organization(self, is_copy: bool, auto_rename: bool) -> None:
        organizable = [
            d for d in self._documents
            if d.suggested_path and d.status not in (
                FileStatus.REJECTED, FileStatus.IGNORED, FileStatus.ERROR, FileStatus.MOVED, FileStatus.COPIED
            )
        ]
        if not organizable:
            QMessageBox.information(self, "No Files", "No eligible files to organize.")
            return

        op_type = OperationType.COPY if is_copy else OperationType.MOVE
        strat = ConflictResolution.AUTO_RENAME if auto_rename else ConflictResolution.SKIP_AND_FLAG

        mover = FileMover(db=self._db, operation_type=op_type, conflict_resolution=strat)
        results = mover.organize_documents(organizable)

        success = sum(1 for r in results if r.success)
        conflicts = sum(1 for r in results if r.conflict_detected)
        errors = sum(1 for r in results if not r.success and not r.conflict_detected)

        # Update activity & dashboard
        self._activity_page.refresh()
        self._dashboard_page.update_metrics(
            discovered=len(self._documents),
            classified=0,
            needs_review=0,
            ocr_required=0,
            last_activity=f"{success} files {op_type.value}d successfully",
        )

        QMessageBox.information(
            self,
            "Organization Complete",
            f"Successfully {op_type.value}d {success} file(s)!\n"
            f"Conflicts: {conflicts} • Errors: {errors}\n\n"
            "This operation can be safely undone at any time under Activity & Undo."
        )
        self._sidebar.select_page("activity")

    @Slot()
    def _on_undo_operation(self) -> None:
        if not self._undo_manager.can_undo():
            QMessageBox.information(self, "Nothing to Undo", "No eligible operations to reverse.")
            return

        reply = QMessageBox.question(
            self, "Confirm Undo", "Safely restore files to their previous locations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            res = self._undo_manager.undo_last_batch()
            self._activity_page.refresh()
            if res.success:
                self._status_bar.showMessage("Operation successfully undone.")
                QMessageBox.information(self, "Undo Complete", "Files were safely restored.")
            else:
                QMessageBox.warning(self, "Undo Failed", "Could not fully restore all files.")

    @Slot(object)
    def _on_profile_saved(self, profile: UserProfile) -> None:
        self._current_profile = profile
        self._save_config()
        self._status_bar.showMessage(f"Profile '{profile.name}' saved.", 4000)

    @Slot(bool)
    def _on_theme_changed(self, is_dark: bool) -> None:
        self.setStyleSheet(Theme.get_stylesheet(dark=is_dark))

    @Slot(dict)
    def _on_config_saved(self, cfg: dict) -> None:
        self._config.update(cfg)
        self._save_config()
        self._status_bar.showMessage("Preferences saved.", 4000)

    def _update_button_states(self) -> None:
        has_docs = len(self._documents) > 0
        is_analyzing = self._worker is not None

        self._scan_page._analyze_btn.setEnabled(not is_analyzing)
        self._scan_page._cancel_btn.setEnabled(is_analyzing)
        self._review_page.review_btn.setEnabled(has_docs and not is_analyzing)
        self._review_page.preview_btn.setEnabled(has_docs and not is_analyzing)
        self._preview_page.organize_btn.setEnabled(has_docs and not is_analyzing)
        self._activity_page.undo_btn.setEnabled(self._undo_manager.can_undo())
