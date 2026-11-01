"""Visual confidence badges and status indicators.

Adheres to Section 5 & Section 13 requirements:
- Displays explicit text ('92% High') rather than only color.
- High = subtle green, Medium = amber, Low = muted red, Manual = blue.
- Never relies solely on color for accessibility.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class ConfidenceBadge(QLabel):
    """Badge showing textual percentage and level with subtle accessible styling."""

    def __init__(self, confidence: float, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(24)
        self.update_confidence(confidence)

    def update_confidence(self, confidence: float) -> None:
        pct = int(round(confidence * 100))
        if pct >= 80:
            level = "High"
            bg = "#064e3b"
            fg = "#6ee7b7"
            border = "#047857"
        elif pct >= 60:
            level = "Medium"
            bg = "#451a03"
            fg = "#fcd34d"
            border = "#78350f"
        elif pct > 0:
            level = "Low"
            bg = "#450a0a"
            fg = "#fca5a5"
            border = "#7f1d1d"
        else:
            level = "Manual"
            bg = "#172554"
            fg = "#93c5fd"
            border = "#1e40af"

        self.setText(f"{pct}% {level}")
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            f"border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
        )


class StatusBadge(QLabel):
    """Status pill for files (Ready, Needs Review, OCR required, Copied, Moved)."""

    def __init__(self, status_text: str, badge_type: str = "info", parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(24)
        self.set_status(status_text, badge_type)

    def set_status(self, text: str, badge_type: str = "info") -> None:
        styles = {
            "success": ("#064e3b", "#6ee7b7", "#047857"),
            "warning": ("#451a03", "#fcd34d", "#78350f"),
            "danger": ("#450a0a", "#fca5a5", "#7f1d1d"),
            "info": ("#172554", "#93c5fd", "#1e40af"),
            "neutral": ("#1e293b", "#94a3b8", "#334155"),
        }
        bg, fg, border = styles.get(badge_type, styles["neutral"])
        self.setText(text)
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            f"border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
        )
