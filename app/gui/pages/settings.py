"""Categorized Application Settings page (Section 19 & 21).

Provides clean tabbed configuration for General, Scanning, Classification,
File Operations, and Privacy without dense or intimidating forms.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsPage(QWidget):
    """Categorized settings interface with theme switching and safety options."""

    themeChanged = Signal(bool)  # is_dark
    configSaved = Signal(dict)

    def __init__(self, current_config: Optional[dict[str, Any]] = None, parent=None) -> None:
        super().__init__(parent)
        self._config: dict[str, Any] = current_config or {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Settings")
        t_font = QFont()
        t_font.setPointSize(18)
        t_font.setBold(True)
        title.setFont(t_font)
        sub = QLabel("Customize application preferences, appearance, and file safety defaults.")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_row.addLayout(title_box)
        top_row.addStretch()

        self._save_btn = QPushButton("Save Preferences")
        self._save_btn.setProperty("class", "primary")
        self._save_btn.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: 700; padding: 6px 20px; border-radius: 6px;"
        )
        self._save_btn.clicked.connect(self._on_save_config)
        top_row.addWidget(self._save_btn)
        layout.addLayout(top_row)

        # Tabbed categories
        tabs = QTabWidget()

        # Tab 1: General & Appearance
        gen_tab = QWidget()
        gen_layout = QVBoxLayout(gen_tab)
        gen_layout.setContentsMargins(14, 14, 14, 14)
        gen_layout.setSpacing(12)

        # Theme
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Appearance Theme:"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark Theme (Default)", "Light Theme"])
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self._theme_combo)
        theme_row.addStretch()
        gen_layout.addLayout(theme_row)

        # Default Destination
        dest_row = QHBoxLayout()
        dest_row.addWidget(QLabel("Default Destination:"))
        self._default_dest_edit = QLineEdit()
        self._default_dest_edit.setText(self._config.get("organization_root", ""))
        self._default_dest_edit.setPlaceholderText("Leave blank for Organized/ alongside source")
        dest_row.addWidget(self._default_dest_edit, 1)
        self._browse_dest_btn = QPushButton("Browse")
        self._browse_dest_btn.clicked.connect(self._on_browse_default_dest)
        dest_row.addWidget(self._browse_dest_btn)
        gen_layout.addLayout(dest_row)

        gen_layout.addStretch()
        tabs.addTab(gen_tab, "General")

        # Tab 2: Scanning & Processing
        scan_tab = QWidget()
        scan_layout = QVBoxLayout(scan_tab)
        scan_layout.setContentsMargins(14, 14, 14, 14)
        scan_layout.setSpacing(12)

        pages_row = QHBoxLayout()
        pages_row.addWidget(QLabel("Pages to analyze per PDF:"))
        self._pages_spin = QSpinBox()
        self._pages_spin.setRange(1, 20)
        self._pages_spin.setValue(self._config.get("max_pages_to_analyze", 2))
        pages_row.addWidget(self._pages_spin)
        pages_row.addStretch()
        scan_layout.addLayout(pages_row)

        self._check_subfolders = QCheckBox("Scan subfolders by default")
        self._check_subfolders.setChecked(self._config.get("include_subfolders", True))
        scan_layout.addWidget(self._check_subfolders)

        scan_layout.addStretch()
        tabs.addTab(scan_tab, "Scanning")

        # Tab 3: File Operations & Safety
        ops_tab = QWidget()
        ops_layout = QVBoxLayout(ops_tab)
        ops_layout.setContentsMargins(14, 14, 14, 14)
        ops_layout.setSpacing(12)

        self._default_test_mode = QCheckBox("Safe Test Mode by default (Copy instead of Move)")
        self._default_test_mode.setChecked(self._config.get("test_mode", True))
        ops_layout.addWidget(self._default_test_mode)

        ops_layout.addStretch()
        tabs.addTab(ops_tab, "File Safety")

        layout.addWidget(tabs)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _on_theme_changed(self, index: int) -> None:
        self.themeChanged.emit(index == 0)

    def _on_browse_default_dest(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Default Destination Folder")
        if folder:
            self._default_dest_edit.setText(folder)

    def _on_save_config(self) -> None:
        self._config["test_mode"] = self._default_test_mode.isChecked()
        self._config["include_subfolders"] = self._check_subfolders.isChecked()
        self._config["max_pages_to_analyze"] = self._pages_spin.value()
        self._config["organization_root"] = self._default_dest_edit.text().strip()
        self.configSaved.emit(self._config)
        QMessageBox.information(self, "Settings Saved", "Preferences have been updated.")
