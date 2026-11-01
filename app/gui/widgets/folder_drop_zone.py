"""Drag-and-drop zone for selecting source folders."""

from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget


class FolderDropZone(QWidget):
    """Modern folder drag-and-drop surface."""

    folderSelected = Signal(Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(160)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)

        icon_lbl = QLabel("📁")
        icon_font = QFont()
        icon_font.setPointSize(28)
        icon_lbl.setFont(icon_font)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel("Drop a folder here")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #f8fafc;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        self._choose_btn = QPushButton("Choose folder")
        self._choose_btn.setFixedWidth(130)
        self._choose_btn.clicked.connect(self._on_choose_folder)
        layout.addWidget(self._choose_btn, 0, Qt.AlignmentFlag.AlignCenter)

        hint_lbl = QLabel("Your files stay on this computer. Scanning does not modify them.")
        hint_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_lbl)

        self._normal_style = (
            "FolderDropZone { background-color: #1e293b; border: 2px dashed #475569; "
            "border-radius: 10px; color: #f8fafc; } FolderDropZone:hover { border-color: #3b82f6; background-color: #0f172a; }"
        )
        self._hover_style = (
            "FolderDropZone { background-color: #172554; border: 2px dashed #3b82f6; "
            "border-radius: 10px; color: #f8fafc; }"
        )
        self.setStyleSheet(self._normal_style)

    def _on_choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Organize")
        if folder:
            self.folderSelected.emit(Path(folder))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.is_dir():
                    event.acceptProposedAction()
                    self.setStyleSheet(self._hover_style)
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.setStyleSheet(self._normal_style)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet(self._normal_style)
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.is_dir():
                    event.acceptProposedAction()
                    self.folderSelected.emit(p)
                    return
        event.ignore()
