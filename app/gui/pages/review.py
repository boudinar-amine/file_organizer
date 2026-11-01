"""Review Workspace — The 3-panel core workflow screen (Section 5 & 6).

LEFT: Hierarchical Category Tree with count badges & filter tabs.
CENTER: Clean Document Table with multi-select, search, and sorting.
RIGHT: Persistent Document Inspector with editable dropdowns & evidence cards.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.models import FileStatus, PDFDocument
from app.gui.widgets.confidence_badge import ConfidenceBadge, StatusBadge
from app.gui.widgets.document_inspector import DocumentInspectorWidget
from app.gui.widgets.search_bar import SearchBar


class ReviewPage(QWidget):
    """The 3-panel Review Workspace."""

    previewRequested = Signal()
    documentsChanged = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._documents: list[PDFDocument] = []
        self._filtered_docs: list[PDFDocument] = []
        self._current_filter_tab = "all"  # 'all', 'review', 'scanned', 'high'

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Top Bar: Title, Search, and Preview action button
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Review Workspace")
        t_font = QFont()
        t_font.setPointSize(16)
        t_font.setBold(True)
        title.setFont(t_font)
        title.setStyleSheet("color: #f8fafc;")
        self._subtitle = QLabel("Review and adjust classifications before organizing.")
        self._subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(self._subtitle)
        top_bar.addLayout(title_box)

        top_bar.addSpacing(20)
        self._search_bar = SearchBar("Search documents by name, type, org…")
        self._search_bar.setFixedWidth(280)
        self._search_bar.searchChanged.connect(self._on_search_filter_changed)
        top_bar.addWidget(self._search_bar)

        top_bar.addStretch()

        self._review_btn = QPushButton("Accept All High Confidence")
        self._review_btn.clicked.connect(self._on_accept_high_confidence)
        top_bar.addWidget(self._review_btn)

        self._preview_btn = QPushButton("📁  Proceed to Preview")
        self._preview_btn.setProperty("class", "primary")
        self._preview_btn.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: 700; padding: 6px 18px; border-radius: 6px;"
        )
        self._preview_btn.clicked.connect(self.previewRequested.emit)
        top_bar.addWidget(self._preview_btn)

        main_layout.addLayout(top_bar)

        # 3-Panel Horizontal Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # =====================================================================
        # PANEL 1 (LEFT): Category Tree & Filter Tabs
        # =====================================================================
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_panel.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        # Tabs / Filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self._tab_all = QPushButton("All")
        self._tab_review = QPushButton("Needs Review")
        self._tab_scanned = QPushButton("OCR")
        self._tab_high = QPushButton("High Conf")

        for b in (self._tab_all, self._tab_review, self._tab_scanned, self._tab_high):
            b.setFixedHeight(26)
            b.setStyleSheet(
                "QPushButton { font-size: 11px; padding: 2px 6px; background-color: #0f172a; "
                "color: #94a3b8; border: 1px solid #334155; border-radius: 4px; } "
                "QPushButton:hover { background-color: #334155; color: #f8fafc; }"
            )
            filter_row.addWidget(b)

        self._tab_all.clicked.connect(lambda: self._set_filter_tab("all"))
        self._tab_review.clicked.connect(lambda: self._set_filter_tab("review"))
        self._tab_scanned.clicked.connect(lambda: self._set_filter_tab("scanned"))
        self._tab_high.clicked.connect(lambda: self._set_filter_tab("high"))
        left_layout.addLayout(filter_row)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.itemClicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self._tree, 1)

        splitter.addWidget(left_panel)

        # =====================================================================
        # PANEL 2 (CENTER): Document List Table
        # =====================================================================
        center_panel = QFrame()
        center_panel.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px;")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.setSpacing(6)

        table_header = QHBoxLayout()
        self._list_title = QLabel("All Documents")
        self._list_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #f8fafc;")
        table_header.addWidget(self._list_title)
        table_header.addStretch()

        self._item_count_lbl = QLabel("0 files")
        self._item_count_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        table_header.addWidget(self._item_count_lbl)
        center_layout.addLayout(table_header)

        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels([
            "✓", "Filename", "Current Folder", "Document Type",
            "Category", "Subcategory", "Suggested Destination",
            "Confidence", "Status",
        ])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 36)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(1, 200)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(2, 120)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(3, 110)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(4, 120)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(5, 120)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(7, 95)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(8, 95)

        self._table.itemSelectionChanged.connect(self._on_table_selection_changed)
        center_layout.addWidget(self._table, 1)

        splitter.addWidget(center_panel)

        # =====================================================================
        # PANEL 3 (RIGHT): Persistent Document Inspector
        # =====================================================================
        self._inspector = DocumentInspectorWidget()
        self._inspector.documentUpdated.connect(self._on_document_updated_from_inspector)
        splitter.addWidget(self._inspector)

        # Set panel proportions (240px left, flex center, 320px right)
        splitter.setSizes([220, 580, 320])
        main_layout.addWidget(splitter, 1)

    # -------------------------------------------------------------------------
    # Public API for MainWindow
    # -------------------------------------------------------------------------

    @property
    def table(self) -> QTableWidget:
        return self._table

    @property
    def review_btn(self) -> QPushButton:
        return self._review_btn

    @property
    def preview_btn(self) -> QPushButton:
        return self._preview_btn

    def set_documents(self, documents: list[PDFDocument]) -> None:
        """Load analyzed documents into the workspace."""
        self._documents = documents
        self._apply_filters()

    def add_document(self, doc: PDFDocument) -> None:
        """Add a single document incrementally as it finishes analysis."""
        self._documents.append(doc)
        self._apply_filters()

    # -------------------------------------------------------------------------
    # Filtering & Tree Population
    # -------------------------------------------------------------------------

    def _set_filter_tab(self, tab: str) -> None:
        self._current_filter_tab = tab
        styles_active = "background-color: #1e3a8a; color: #93c5fd; font-weight: bold; border: 1px solid #2563eb; border-radius: 4px;"
        styles_idle = "background-color: #0f172a; color: #94a3b8; border: 1px solid #334155; border-radius: 4px;"

        self._tab_all.setStyleSheet(styles_active if tab == "all" else styles_idle)
        self._tab_review.setStyleSheet(styles_active if tab == "review" else styles_idle)
        self._tab_scanned.setStyleSheet(styles_active if tab == "scanned" else styles_idle)
        self._tab_high.setStyleSheet(styles_active if tab == "high" else styles_idle)

        self._apply_filters()

    def _apply_filters(self, category_filter: Optional[str] = None) -> None:
        search = self._search_bar.text().lower()

        filtered = []
        for d in self._documents:
            # Tab filter
            if self._current_filter_tab == "review" and not d.classification.needs_review:
                continue
            if self._current_filter_tab == "scanned" and d.status != FileStatus.OCR_REQUIRED:
                continue
            if self._current_filter_tab == "high" and d.classification.confidence < 0.80:
                continue

            # Category tree filter
            if category_filter:
                cat = d.classification.category if d.classification else "Unknown"
                if cat != category_filter:
                    continue

            # Text search filter
            if search:
                fn = d.file_info.filename.lower()
                c = (d.classification.category or "").lower() if d.classification else ""
                s = (d.classification.subcategory or "").lower() if d.classification else ""
                o = (d.classification.organization or "").lower() if d.classification else ""
                t = (d.classification.document_type or "").lower() if d.classification else ""
                if not any(search in field for field in (fn, c, s, o, t)):
                    continue

            filtered.append(d)

        self._filtered_docs = filtered
        self._rebuild_tree()
        self._populate_table()

    def _rebuild_tree(self) -> None:
        self._tree.clear()

        # Count documents by category and subcategory
        categories: dict[str, dict[str, list[PDFDocument]]] = {}
        for d in self._documents:
            cat = d.classification.category if d.classification else "Unknown"
            subcat = d.classification.subcategory if d.classification else "General"
            if cat not in categories:
                categories[cat] = {}
            if subcat not in categories[cat]:
                categories[cat][subcat] = []
            categories[cat][subcat].append(d)

        # Root item "All Documents"
        all_root = QTreeWidgetItem(self._tree, [f"All Documents ({len(self._documents)})"])
        all_root.setData(0, Qt.ItemDataRole.UserRole, "__all__")

        for cat_name, subcats in sorted(categories.items()):
            cat_count = sum(len(docs) for docs in subcats.values())
            cat_item = QTreeWidgetItem(self._tree, [f"📁 {cat_name} ({cat_count})"])
            cat_item.setData(0, Qt.ItemDataRole.UserRole, cat_name)

            for subcat_name, docs in sorted(subcats.items()):
                sub_item = QTreeWidgetItem(cat_item, [f"{subcat_name} ({len(docs)})"])
                sub_item.setData(0, Qt.ItemDataRole.UserRole, f"{cat_name}::{subcat_name}")

        self._tree.expandItem(all_root)

    def _populate_table(self) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._filtered_docs))
        self._item_count_lbl.setText(f"{len(self._filtered_docs)} files")

        for row, doc in enumerate(self._filtered_docs):
            # Column 0: Checkbox
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check_item.setCheckState(Qt.CheckState.Checked if doc.status != FileStatus.REJECTED else Qt.CheckState.Unchecked)
            self._table.setItem(row, 0, check_item)

            # Column 1: Filename
            fn_item = QTableWidgetItem(doc.file_info.filename)
            fn_item.setData(Qt.ItemDataRole.UserRole, doc)
            self._table.setItem(row, 1, fn_item)

            # Column 2: Current Folder
            folder_name = doc.file_info.path.parent.name if doc.file_info.path.parent else ""
            self._table.setItem(row, 2, QTableWidgetItem(folder_name))

            # Column 3: Document Type
            doc_type = doc.classification.document_type if doc.classification else "—"
            self._table.setItem(row, 3, QTableWidgetItem(doc_type))

            # Column 4: Category
            cat = doc.classification.category if doc.classification else "—"
            self._table.setItem(row, 4, QTableWidgetItem(cat))

            # Column 5: Subcategory
            subcat = doc.classification.subcategory if doc.classification else "—"
            self._table.setItem(row, 5, QTableWidgetItem(subcat))

            # Column 6: Suggested Destination
            dest_str = str(doc.suggested_path) if doc.suggested_path else "—"
            self._table.setItem(row, 6, QTableWidgetItem(dest_str))

            # Column 7: Confidence Badge
            conf = doc.classification.confidence if doc.classification else 0.0
            badge = ConfidenceBadge(conf)
            self._table.setCellWidget(row, 7, badge)

            # Column 8: Status Badge
            if doc.status == FileStatus.OCR_REQUIRED:
                st_badge = StatusBadge("OCR Required", "warning")
            elif doc.classification and doc.classification.needs_review:
                st_badge = StatusBadge("Needs Review", "warning")
            else:
                st_badge = StatusBadge("Ready", "success")
            self._table.setCellWidget(row, 8, st_badge)

        self._table.setSortingEnabled(True)

        if self._filtered_docs:
            self._table.selectRow(0)

    # -------------------------------------------------------------------------
    # UI Event Handlers
    # -------------------------------------------------------------------------

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key == "__all__":
            self._list_title.setText("All Documents")
            self._apply_filters(None)
        elif key:
            cat_name = key.split("::")[0]
            self._list_title.setText(f"Category: {cat_name}")
            self._apply_filters(cat_name)

    def _on_search_filter_changed(self, text: str) -> None:
        self._apply_filters()

    def _on_table_selection_changed(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._filtered_docs):
            doc = self._filtered_docs[row]
            self._inspector.set_document(doc)
        else:
            self._inspector.set_document(None)

    def _on_document_updated_from_inspector(self, doc: PDFDocument) -> None:
        """When user edits dropdowns in inspector, refresh row and tree."""
        self._populate_table()
        self._rebuild_tree()
        self.documentsChanged.emit(self._documents)

    def _on_accept_high_confidence(self) -> None:
        for doc in self._documents:
            if doc.classification and doc.classification.confidence >= 0.80:
                doc.status = FileStatus.APPROVED
        self._apply_filters()
        self.documentsChanged.emit(self._documents)
