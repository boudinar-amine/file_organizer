"""Pre-execution safety confirmation dialog before moving/copying files."""

from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)


class ConfirmOperationDialog(QDialog):
    """Explicit, safe confirmation dialog shown prior to file operations."""

    def __init__(
        self,
        source: Path,
        destination: Path,
        mode_is_copy: bool,
        ready_count: int,
        skipped_count: int,
        conflict_count: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ready to organize")
        self.setFixedWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        title = QLabel("Ready to organize")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Summary frame
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(6)

        def make_row(lbl: str, val: str, bold: bool = False) -> QHBoxLayout:
            r = QHBoxLayout()
            l = QLabel(f"<b>{lbl}</b>" if bold else lbl)
            l.setStyleSheet("color: #94a3b8; font-size: 12px;")
            l.setFixedWidth(90)
            v = QLabel(val)
            v.setStyleSheet("color: #f8fafc; font-size: 12px; font-weight: 600;" if bold else "color: #f8fafc; font-size: 12px;")
            v.setWordWrap(True)
            r.addWidget(l)
            r.addWidget(v, 1)
            return r

        info_layout.addLayout(make_row("Source:", str(source)))
        info_layout.addLayout(make_row("Destination:", str(destination)))
        mode_str = "COPY (Originals untouched)" if mode_is_copy else "MOVE (Relocate originals)"
        info_layout.addLayout(make_row("Mode:", mode_str, bold=True))
        info_layout.addLayout(make_row("Files to organize:", str(ready_count), bold=True))
        if skipped_count > 0:
            info_layout.addLayout(make_row("Skipped files:", str(skipped_count)))
        if conflict_count > 0:
            info_layout.addLayout(make_row("Conflicts:", f"⚠️ {conflict_count} filename collisions"))

        layout.addWidget(info_frame)

        # Conflict resolution selection
        if conflict_count > 0:
            conf_box = QFrame()
            conf_box.setStyleSheet("background-color: #78350f; border: 1px solid #b45309; border-radius: 6px; padding: 8px;")
            conf_layout = QVBoxLayout(conf_box)
            conf_layout.setSpacing(4)
            conf_lbl = QLabel("Conflict strategy:")
            conf_lbl.setStyleSheet("font-weight: 600; color: #fde68a; font-size: 12px;")
            conf_layout.addWidget(conf_lbl)

            self._radio_rename = QRadioButton("Auto-rename duplicate files with (1)")
            self._radio_rename.setChecked(True)
            self._radio_skip = QRadioButton("Skip duplicates safely (leave untouched)")
            conf_layout.addWidget(self._radio_rename)
            conf_layout.addWidget(self._radio_skip)
            layout.addWidget(conf_box)
        else:
            self._radio_rename = None
            self._radio_skip = None

        # Safe buttons
        button_box = QDialogButtonBox()
        self._action_btn = button_box.addButton(
            f"Copy {ready_count} Files" if mode_is_copy else f"Move {ready_count} Files",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self._action_btn.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: bold; padding: 6px 16px; border-radius: 6px;"
        )
        self._cancel_btn = button_box.addButton("Go Back", QDialogButtonBox.ButtonRole.RejectRole)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    @property
    def auto_rename_conflicts(self) -> bool:
        if self._radio_rename is not None:
            return self._radio_rename.isChecked()
        return True
