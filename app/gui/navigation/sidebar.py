"""Persistent modern left navigation sidebar (Section 2).

Provides categorized sections (ORGANIZE, KNOWLEDGE, SYSTEM) with subtle accent
highlights, clean icons, collapsible width, and privacy/offline indicators.
"""

from __future__ import annotations

from typing import Callable, Optional
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


class NavButton(QPushButton):
    """Subtly styled sidebar navigation item."""

    def __init__(self, key: str, label: str, icon_str: str, parent=None) -> None:
        super().__init__(f"  {icon_str}  {label}", parent)
        self.key = key
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active = False
        self._update_style()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()

    def _update_style(self) -> None:
        if self._active:
            self.setStyleSheet(
                "QPushButton { text-align: left; padding-left: 12px; font-weight: 600; "
                "font-size: 13px; color: #60a5fa; background-color: #1e3a8a; "
                "border: none; border-radius: 6px; } "
            )
        else:
            self.setStyleSheet(
                "QPushButton { text-align: left; padding-left: 12px; font-weight: 500; "
                "font-size: 13px; color: #94a3b8; background-color: transparent; "
                "border: none; border-radius: 6px; } "
                "QPushButton:hover { background-color: #334155; color: #f8fafc; }"
            )


class SidebarWidget(QWidget):
    """Persistent modern navigation sidebar with status footer."""

    pageSelected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setStyleSheet("background-color: #0f172a; border-right: 1px solid #1e293b;")
        self._buttons: dict[str, NavButton] = {}
        self._current_page = "dashboard"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(12)

        # App Brand Header
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        logo_lbl = QLabel("📑")
        logo_font = QFont()
        logo_font.setPointSize(18)
        logo_lbl.setFont(logo_font)
        header_row.addWidget(logo_lbl)

        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(0)
        app_name = QLabel("PDF Organizer")
        name_font = QFont()
        name_font.setPointSize(14)
        name_font.setBold(True)
        app_name.setFont(name_font)
        app_name.setStyleSheet("color: #f8fafc;")
        app_sub = QLabel("Local & Intelligent")
        app_sub.setStyleSheet("color: #64748b; font-size: 11px;")
        brand_layout.addWidget(app_name)
        brand_layout.addWidget(app_sub)
        header_row.addLayout(brand_layout)
        header_row.addStretch()
        layout.addLayout(header_row)

        layout.addSpacing(6)

        # Nav Sections
        self._nav_container = QVBoxLayout()
        self._nav_container.setSpacing(2)

        self._add_section_header("ORGANIZE")
        self._add_nav_item("dashboard", "Dashboard", "📊")
        self._add_nav_item("scan", "Scan Folder", "🔍")
        self._add_nav_item("review", "Review Workspace", "📋")
        self._add_nav_item("preview", "Organized Files", "📁")

        self._nav_container.addSpacing(10)
        self._add_section_header("KNOWLEDGE")
        self._add_nav_item("profile", "User Profile", "👤")
        self._add_nav_item("rules", "Classification Rules", "📜")

        self._nav_container.addSpacing(10)
        self._add_section_header("SYSTEM")
        self._add_nav_item("activity", "Activity & Undo", "↩️")
        self._add_nav_item("local_ai", "Local AI Models", "🤖")
        self._add_nav_item("settings", "Settings", "⚙️")

        layout.addLayout(self._nav_container)
        layout.addStretch()

        # Bottom Safety / Status Footer
        footer_card = QFrame()
        footer_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        footer_layout = QVBoxLayout(footer_card)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(4)

        self._privacy_lbl = QLabel("● Offline")
        self._privacy_lbl.setStyleSheet("color: #4ade80; font-weight: 700; font-size: 11px;")
        self._privacy_sub = QLabel("Files never leave this PC")
        self._privacy_sub.setStyleSheet("color: #94a3b8; font-size: 10px;")

        self._version_lbl = QLabel("Version 1.2.0 • Local AI")
        self._version_lbl.setStyleSheet("color: #64748b; font-size: 10px;")

        footer_layout.addWidget(self._privacy_lbl)
        footer_layout.addWidget(self._privacy_sub)
        footer_layout.addWidget(self._version_lbl)
        layout.addWidget(footer_card)

        # Set initial active page
        self.select_page("dashboard")

    def _add_section_header(self, title: str) -> None:
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; padding-left: 12px; margin-top: 6px; margin-bottom: 2px;")
        self._nav_container.addWidget(lbl)

    def _add_nav_item(self, key: str, label: str, icon_str: str) -> None:
        btn = NavButton(key, label, icon_str)
        btn.clicked.connect(lambda: self.select_page(key))
        self._buttons[key] = btn
        self._nav_container.addWidget(btn)

    def select_page(self, key: str) -> None:
        """Select a navigation page and notify listeners."""
        if key not in self._buttons:
            return
        for k, btn in self._buttons.items():
            btn.set_active(k == key)
        self._current_page = key
        self.pageSelected.emit(key)

    def set_ai_status(self, connected: bool, details: str = "") -> None:
        """Update the sidebar AI indicator."""
        if connected:
            self._version_lbl.setText(f"AI: Ready ({details[:12]})")
        else:
            self._version_lbl.setText("AI: Rules + BM25")
