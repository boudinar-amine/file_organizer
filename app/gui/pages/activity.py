"""Activity & Undo operation history page (Section 11).

Provides readable operation logs with one-click reversible Undo.
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
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.organizer.undo_manager import UndoManager


class ActivityCard(QFrame):
    """Card representing an individual file organization transaction."""

    undoRequested = Signal(str)  # transaction_id

    def __init__(
        self,
        transaction_id: str,
        timestamp_str: str,
        mode: str,
        file_count: int,
        source: str,
        destination: str,
        is_undone: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "ActivityCard { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px; } "
            "ActivityCard:hover { border-color: #475569; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header: Date / Time + Status
        top_row = QHBoxLayout()
        time_lbl = QLabel(f"<b>Organized Documents</b> • {timestamp_str}")
        time_lbl.setStyleSheet("font-size: 13px; color: #f8fafc;")
        top_row.addWidget(time_lbl)
        top_row.addStretch()

        if is_undone:
            badge = QLabel("Undone")
            badge.setStyleSheet(
                "background-color: #334155; color: #94a3b8; border: 1px solid #475569; "
                "border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
            )
            top_row.addWidget(badge)
        else:
            badge = QLabel("Completed")
            badge.setStyleSheet(
                "background-color: #064e3b; color: #86efac; border: 1px solid #059669; "
                "border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
            )
            top_row.addWidget(badge)
        layout.addLayout(top_row)

        # Details
        desc_lbl = QLabel(f"{file_count} files {mode.lower()} • {source} → {destination}")
        desc_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._undo_btn = QPushButton("↩ Undo This Operation")
        self._undo_btn.setFixedHeight(30)
        self._undo_btn.setEnabled(not is_undone)
        self._undo_btn.setStyleSheet(
            "QPushButton { background-color: #78350f; color: #fde68a; border: 1px solid #b45309; "
            "font-weight: 600; border-radius: 4px; padding: 0 14px; font-size: 12px; } "
            "QPushButton:hover { background-color: #92400e; } "
            "QPushButton:disabled { color: #64748b; border-color: #334155; background: #0f172a; }"
        )
        self._undo_btn.clicked.connect(lambda: self.undoRequested.emit(transaction_id))
        btn_row.addWidget(self._undo_btn)
        layout.addLayout(btn_row)


class ActivityPage(QWidget):
    """Activity history and safe Undo operations page."""

    undoRequested = Signal()

    def __init__(self, undo_manager: Optional[UndoManager] = None, parent=None) -> None:
        super().__init__(parent)
        self._undo_manager = undo_manager

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header
        hdr_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Activity & Undo")
        t_font = QFont()
        t_font.setPointSize(18)
        t_font.setBold(True)
        title.setFont(t_font)
        sub = QLabel("Review past document operations and safely undo any changes.")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        hdr_row.addLayout(title_box)
        hdr_row.addStretch()

        self._undo_latest_btn = QPushButton("↩  Undo Latest Operation")
        self._undo_latest_btn.setFixedHeight(36)
        self._undo_latest_btn.setProperty("class", "primary")
        self._undo_latest_btn.clicked.connect(self.undoRequested.emit)
        hdr_row.addWidget(self._undo_latest_btn)
        layout.addLayout(hdr_row)

        # Timeline list container
        self._cards_layout = QVBoxLayout()
        self._cards_layout.setSpacing(10)
        layout.addLayout(self._cards_layout)

        layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.refresh()

    @property
    def undo_btn(self) -> QPushButton:
        return self._undo_latest_btn

    def set_undo_manager(self, undo_manager: UndoManager) -> None:
        self._undo_manager = undo_manager
        self.refresh()

    def refresh(self) -> None:
        """Reload operation history cards."""
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        can_undo = self._undo_manager.can_undo() if self._undo_manager else False
        self._undo_latest_btn.setEnabled(can_undo)

        summary = self._undo_manager.get_last_batch_summary() if self._undo_manager else None
        if not summary:
            empty = QLabel("No file operations recorded yet. Your organization history will appear here.")
            empty.setStyleSheet("color: #94a3b8; font-size: 13px; padding: 20px 0;")
            self._cards_layout.addWidget(empty)
            return

        time_str = summary.get("timestamp", "Recently")
        card = ActivityCard(
            transaction_id=summary.get("batch_id", ""),
            timestamp_str=time_str,
            mode=summary.get("operation_type", "copied"),
            file_count=summary.get("count", 0),
            source="Source Folder",
            destination="Organized Folder",
            is_undone=False,
        )
        card.undoRequested.connect(self._on_undo_card_click)
        self._cards_layout.addWidget(card)

    def _on_undo_card_click(self, transaction_id: str) -> None:
        self.undoRequested.emit()
