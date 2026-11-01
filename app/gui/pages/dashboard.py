"""Dashboard home screen page (Section 3).

Provides compact statistics, a prominent folder drop zone, and recent activity.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.gui.widgets.folder_drop_zone import FolderDropZone


class DashboardPage(QWidget):
    """Home dashboard screen with key metrics and quick folder drop."""

    folderSelected = Signal(Path)
    resumeReviewRequested = Signal()
    viewHistoryRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # 1. Greeting Header
        now = datetime.datetime.now()
        greeting = "Good morning" if now.hour < 12 else ("Good afternoon" if now.hour < 18 else "Good evening")
        header_lbl = QLabel(f"{greeting} — your document workspace is ready")
        h_font = QFont()
        h_font.setPointSize(18)
        h_font.setBold(True)
        header_lbl.setFont(h_font)
        header_lbl.setStyleSheet("color: #f8fafc;")
        layout.addWidget(header_lbl)

        # 2. Compact Statistics Cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._stat_discovered = self._create_stat_card("PDFs Discovered", "0", "Total files scanned")
        self._stat_classified = self._create_stat_card("Classified", "0", "High confidence", "#4ade80")
        self._stat_review = self._create_stat_card("Needs Review", "0", "Requires attention", "#fbbf24")
        self._stat_scanned = self._create_stat_card("OCR Required", "0", "Scanned pages", "#94a3b8")

        stats_row.addWidget(self._stat_discovered)
        stats_row.addWidget(self._stat_classified)
        stats_row.addWidget(self._stat_review)
        stats_row.addWidget(self._stat_scanned)
        layout.addLayout(stats_row)

        # Resume review banner (visible only when unreviewed files exist)
        self._resume_frame = QFrame()
        self._resume_frame.setStyleSheet("background-color: #172554; border: 1px solid #1e40af; border-radius: 8px; padding: 12px;")
        res_layout = QHBoxLayout(self._resume_frame)
        res_layout.setContentsMargins(0, 0, 0, 0)
        self._resume_text = QLabel("📋 You have analyzed documents ready for review.")
        self._resume_text.setStyleSheet("color: #93c5fd; font-weight: 500;")
        self._resume_btn = QPushButton("Resume Review")
        self._resume_btn.setProperty("class", "primary")
        self._resume_btn.clicked.connect(self.resumeReviewRequested.emit)
        res_layout.addWidget(self._resume_text, 1)
        res_layout.addWidget(self._resume_btn)
        self._resume_frame.hide()
        layout.addWidget(self._resume_frame)

        # 3. Quick Action Drop Zone
        drop_section = QVBoxLayout()
        drop_section.setSpacing(8)
        sec_title = QLabel("Quick Action")
        sec_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #cbd5e1;")
        drop_section.addWidget(sec_title)

        self._drop_zone = FolderDropZone()
        self._drop_zone.folderSelected.connect(self.folderSelected.emit)
        drop_section.addWidget(self._drop_zone)
        layout.addLayout(drop_section)

        # 4. Recent Folders & Operations
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        # Recent folder card
        recent_card = QFrame()
        recent_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;")
        rec_layout = QVBoxLayout(recent_card)
        rec_layout.setSpacing(8)
        rec_title = QLabel("Recent Folder")
        rec_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #cbd5e1;")
        rec_layout.addWidget(rec_title)

        self._recent_path_lbl = QLabel("No recent folders scanned.")
        self._recent_path_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self._recent_path_lbl.setWordWrap(True)
        rec_layout.addWidget(self._recent_path_lbl)
        rec_layout.addStretch()

        # Last operation card
        op_card = QFrame()
        op_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;")
        op_layout = QVBoxLayout(op_card)
        op_layout.setSpacing(8)
        op_title = QLabel("Recent Organization Activity")
        op_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #cbd5e1;")
        op_layout.addWidget(op_title)

        self._op_history_lbl = QLabel("No file operations recorded yet.")
        self._op_history_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self._op_history_lbl.setWordWrap(True)
        op_layout.addWidget(self._op_history_lbl)
        op_layout.addStretch()

        bottom_row.addWidget(recent_card, 1)
        bottom_row.addWidget(op_card, 1)
        layout.addLayout(bottom_row)

        layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_stat_card(self, title: str, value: str, subtitle: str, color: Optional[str] = None) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px;")
        card.setFixedHeight(84)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(2)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        c_layout.addWidget(t_lbl)

        v_lbl = QLabel(value)
        v_font = QFont()
        v_font.setPointSize(18)
        v_font.setBold(True)
        v_lbl.setFont(v_font)
        if color:
            v_lbl.setStyleSheet(f"color: {color};")
        else:
            v_lbl.setStyleSheet("color: #f8fafc;")
        c_layout.addWidget(v_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet("color: #64748b; font-size: 10px;")
        c_layout.addWidget(sub_lbl)
        return card

    def update_metrics(
        self,
        discovered: int,
        classified: int,
        needs_review: int,
        ocr_required: int,
        last_folder: str = "",
        last_activity: str = "",
    ) -> None:
        """Update dashboard compact counters."""
        self._stat_discovered.findChildren(QLabel)[1].setText(str(discovered))
        self._stat_classified.findChildren(QLabel)[1].setText(str(classified))
        self._stat_review.findChildren(QLabel)[1].setText(str(needs_review))
        self._stat_scanned.findChildren(QLabel)[1].setText(str(ocr_required))

        if last_folder:
            self._recent_path_lbl.setText(last_folder)
        if last_activity:
            self._op_history_lbl.setText(last_activity)

        if needs_review > 0 or classified > 0:
            self._resume_text.setText(f"📋 You have {classified + needs_review} analyzed documents ready for review.")
            self._resume_frame.show()
        else:
            self._resume_frame.hide()
