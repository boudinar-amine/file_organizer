"""Friendly, instructive empty state placeholders for views without content."""

from __future__ import annotations

from typing import Callable, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyStateWidget(QWidget):
    """Clean empty state container guiding the user on next steps."""

    def __init__(
        self,
        icon: str,
        title: str,
        description: str,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        layout.setContentsMargins(40, 60, 40, 60)

        # Icon / Emoji
        icon_lbl = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(36)
        icon_lbl.setFont(icon_font)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        # Title
        title_lbl = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setMaximumWidth(480)
        layout.addWidget(desc_lbl)

        # Optional action button
        if action_text and action_callback:
            layout.addSpacing(6)
            btn = QPushButton(action_text)
            btn.setProperty("class", "primary")
            btn.setFixedHeight(34)
            btn.setFixedWidth(180)
            btn.clicked.connect(action_callback)
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
