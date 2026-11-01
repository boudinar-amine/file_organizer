"""Interactive Organization Preview & Safe Execution page (Section 7 & 8).

Shows hierarchical destination tree, summary metrics, folder renaming,
exclusion, and persistent bottom safety action bar (COPY vs MOVE).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.models import FileStatus, PDFDocument
from app.gui.widgets.confirm_dialog import ConfirmOperationDialog


class PreviewPage(QWidget):
    """Hierarchical destination tree preview with persistent execution action bar."""

    organizeRequested = Signal(bool, bool)  # is_copy_mode, auto_rename_conflicts
    goBackRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._documents: list[PDFDocument] = []
        self._dest_root: Path = Path(".")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 16)
        main_layout.setSpacing(12)

        # 1. Header & Summary Bar
        header_row = QHBoxLayout()
        h_box = QVBoxLayout()
        title = QLabel("Organization Preview")
        t_font = QFont()
        t_font.setPointSize(16)
        t_font.setBold(True)
        title.setFont(t_font)
        self._summary_lbl = QLabel("0 files analyzed • 0 ready to organize")
        self._summary_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        h_box.addWidget(title)
        h_box.addWidget(self._summary_lbl)
        header_row.addLayout(h_box)
        header_row.addStretch()

        self._back_btn = QPushButton("← Back to Review")
        self._back_btn.clicked.connect(self.goBackRequested.emit)
        header_row.addWidget(self._back_btn)
        main_layout.addLayout(header_row)

        # 2. Destination Root path display/edit
        dest_bar = QHBoxLayout()
        dest_lbl = QLabel("Destination Directory:")
        dest_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1; font-size: 12px;")
        self._dest_input = QLineEdit()
        self._dest_input.setPlaceholderText("Target folder for organized structure...")
        self._dest_input.setFixedHeight(30)
        self._dest_input.textChanged.connect(self._on_dest_changed)
        dest_bar.addWidget(dest_lbl)
        dest_bar.addWidget(self._dest_input, 1)
        main_layout.addLayout(dest_bar)

        # 3. Hierarchical Preview Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Planned Directory Structure", "Action", "Document Count"])
        self._tree.setAnimated(True)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self._tree.setColumnWidth(1, 140)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._tree.setColumnWidth(2, 110)
        main_layout.addWidget(self._tree, 1)

        # 4. Persistent Safety Action Bar (Section 8)
        action_bar = QFrame()
        action_bar.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px;"
        )
        act_layout = QHBoxLayout(action_bar)
        act_layout.setContentsMargins(10, 6, 10, 6)
        act_layout.setSpacing(16)

        # Left: Ready count & mode selector
        mode_box = QVBoxLayout()
        mode_box.setSpacing(2)
        self._ready_count_lbl = QLabel("<b>0 files ready</b>")
        self._ready_count_lbl.setStyleSheet("font-size: 13px; color: #f8fafc;")
        mode_box.addWidget(self._ready_count_lbl)

        # Radio buttons: COPY vs MOVE
        radios_row = QHBoxLayout()
        radios_row.setSpacing(12)
        self._radio_copy = QRadioButton("COPY — Safe Test Mode (Originals untouched)")
        self._radio_copy.setChecked(True)
        self._radio_copy.toggled.connect(self._update_action_button_text)
        self._radio_move = QRadioButton("MOVE — Relocate Originals (Reversible with Undo)")
        self._radio_move.toggled.connect(self._update_action_button_text)
        radios_row.addWidget(self._radio_copy)
        radios_row.addWidget(self._radio_move)
        mode_box.addLayout(radios_row)
        act_layout.addLayout(mode_box, 1)

        # Conflict strategy dropdown
        act_layout.addWidget(QLabel("Conflict:"))
        self._conflict_combo = QComboBox()
        self._conflict_combo.addItems(["Auto-rename with (1)", "Skip duplicates"])
        self._conflict_combo.setFixedHeight(34)
        act_layout.addWidget(self._conflict_combo)

        # Primary Organize Action Button
        self._organize_btn = QPushButton("⚡  Copy 0 Files")
        self._organize_btn.setProperty("class", "primary")
        self._organize_btn.setFixedHeight(40)
        self._organize_btn.setStyleSheet(
            "background-color: #16a34a; color: white; font-weight: 700; font-size: 13px; padding: 0 24px; border-radius: 6px;"
        )
        self._organize_btn.clicked.connect(self._on_execute_click)
        act_layout.addWidget(self._organize_btn)

        main_layout.addWidget(action_bar)

    @property
    def organize_btn(self) -> QPushButton:
        return self._organize_btn

    @property
    def preview_btn(self) -> QPushButton:
        return self._organize_btn

    def set_data(self, documents: list[PDFDocument], destination_root: Path) -> None:
        """Populate destination tree with planned structure."""
        self._documents = documents
        self._dest_root = destination_root
        self._dest_input.setText(str(destination_root))
        self._refresh_tree()

    def _on_dest_changed(self, text: str) -> None:
        if text.strip():
            self._dest_root = Path(text.strip())

    def _refresh_tree(self) -> None:
        self._tree.clear()

        ready_count = 0
        review_count = 0
        scanned_count = 0

        # Build folder hierarchy from suggested_paths
        folder_map: dict[str, list[PDFDocument]] = {}
        for d in self._documents:
            if d.status == FileStatus.REJECTED or d.status == FileStatus.IGNORED:
                continue
            if d.status == FileStatus.OCR_REQUIRED:
                scanned_count += 1
            elif d.classification and d.classification.needs_review:
                review_count += 1
            else:
                ready_count += 1

            if d.suggested_path:
                try:
                    rel = d.suggested_path.relative_to(self._dest_root)
                    folder_key = str(rel.parent)
                except Exception:
                    folder_key = "General"
            else:
                folder_key = "Unclassified"

            if folder_key not in folder_map:
                folder_map[folder_key] = []
            folder_map[folder_key].append(d)

        # Update summary
        total = len(self._documents)
        self._summary_lbl.setText(
            f"{total} files analyzed • <b>{ready_count} ready</b> • {review_count} need review • {scanned_count} scanned"
        )
        self._ready_count_lbl.setText(f"<b>{ready_count} files ready to organize</b>")
        self._update_action_button_text()

        # Root Item
        root_item = QTreeWidgetItem(self._tree, [f"📂 {self._dest_root.name or 'Organized'}", "Destination", f"{ready_count} files"])
        root_item.setExpanded(True)

        for folder_path, docs in sorted(folder_map.items()):
            folder_item = QTreeWidgetItem(root_item, [f"📁 {folder_path}", "Folder", f"{len(docs)} files"])
            folder_item.setExpanded(True)

            for doc in docs:
                action_text = "Copy" if self._radio_copy.isChecked() else "Move"
                file_item = QTreeWidgetItem(folder_item, [f"📄 {doc.file_info.filename}", action_text, "1 file"])
                if doc.status == FileStatus.APPROVED:
                    file_item.setText(1, "Modified by you")

        self._organize_btn.setEnabled(ready_count > 0)

    def _update_action_button_text(self) -> None:
        ready = sum(1 for d in self._documents if d.status not in (FileStatus.REJECTED, FileStatus.IGNORED, FileStatus.ERROR))
        mode = "Copy" if self._radio_copy.isChecked() else "Move"
        self._organize_btn.setText(f"⚡  {mode} {ready} Files")
        if mode == "Move":
            self._organize_btn.setStyleSheet(
                "background-color: #2563eb; color: white; font-weight: 700; font-size: 13px; padding: 0 24px; border-radius: 6px;"
            )
        else:
            self._organize_btn.setStyleSheet(
                "background-color: #16a34a; color: white; font-weight: 700; font-size: 13px; padding: 0 24px; border-radius: 6px;"
            )

    def _on_execute_click(self) -> None:
        is_copy = self._radio_copy.isChecked()
        auto_rename = (self._conflict_combo.currentIndex() == 0)

        # Section 9 Confirmation Dialog
        ready_count = sum(1 for d in self._documents if d.status not in (FileStatus.REJECTED, FileStatus.IGNORED, FileStatus.ERROR))
        skipped_count = len(self._documents) - ready_count
        source_dir = self._documents[0].file_info.path.parent if self._documents else Path(".")

        dialog = ConfirmOperationDialog(
            source=source_dir,
            destination=self._dest_root,
            mode_is_copy=is_copy,
            ready_count=ready_count,
            skipped_count=skipped_count,
            conflict_count=0,
            parent=self,
        )
        if dialog.exec() == ConfirmOperationDialog.DialogCode.Accepted:
            self.organizeRequested.emit(is_copy, dialog.auto_rename_conflicts)
