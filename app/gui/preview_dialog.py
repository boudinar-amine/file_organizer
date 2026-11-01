"""Interactive Organization Preview Dialog.

Provides a rich, hierarchical UI/UX preview of how files will be organized
into Categories and Subcategories, with search filtering, folder tree navigation,
confidence indicators, and a document inspector card.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.models import (
    ConfidenceLevel,
    FileStatus,
    PDFDocument,
)


class PreviewOrganizationDialog(QDialog):
    """Rich interactive preview dialog for planned file organization."""

    def __init__(
        self,
        documents: list[PDFDocument],
        destination_root: Path,
        is_copy_mode: bool = True,
        auto_rename_conflicts: bool = False,
        on_confirm_organize: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Organization Preview & Destination Tree")
        self.setMinimumSize(980, 680)
        self.resize(1100, 750)

        self._documents = [
            d for d in documents
            if d.suggested_path and d.status not in (
                FileStatus.REJECTED,
                FileStatus.ERROR,
                FileStatus.IGNORED,
                FileStatus.MOVED,
                FileStatus.COPIED,
            )
        ]
        self._destination_root = destination_root
        self._is_copy_mode = is_copy_mode
        self._auto_rename_conflicts = auto_rename_conflicts
        self._on_confirm_organize = on_confirm_organize

        self._build_ui()
        self._populate_tree()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Header Banner
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "QFrame { background-color: #f8fafc; border: 1px solid #e2e8f0; "
            "border-radius: 8px; padding: 12px; }"
        )
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_label = QLabel("📁  Interactive Organization Preview")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_row.addWidget(title_label)

        title_row.addStretch()

        mode_badge = QLabel(
            "🛡️ Mode: Safe Copy (Originals Preserved)"
            if self._is_copy_mode
            else "⚠️ Mode: Live Move (Files Relocated)"
        )
        mode_badge.setStyleSheet(
            f"padding: 4px 10px; border-radius: 4px; font-weight: bold; "
            f"background-color: {'#dcfce7; color: #166534;' if self._is_copy_mode else '#fef3c7; color: #92400e;'}"
        )
        title_row.addWidget(mode_badge)

        conflict_badge = QLabel(
            "Conflict: Auto-rename (1)"
            if self._auto_rename_conflicts
            else "Conflict: Skip safely"
        )
        conflict_badge.setStyleSheet(
            "padding: 4px 10px; border-radius: 4px; font-weight: bold; "
            "background-color: #f1f5f9; color: #334155;"
        )
        title_row.addWidget(conflict_badge)

        header_layout.addLayout(title_row)

        desc_label = QLabel(
            f"<b>Destination Root:</b> <code>{self._destination_root}</code> &nbsp;|&nbsp; "
            f"<b>Files to Organize:</b> {len(self._documents)} file(s)"
        )
        desc_label.setStyleSheet("color: #475569; font-size: 12px;")
        header_layout.addWidget(desc_label)

        main_layout.addWidget(header_frame)

        # 2. Search & Filter Bar
        filter_row = QHBoxLayout()
        filter_label = QLabel("🔍 Filter:")
        filter_row.addWidget(filter_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter by file name, category, subcategory, or document type...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_changed)
        filter_row.addWidget(self._search_input, 1)

        self._expand_btn = QPushButton("Expand All")
        self._expand_btn.setFixedHeight(30)
        self._expand_btn.clicked.connect(lambda: self._tree.expandAll())
        filter_row.addWidget(self._expand_btn)

        self._collapse_btn = QPushButton("Collapse All")
        self._collapse_btn.setFixedHeight(30)
        self._collapse_btn.clicked.connect(lambda: self._tree.collapseAll())
        filter_row.addWidget(self._collapse_btn)

        main_layout.addLayout(filter_row)

        # 3. Main Splitter: Tree + Inspector Card
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Hierarchical Tree
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(4)

        tree_header = QLabel("Hierarchical Destination Structure:")
        tree_header.setStyleSheet("font-weight: bold; color: #1e293b;")
        tree_layout.addWidget(tree_header)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Folder / File", "Items / Size", "Document Type", "Confidence"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setAnimated(True)
        self._tree.setStyleSheet(
            "QTreeWidget { border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; }"
            "QTreeWidget::item { padding: 4px; }"
            "QTreeWidget::item:selected { background-color: #e0f2fe; color: #0369a1; }"
        )
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.currentItemChanged.connect(self._on_tree_selection_changed)

        tree_layout.addWidget(self._tree)
        splitter.addWidget(tree_container)

        # Right: Detail Inspector Card
        self._inspector_card = self._create_inspector_card()
        splitter.addWidget(self._inspector_card)

        # Give 65% space to tree, 35% to inspector
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)

        main_layout.addWidget(splitter, 1)

        # 4. Bottom Buttons
        bottom_row = QHBoxLayout()

        help_label = QLabel(
            "💡 Click on any file in the tree to inspect its classification reasoning and full paths."
        )
        help_label.setStyleSheet("color: #64748b; font-size: 11px;")
        bottom_row.addWidget(help_label)

        bottom_row.addStretch()

        close_btn = QPushButton("Close Preview")
        close_btn.setFixedHeight(34)
        close_btn.clicked.connect(self.reject)
        bottom_row.addWidget(close_btn)

        if self._documents:
            self._confirm_btn = QPushButton("⚡  Confirm & Organize Now")
            self._confirm_btn.setFixedHeight(34)
            self._confirm_btn.setStyleSheet(
                "QPushButton { background-color: #16a34a; color: white; font-weight: bold; "
                "border-radius: 4px; padding: 0 18px; }"
                "QPushButton:hover { background-color: #15803d; }"
            )
            self._confirm_btn.clicked.connect(self._on_confirm_clicked)
            bottom_row.addWidget(self._confirm_btn)

        main_layout.addLayout(bottom_row)

    def _create_inspector_card(self) -> QWidget:
        """Create the right-hand side document detail inspector card."""
        card = QFrame()
        card.setMinimumWidth(320)
        card.setStyleSheet(
            "QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; "
            "border-radius: 8px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        card_title = QLabel("📄 Document Inspector")
        card_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        card_title.setStyleSheet("color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;")
        layout.addWidget(card_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        # Filename
        self._card_filename = QLabel("Select an item on the left")
        self._card_filename.setWordWrap(True)
        self._card_filename.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self._card_filename.setStyleSheet("color: #1e293b;")
        scroll_layout.addWidget(self._card_filename)

        # Classification badges
        badges_row = QHBoxLayout()
        self._card_doctype_badge = QLabel("")
        self._card_doctype_badge.setStyleSheet(
            "background-color: #f1f5f9; color: #334155; font-size: 11px; "
            "padding: 3px 8px; border-radius: 4px; font-weight: bold;"
        )
        badges_row.addWidget(self._card_doctype_badge)

        self._card_conf_badge = QLabel("")
        self._card_conf_badge.setStyleSheet(
            "background-color: #dcfce7; color: #166534; font-size: 11px; "
            "padding: 3px 8px; border-radius: 4px; font-weight: bold;"
        )
        badges_row.addWidget(self._card_conf_badge)
        badges_row.addStretch()
        scroll_layout.addLayout(badges_row)

        # Confidence Bar
        self._card_conf_bar = QProgressBar()
        self._card_conf_bar.setFixedHeight(12)
        self._card_conf_bar.setTextVisible(False)
        self._card_conf_bar.setValue(0)
        self._card_conf_bar.setStyleSheet(
            "QProgressBar { background-color: #f1f5f9; border-radius: 6px; } "
            "QProgressBar::chunk { background-color: #16a34a; border-radius: 6px; }"
        )
        scroll_layout.addWidget(self._card_conf_bar)

        # Path mapping: FROM -> TO
        scroll_layout.addSpacing(6)
        path_box = QFrame()
        path_box.setStyleSheet(
            "QFrame { background-color: #f8fafc; border: 1px dashed #cbd5e1; "
            "border-radius: 6px; padding: 8px; }"
        )
        path_layout = QVBoxLayout(path_box)
        path_layout.setSpacing(4)

        from_label = QLabel("<b>ORIGIN (Current):</b>")
        from_label.setStyleSheet("color: #64748b; font-size: 10px;")
        path_layout.addWidget(from_label)

        self._card_origin_path = QLabel("—")
        self._card_origin_path.setWordWrap(True)
        self._card_origin_path.setStyleSheet("font-family: Consolas; font-size: 11px; color: #334155;")
        path_layout.addWidget(self._card_origin_path)

        arrow_label = QLabel("⬇  relocating to")
        arrow_label.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        path_layout.addWidget(arrow_label)

        to_label = QLabel("<b>DESTINATION:</b>")
        to_label.setStyleSheet("color: #15803d; font-size: 10px;")
        path_layout.addWidget(to_label)

        self._card_dest_path = QLabel("—")
        self._card_dest_path.setWordWrap(True)
        self._card_dest_path.setStyleSheet("font-family: Consolas; font-size: 11px; color: #166534; font-weight: bold;")
        path_layout.addWidget(self._card_dest_path)

        scroll_layout.addWidget(path_box)

        # Metadata Signals
        scroll_layout.addSpacing(6)
        signals_title = QLabel("<b>Document Signals & Evidence:</b>")
        signals_title.setStyleSheet("color: #334155; font-size: 11px;")
        scroll_layout.addWidget(signals_title)

        self._card_signals = QLabel("—")
        self._card_signals.setWordWrap(True)
        self._card_signals.setStyleSheet("color: #475569; font-size: 11px; line-height: 1.4;")
        scroll_layout.addWidget(self._card_signals)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        return card

    # ------------------------------------------------------------------
    # Tree Population & Filtering
    # ------------------------------------------------------------------

    def _populate_tree(self) -> None:
        """Group documents by Category -> Subcategory -> File and build tree."""
        self._tree.clear()

        # Grouping: category -> subcategory -> list[PDFDocument]
        tree_data: dict[str, dict[str, list[PDFDocument]]] = {}

        for doc in self._documents:
            cat = doc.classification.category if doc.classification else "Uncategorized"
            subcat = doc.classification.subcategory if doc.classification else "General"

            if cat not in tree_data:
                tree_data[cat] = {}
            if subcat not in tree_data[cat]:
                tree_data[cat][subcat] = []
            tree_data[cat][subcat].append(doc)

        for cat, subcats in sorted(tree_data.items()):
            cat_count = sum(len(docs) for docs in subcats.values())
            cat_item = QTreeWidgetItem(self._tree)
            cat_item.setText(0, f"📁  {cat}")
            cat_item.setText(1, f"[{cat_count} file{'s' if cat_count > 1 else ''}]")
            cat_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            cat_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "name": cat, "count": cat_count})

            for subcat, docs in sorted(subcats.items()):
                subcat_item = QTreeWidgetItem(cat_item)
                subcat_item.setText(0, f"📂  {subcat}")
                subcat_item.setText(1, f"[{len(docs)} file{'s' if len(docs) > 1 else ''}]")
                subcat_item.setFont(0, QFont("Arial", 9, QFont.Weight.DemiBold))
                subcat_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "subcategory",
                    "category": cat,
                    "name": subcat,
                    "count": len(docs),
                })

                for doc in sorted(docs, key=lambda d: d.file_info.filename.lower()):
                    file_item = QTreeWidgetItem(subcat_item)
                    file_item.setText(0, f"📄  {doc.file_info.filename}")

                    # Size
                    size_kb = doc.file_info.size_bytes / 1024
                    size_str = f"{size_kb / 1024:.1f} MB" if size_kb >= 1024 else f"{size_kb:.0f} KB"
                    file_item.setText(1, size_str)

                    # Doc Type
                    doctype = doc.classification.document_type if doc.classification else "Unknown"
                    file_item.setText(2, doctype)

                    # Confidence
                    conf = doc.classification.confidence if doc.classification else 0.0
                    conf_pct = f"{conf:.0%}"
                    file_item.setText(3, conf_pct)
                    file_item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)

                    # Color coding for confidence
                    if conf >= 0.75:
                        file_item.setForeground(3, QColor("#16a34a"))
                    elif conf >= 0.50:
                        file_item.setForeground(3, QColor("#ca8a04"))
                    else:
                        file_item.setForeground(3, QColor("#dc2626"))

                    file_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "document": doc})

        self._tree.expandAll()

    def _on_search_changed(self, text: str) -> None:
        """Dynamically filter the tree items based on search query."""
        query = text.strip().lower()

        for cat_idx in range(self._tree.topLevelItemCount()):
            cat_item = self._tree.topLevelItem(cat_idx)
            cat_matched = False

            for subcat_idx in range(cat_item.childCount()):
                subcat_item = cat_item.child(subcat_idx)
                subcat_matched = False

                for file_idx in range(subcat_item.childCount()):
                    file_item = subcat_item.child(file_idx)
                    filename = file_item.text(0).lower()
                    doctype = file_item.text(2).lower()

                    matches = (
                        not query
                        or query in filename
                        or query in doctype
                        or query in cat_item.text(0).lower()
                        or query in subcat_item.text(0).lower()
                    )
                    file_item.setHidden(not matches)
                    if matches:
                        subcat_matched = True

                subcat_item.setHidden(not subcat_matched and query != "")
                if subcat_matched or (query and query in subcat_item.text(0).lower()):
                    cat_matched = True

            cat_item.setHidden(not cat_matched and query != "")
            if cat_matched:
                cat_item.setExpanded(True)

    def _on_tree_selection_changed(
        self,
        current: Optional[QTreeWidgetItem],
        previous: Optional[QTreeWidgetItem],
    ) -> None:
        """Update inspector card when tree selection changes."""
        if not current:
            return

        data = current.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type")

        if item_type == "file":
            doc: PDFDocument = data["document"]
            self._update_inspector_for_document(doc)
        elif item_type == "category":
            cat_name = data.get("name", "")
            count = data.get("count", 0)
            self._card_filename.setText(f"📁 Category: {cat_name}")
            self._card_doctype_badge.setText(f"{count} files total")
            self._card_conf_badge.setText("Category Folder")
            self._card_conf_bar.setValue(100)
            self._card_origin_path.setText("—")
            self._card_dest_path.setText(str(self._destination_root / cat_name))
            self._card_signals.setText(
                f"Top-level organizational directory containing {count} document(s) divided into specialized subcategories."
            )
        elif item_type == "subcategory":
            cat_name = data.get("category", "")
            subcat_name = data.get("name", "")
            count = data.get("count", 0)
            self._card_filename.setText(f"📂 Subcategory: {subcat_name}")
            self._card_doctype_badge.setText(f"{count} file(s)")
            self._card_conf_badge.setText(f"Under: {cat_name}")
            self._card_conf_bar.setValue(100)
            self._card_origin_path.setText("—")
            self._card_dest_path.setText(str(self._destination_root / cat_name / subcat_name))
            self._card_signals.setText(
                f"Subfolder for {subcat_name} documents within the {cat_name} domain."
            )

    def _update_inspector_for_document(self, doc: PDFDocument) -> None:
        """Fill inspector card with full metadata, confidence, and paths."""
        self._card_filename.setText(doc.file_info.filename)

        cls = doc.classification
        doctype = cls.document_type if cls else "Unknown Document"
        conf = cls.confidence if cls else 0.0

        self._card_doctype_badge.setText(f"Type: {doctype}")
        self._card_conf_badge.setText(f"Confidence: {conf:.0%}")

        # Bar color
        self._card_conf_bar.setValue(int(conf * 100))
        if conf >= 0.75:
            bar_color = "#16a34a"
            self._card_conf_badge.setStyleSheet(
                "background-color: #dcfce7; color: #166534; font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: bold;"
            )
        elif conf >= 0.50:
            bar_color = "#ca8a04"
            self._card_conf_badge.setStyleSheet(
                "background-color: #fef9c3; color: #854d0e; font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: bold;"
            )
        else:
            bar_color = "#dc2626"
            self._card_conf_badge.setStyleSheet(
                "background-color: #fee2e2; color: #991b1b; font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: bold;"
            )

        self._card_conf_bar.setStyleSheet(
            f"QProgressBar {{ background-color: #f1f5f9; border-radius: 6px; }} "
            f"QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 6px; }}"
        )

        # Paths
        self._card_origin_path.setText(str(doc.file_info.path))
        self._card_dest_path.setText(str(doc.suggested_path) if doc.suggested_path else "Not planned yet")

        # Evidence / Signals
        signals: list[str] = []
        if doc.metadata:
            if doc.metadata.title:
                signals.append(f"<b>Title:</b> {doc.metadata.title}")
            if doc.metadata.author:
                signals.append(f"<b>Author:</b> {doc.metadata.author}")
            if doc.metadata.creation_date:
                signals.append(f"<b>Created:</b> {doc.metadata.creation_date[:10]}")
            signals.append(f"<b>Pages:</b> {doc.metadata.page_count}")

        if cls:
            # Section 21: Context & Relationship Signals
            if cls.scope:
                signals.append(f"<b>Context (Scope):</b> 🏷️ {cls.scope}")
            if cls.work_context:
                signals.append(f"<b>Work Context:</b> {cls.work_context}")
            if cls.organization:
                signals.append(f"<b>Organization:</b> 🏢 {cls.organization}")
            if cls.role:
                signals.append(f"<b>Inferred Role:</b> 👤 {cls.role}")
            if cls.project:
                signals.append(f"<b>Project:</b> 🚀 {cls.project}")

            if cls.extracted_signals:
                sig_details = []
                for k, v in cls.extracted_signals.items():
                    if k in ("organization_match", "project_match", "role_match", "temporal_consistency", "domain_similarity"):
                        sig_details.append(f"{k.replace('_', ' ').capitalize()} (+{v:.2f})")
                if sig_details:
                    signals.append(f"<b>Evidence Weights:</b> {', '.join(sig_details)}")

                matched = cls.extracted_signals.get("matched_keywords", [])
                if matched:
                    signals.append(f"<b>Matched Keywords:</b> {', '.join(matched[:6])}")
                markers = cls.extracted_signals.get("strong_markers", [])
                if markers:
                    signals.append(f"<b>Strong Markers:</b> {', '.join(markers[:4])}")
                domain = cls.extracted_signals.get("user_domain_boosted")
                if domain:
                    signals.append(f"<b>Personalized Domain:</b> ⭐ {domain}")

            if cls.reasoning:
                signals.append(f"<b>Reasoning:</b> {cls.reasoning}")

        self._card_signals.setText("<br>".join(signals) if signals else "No extra metadata signals detected.")

    def _on_confirm_clicked(self) -> None:
        """Handle 'Confirm & Organize' button click."""
        self.accept()
        if self._on_confirm_organize:
            self._on_confirm_organize()
