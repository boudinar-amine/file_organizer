"""Search input bar with clear button and signal dispatch."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class SearchBar(QWidget):
    """Modern search input widget with an inline clear button."""

    searchChanged = Signal(str)

    def __init__(self, placeholder: str = "Search documents…", parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setClearButtonEnabled(True)
        self._input.setFixedHeight(34)
        self._input.textChanged.connect(self.searchChanged.emit)

        layout.addWidget(self._input)

    def text(self) -> str:
        return self._input.text().strip()

    def setText(self, text: str) -> None:
        self._input.setText(text)

    def clear(self) -> None:
        self._input.clear()
