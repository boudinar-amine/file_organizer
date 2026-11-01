"""Right-side Document Inspector panel (Section 6).

Displays clean classification controls, human-readable evidence cards,
metadata fields, and safe path preview without raw debug dictionaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.database.models import FileStatus, PDFDocument
from app.gui.widgets.confidence_badge import ConfidenceBadge


class DocumentInspectorWidget(QWidget):
    """Right-side inspector showing classification details and human-readable evidence."""

    documentUpdated = Signal(object)  # Emits modified PDFDocument

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_doc: Optional[PDFDocument] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Scroll area for compact height adaptability
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Header (Filename & icon)
        header_row = QHBoxLayout()
        icon_lbl = QLabel("📄")
        icon_lbl.setStyleSheet("font-size: 20px;")
        header_row.addWidget(icon_lbl)

        self._filename_lbl = QLabel("No document selected")
        fn_font = QFont()
        fn_font.setPointSize(13)
        fn_font.setBold(True)
        self._filename_lbl.setFont(fn_font)
        self._filename_lbl.setWordWrap(True)
        header_row.addWidget(self._filename_lbl, 1)
        layout.addLayout(header_row)

        # 2. Classification Card
        classif_card = QFrame()
        classif_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        classif_layout = QVBoxLayout(classif_card)
        classif_layout.setSpacing(8)

        card_title = QLabel("Classification")
        card_title.setStyleSheet("font-weight: 700; font-size: 12px; color: #f8fafc;")
        classif_layout.addWidget(card_title)

        # Category
        cat_row = QHBoxLayout()
        cat_lbl = QLabel("Category:")
        cat_lbl.setFixedWidth(85)
        cat_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self._category_combo = QComboBox()
        self._category_combo.setEditable(True)
        self._category_combo.addItems([
            "Public Health", "Research", "Insurtech", "Sécurité Sanitaire",
            "Administration", "Legal", "Financial", "Personal", "Other"
        ])
        cat_row.addWidget(cat_lbl)
        cat_row.addWidget(self._category_combo, 1)
        classif_layout.addLayout(cat_row)

        # Subcategory
        subcat_row = QHBoxLayout()
        subcat_lbl = QLabel("Subcategory:")
        subcat_lbl.setFixedWidth(85)
        subcat_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self._subcategory_combo = QComboBox()
        self._subcategory_combo.setEditable(True)
        subcat_row.addWidget(subcat_lbl)
        subcat_row.addWidget(self._subcategory_combo, 1)
        classif_layout.addLayout(subcat_row)

        # Document Type
        type_row = QHBoxLayout()
        type_lbl = QLabel("Doc Type:")
        type_lbl.setFixedWidth(85)
        type_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self._doctype_combo = QComboBox()
        self._doctype_combo.setEditable(True)
        self._doctype_combo.addItems([
            "Report", "Scientific Article", "Invoice", "Meeting Minutes",
            "Contract", "Clinical Evaluation", "Regulation", "Strategy"
        ])
        type_row.addWidget(type_lbl)
        type_row.addWidget(self._doctype_combo, 1)
        classif_layout.addLayout(type_row)

        # Organization
        org_row = QHBoxLayout()
        org_lbl = QLabel("Organization:")
        org_lbl.setFixedWidth(85)
        org_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self._org_edit = QLineEdit()
        self._org_edit.setPlaceholderText("e.g. World Health Organization")
        org_row.addWidget(org_lbl)
        org_row.addWidget(self._org_edit, 1)
        classif_layout.addLayout(org_row)

        # Confidence Badge row
        conf_row = QHBoxLayout()
        conf_title = QLabel("Confidence:")
        conf_title.setStyleSheet("color: #94a3b8; font-size: 11px;")
        conf_row.addWidget(conf_title)
        self._confidence_badge = ConfidenceBadge(0.0)
        conf_row.addWidget(self._confidence_badge)
        conf_row.addStretch()
        classif_layout.addLayout(conf_row)

        # Apply changes button
        self._apply_btn = QPushButton("Save Classification Changes")
        self._apply_btn.setProperty("class", "primary")
        self._apply_btn.clicked.connect(self._on_save_changes)
        classif_layout.addWidget(self._apply_btn)

        layout.addWidget(classif_card)

        # 3. Why this category? (Human-Readable Evidence Cards)
        why_card = QFrame()
        why_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        why_layout = QVBoxLayout(why_card)
        why_layout.setSpacing(6)

        why_title = QLabel("Why was this classified here?")
        why_title.setStyleSheet("font-weight: 700; font-size: 12px; color: #f8fafc;")
        why_layout.addWidget(why_title)

        self._evidence_layout = QVBoxLayout()
        self._evidence_layout.setSpacing(4)
        why_layout.addLayout(self._evidence_layout)
        layout.addWidget(why_card)

        # 4. File Information
        info_card = QFrame()
        info_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(4)

        info_title = QLabel("File Information")
        info_title.setStyleSheet("font-weight: 700; font-size: 12px; color: #f8fafc;")
        info_layout.addWidget(info_title)

        self._meta_title_lbl = QLabel("Title: —")
        self._meta_author_lbl = QLabel("Author: —")
        self._meta_pages_lbl = QLabel("Pages: —")
        self._meta_size_lbl = QLabel("Size: —")
        for lbl in (self._meta_title_lbl, self._meta_author_lbl, self._meta_pages_lbl, self._meta_size_lbl):
            lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
            info_layout.addWidget(lbl)
        layout.addWidget(info_card)

        # 5. Path Preview
        path_card = QFrame()
        path_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        path_layout = QVBoxLayout(path_card)
        path_layout.setSpacing(4)

        path_title = QLabel("Path Preview")
        path_title.setStyleSheet("font-weight: 700; font-size: 12px; color: #f8fafc;")
        path_layout.addWidget(path_title)

        path_layout.addWidget(QLabel("<b style='color:#94a3b8; font-size:10px;'>FROM:</b>"))
        self._from_path_lbl = QLabel("—")
        self._from_path_lbl.setWordWrap(True)
        self._from_path_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        path_layout.addWidget(self._from_path_lbl)

        path_layout.addWidget(QLabel("<b style='color:#4ade80; font-size:10px;'>TO:</b>"))
        self._to_path_edit = QLineEdit()
        self._to_path_edit.setStyleSheet("font-size: 11px;")
        path_layout.addWidget(self._to_path_edit)

        layout.addWidget(path_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def set_document(self, doc: Optional[PDFDocument]) -> None:
        """Inspect a specific PDFDocument."""
        self._current_doc = doc
        if doc is None:
            self._filename_lbl.setText("No document selected")
            self._from_path_lbl.setText("—")
            self._to_path_edit.setText("")
            self._confidence_badge.update_confidence(0.0)
            self._clear_evidence()
            return

        self._filename_lbl.setText(doc.file_info.filename)
        self._from_path_lbl.setText(str(doc.file_info.path))
        self._to_path_edit.setText(str(doc.suggested_path) if doc.suggested_path else "")

        if doc.classification:
            self._category_combo.setCurrentText(doc.classification.category)
            self._subcategory_combo.setCurrentText(doc.classification.subcategory)
            self._doctype_combo.setCurrentText(doc.classification.document_type)
            self._org_edit.setText(doc.classification.organization or "")
            self._confidence_badge.update_confidence(doc.classification.confidence)
            self._render_evidence(doc)
        else:
            self._confidence_badge.update_confidence(0.0)
            self._clear_evidence()

        # Metadata
        if doc.metadata:
            self._meta_title_lbl.setText(f"Title: {doc.metadata.title or '—'}")
            self._meta_author_lbl.setText(f"Author: {doc.metadata.author or '—'}")
            self._meta_pages_lbl.setText(f"Pages: {doc.metadata.page_count}")
        self._meta_size_lbl.setText(f"Size: {doc.file_info.size_bytes // 1024} KB")

    def _clear_evidence(self) -> None:
        while self._evidence_layout.count():
            item = self._evidence_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_evidence(self, doc: PDFDocument) -> None:
        self._clear_evidence()
        if not doc.classification:
            return

        signals = doc.classification.extracted_signals or {}
        reason = doc.classification.reason or ""

        # Human-readable cards
        cards = []
        if doc.classification.document_type:
            cards.append(("Document Structure", f"Identified as {doc.classification.document_type}"))
        if doc.classification.organization:
            cards.append(("Organization Entity", doc.classification.organization))
        if signals.get("domain_score"):
            cards.append(("Domain Semantic Score", f"+{signals['domain_score']:.1f} matched keywords"))
        if reason:
            cards.append(("Classifier Reasoning", reason))

        if not cards:
            cards.append(("Heuristic Match", "Matched general content and document context"))

        for title, detail in cards:
            c = QFrame()
            c.setStyleSheet("background: #0f172a; border-left: 3px solid #3b82f6; border-radius: 4px; padding: 4px 8px;")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(2)
            t = QLabel(f"<b>{title}</b>")
            t.setStyleSheet("font-size: 11px; color: #60a5fa;")
            d = QLabel(detail)
            d.setStyleSheet("font-size: 11px; color: #cbd5e1;")
            d.setWordWrap(True)
            cl.addWidget(t)
            cl.addWidget(d)
            self._evidence_layout.addWidget(c)

    def _on_save_changes(self) -> None:
        if not self._current_doc:
            return
        if not self._current_doc.classification:
            return

        self._current_doc.classification.category = self._category_combo.currentText().strip()
        self._current_doc.classification.subcategory = self._subcategory_combo.currentText().strip()
        self._current_doc.classification.document_type = self._doctype_combo.currentText().strip()
        self._current_doc.classification.organization = self._org_edit.text().strip()
        self._current_doc.classification.confidence = 1.0  # Manual override = 100% confidence
        self._current_doc.status = FileStatus.APPROVED

        new_dest = self._to_path_edit.text().strip()
        if new_dest:
            self._current_doc.suggested_path = Path(new_dest)

        self._confidence_badge.update_confidence(1.0)
        self.documentUpdated.emit(self._current_doc)
