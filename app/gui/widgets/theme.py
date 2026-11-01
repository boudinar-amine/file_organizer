"""Unified design system, themes, and styles for the PDF Organizer desktop app.

Provides light and dark theme palettes adhering to modern Windows 11 / PowerToys aesthetics:
- 8px spacing grid
- 6-10px corner radius
- High contrast and accessible semantic indicators
"""

from __future__ import annotations


class Theme:
    """Color tokens and stylesheet generator for light and dark modes."""

    # Light palette
    LIGHT_BG = "#f8fafc"           # Slate 50
    LIGHT_SURFACE = "#ffffff"      # Pure white
    LIGHT_SURFACE_ALT = "#f1f5f9"  # Slate 100
    LIGHT_BORDER = "#e2e8f0"       # Slate 200
    LIGHT_TEXT = "#0f172a"         # Slate 900
    LIGHT_TEXT_MUTED = "#64748b"   # Slate 500
    LIGHT_TEXT_SUBTLE = "#94a3b8"  # Slate 400

    # Dark palette
    DARK_BG = "#0f172a"            # Slate 900
    DARK_SURFACE = "#1e293b"       # Slate 800
    DARK_SURFACE_ALT = "#334155"   # Slate 700
    DARK_BORDER = "#334155"        # Slate 700
    DARK_TEXT = "#f8fafc"          # Slate 50
    DARK_TEXT_MUTED = "#94a3b8"    # Slate 400
    DARK_TEXT_SUBTLE = "#64748b"   # Slate 500

    # Semantic Accents
    ACCENT_PRIMARY = "#2563eb"     # Blue 600
    ACCENT_PRIMARY_HOVER = "#1d4ed8"
    ACCENT_LIGHT = "#eff6ff"       # Blue 50
    SUCCESS = "#16a34a"            # Green 600
    SUCCESS_BG = "#f0fdf4"
    SUCCESS_BORDER = "#bbf7d0"
    WARNING = "#d97706"            # Amber 600
    WARNING_BG = "#fffbeb"
    WARNING_BORDER = "#fde68a"
    DANGER = "#dc2626"             # Red 600
    DANGER_BG = "#fef2f2"
    DANGER_BORDER = "#fecaca"

    @classmethod
    def get_stylesheet(cls, dark: bool = True) -> str:
        """Generate comprehensive application stylesheet (default: Dark Mode)."""
        bg = cls.DARK_BG if dark else cls.LIGHT_BG
        surface = cls.DARK_SURFACE if dark else cls.LIGHT_SURFACE
        surface_alt = cls.DARK_SURFACE_ALT if dark else cls.LIGHT_SURFACE_ALT
        border = cls.DARK_BORDER if dark else cls.LIGHT_BORDER
        text = cls.DARK_TEXT if dark else cls.LIGHT_TEXT
        text_muted = cls.DARK_TEXT_MUTED if dark else cls.LIGHT_TEXT_MUTED
        accent = "#3b82f6" if dark else cls.ACCENT_PRIMARY
        accent_bg = "#1e3a8a" if dark else cls.ACCENT_LIGHT
        alt_row = "#162032" if dark else "#f8fafc"

        return f"""
        QMainWindow, QDialog {{
            background-color: {bg};
            color: {text};
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            font-size: 13px;
        }}
        QWidget {{
            color: {text};
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        }}
        QGroupBox {{
            background-color: {surface};
            border: 1px solid {border};
            border-radius: 8px;
            margin-top: 18px;
            padding: 16px;
            font-weight: 600;
            font-size: 13px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {text};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px 10px;
            selection-background-color: {accent};
            font-size: 13px;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid {accent};
        }}
        QComboBox QAbstractItemView {{
            background-color: {surface};
            color: {text};
            selection-background-color: {accent_bg};
            selection-color: #ffffff;
            border: 1px solid {border};
        }}
        QPushButton {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: 500;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {surface_alt};
            border-color: {accent};
        }}
        QPushButton:pressed {{
            background-color: {surface_alt};
        }}
        QPushButton:disabled {{
            color: {text_muted};
            background-color: {bg};
            border-color: {border};
        }}
        QPushButton.primary {{
            background-color: {accent};
            color: #ffffff;
            border: none;
            font-weight: 600;
        }}
        QPushButton.primary:hover {{
            background-color: #2563eb;
        }}
        QPushButton.success {{
            background-color: {cls.SUCCESS};
            color: #ffffff;
            border: none;
            font-weight: 600;
        }}
        QPushButton.success:hover {{
            background-color: #15803d;
        }}
        QTableWidget, QTableView, QTreeWidget, QTreeView {{
            background-color: {surface};
            alternate-background-color: {alt_row};
            color: {text};
            border: 1px solid {border};
            border-radius: 8px;
            gridline-color: {border};
            selection-background-color: {accent_bg};
            selection-color: #ffffff;
            outline: none;
        }}
        QHeaderView::section {{
            background-color: {surface_alt};
            color: {text};
            font-weight: 600;
            font-size: 12px;
            border: none;
            border-bottom: 1px solid {border};
            padding: 6px 10px;
        }}
        QScrollBar:vertical {{
            border: none;
            background: {bg};
            width: 8px;
            margin: 0;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: {bg};
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {border};
            min-height: 24px;
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background: {text_muted};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            height: 0px;
            width: 0px;
        }}
        QProgressBar {{
            background-color: {surface_alt};
            border: 1px solid {border};
            border-radius: 4px;
            text-align: center;
            font-size: 11px;
            font-weight: 600;
            color: {text};
        }}
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 3px;
        }}
        QTabWidget::pane {{
            border: 1px solid {border};
            border-radius: 8px;
            background: {surface};
            top: -1px;
        }}
        QTabBar::tab {{
            background: {surface_alt};
            color: {text_muted};
            border: 1px solid {border};
            border-bottom: none;
            padding: 8px 16px;
            font-weight: 500;
            margin-right: 4px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background: {surface};
            font-weight: 600;
            color: {accent};
            border-bottom: 2px solid {accent};
        }}
        QStatusBar {{
            background-color: {surface};
            border-top: 1px solid {border};
            color: {text_muted};
            font-size: 12px;
        }}
        QMenu {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 16px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {accent_bg};
            color: #ffffff;
        }}
        QToolTip {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
        }}
        """
