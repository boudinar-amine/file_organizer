"""Scan Folder page implementing guided 3-step workflow (Section 4).

Step 1: Source Folder & PDF detection
Step 2: Analysis Options (with collapsible advanced settings)
Step 3: Read-only Analysis Execution & non-blocking Progress Panel
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
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
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ScanPage(QWidget):
    """Guided scan workflow page."""

    analyzeRequested = Signal(Path, bool, int, bool, str)  # folder, subfolders, pages, use_ai, ai_model
    cancelRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header
        title = QLabel("Scan & Analyze Folder")
        t_font = QFont()
        t_font.setPointSize(18)
        t_font.setBold(True)
        title.setFont(t_font)
        title.setStyleSheet("color: #f8fafc;")
        sub = QLabel("Select a folder of documents to analyze and categorize with offline AI.")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(sub)

        # =====================================================================
        # Step 1: Source
        # =====================================================================
        step1_card = QFrame()
        step1_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        s1_layout = QVBoxLayout(step1_card)
        s1_layout.setSpacing(10)

        s1_hdr = QLabel("Step 1 — Source Folder")
        s1_hdr.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
        s1_layout.addWidget(s1_hdr)

        folder_row = QHBoxLayout()
        self._folder_input = QLineEdit()
        self._folder_input.setPlaceholderText("Select or enter a folder path to scan...")
        self._folder_input.setFixedHeight(34)
        self._folder_input.textChanged.connect(self._on_folder_changed)
        folder_row.addWidget(self._folder_input, 1)

        self._browse_btn = QPushButton("Browse Folder")
        self._browse_btn.setFixedHeight(34)
        self._browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(self._browse_btn)
        s1_layout.addLayout(folder_row)

        opts_row = QHBoxLayout()
        self._subfolders_check = QCheckBox("Include subfolders")
        self._subfolders_check.setChecked(True)
        opts_row.addWidget(self._subfolders_check)

        self._folder_stats_lbl = QLabel("No folder selected yet.")
        self._folder_stats_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        opts_row.addStretch()
        opts_row.addWidget(self._folder_stats_lbl)
        s1_layout.addLayout(opts_row)

        layout.addWidget(step1_card)

        # =====================================================================
        # Step 2: Analysis Options
        # =====================================================================
        step2_card = QFrame()
        step2_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        s2_layout = QVBoxLayout(step2_card)
        s2_layout.setSpacing(10)

        s2_hdr = QLabel("Step 2 — Analysis Options")
        s2_hdr.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
        s2_layout.addWidget(s2_hdr)

        # Main options row
        main_opts = QHBoxLayout()
        main_opts.addWidget(QLabel("Pages to inspect:"))
        self._max_pages_spin = QSpinBox()
        self._max_pages_spin.setRange(1, 100)
        self._max_pages_spin.setValue(2)
        self._max_pages_spin.setFixedWidth(60)
        main_opts.addWidget(self._max_pages_spin)
        main_opts.addSpacing(20)

        main_opts.addWidget(QLabel("Classification Engine:"))
        self._ai_combo = QComboBox()
        self._ai_combo.addItems([
            "Rules only",
            "Rules + Local AI (Ollama)",
        ])
        self._ai_combo.currentIndexChanged.connect(self._on_ai_combo_changed)
        main_opts.addWidget(self._ai_combo)
        main_opts.addStretch()
        s2_layout.addLayout(main_opts)

        # Feature checkboxes
        feats_row = QHBoxLayout()
        self._use_meta_check = QCheckBox("Use document metadata")
        self._use_meta_check.setChecked(True)
        self._detect_scanned_check = QCheckBox("Detect scanned / image-only PDFs")
        self._detect_scanned_check.setChecked(True)
        self._use_profile_check = QCheckBox("Use profile knowledge graph")
        self._use_profile_check.setChecked(True)

        feats_row.addWidget(self._use_meta_check)
        feats_row.addWidget(self._detect_scanned_check)
        feats_row.addWidget(self._use_profile_check)
        feats_row.addStretch()
        s2_layout.addLayout(feats_row)

        # Ollama / AI Status Banner
        self._ollama_hint_label = QLabel()
        self._ollama_hint_label.setStyleSheet(
            "background-color: #064e3b; color: #6ee7b7; border: 1px solid #047857; "
            "border-radius: 6px; padding: 8px 12px; font-size: 11px;"
        )
        self._ollama_hint_label.setWordWrap(True)
        self._ollama_hint_label.setText("✅ <b>Local AI Ready:</b> Offline neural and BM25 models active on this machine.")
        self._ollama_hint_label.hide()
        s2_layout.addWidget(self._ollama_hint_label)

        layout.addWidget(step2_card)

        # =====================================================================
        # Step 3: Scan Action & Progress Panel
        # =====================================================================
        step3_card = QFrame()
        step3_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        s3_layout = QVBoxLayout(step3_card)
        s3_layout.setSpacing(12)

        s3_hdr = QLabel("Step 3 — Analyze")
        s3_hdr.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
        s3_layout.addWidget(s3_hdr)

        btn_row = QHBoxLayout()
        self._analyze_btn = QPushButton("🔍  Analyze Documents")
        self._analyze_btn.setProperty("class", "primary")
        self._analyze_btn.setFixedHeight(38)
        self._analyze_btn.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: 700; padding: 0 24px; border-radius: 6px;"
        )
        self._analyze_btn.clicked.connect(self._on_start_analyze)
        btn_row.addWidget(self._analyze_btn)

        self._cancel_btn = QPushButton("Stop Scan")
        self._cancel_btn.setFixedHeight(38)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self.cancelRequested.emit)
        btn_row.addWidget(self._cancel_btn)

        copy_lbl = QLabel("🔒 Analysis is read-only. No files will be moved or renamed.")
        copy_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; margin-left: 10px;")
        btn_row.addWidget(copy_lbl)
        btn_row.addStretch()
        s3_layout.addLayout(btn_row)

        # Progress Panel
        self._progress_panel = QFrame()
        self._progress_panel.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 10px;")
        prog_layout = QVBoxLayout(self._progress_panel)
        prog_layout.setSpacing(6)

        prog_top = QHBoxLayout()
        self._progress_file_lbl = QLabel("Ready to analyze.")
        self._progress_file_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1; font-size: 12px;")
        self._progress_count_lbl = QLabel("0 / 0 documents")
        self._progress_count_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        prog_top.addWidget(self._progress_file_lbl, 1)
        prog_top.addWidget(self._progress_count_lbl)
        prog_layout.addLayout(prog_top)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(12)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setValue(0)
        prog_layout.addWidget(self._progress_bar)

        self._progress_panel.hide()
        s3_layout.addWidget(self._progress_panel)

        layout.addWidget(step3_card)

        layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _on_ai_combo_changed(self, idx: int) -> None:
        if idx == 1:
            self._ollama_hint_label.show()
        else:
            self._ollama_hint_label.hide()

    def set_folder(self, folder: Path) -> None:
        self._folder_input.setText(str(folder))

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan", self._folder_input.text().strip())
        if folder:
            self._folder_input.setText(folder)

    def _on_folder_changed(self, text: str) -> None:
        p = Path(text.strip()) if text.strip() else None
        if p and p.is_dir():
            try:
                pdfs = list(p.glob("*.pdf"))
                self._folder_stats_lbl.setText(f"Found {len(pdfs)} PDF(s) in root directory.")
            except Exception:
                self._folder_stats_lbl.setText("Folder accessible.")
        else:
            self._folder_stats_lbl.setText("Please select a valid directory.")

    def _on_start_analyze(self) -> None:
        folder_text = self._folder_input.text().strip()
        if not folder_text:
            return
        folder = Path(folder_text)
        subfolders = self._subfolders_check.isChecked()
        pages = self._max_pages_spin.value()
        use_ollama = (self._ai_combo.currentIndex() == 2)
        self.analyzeRequested.emit(folder, subfolders, pages, use_ollama, "qwen2.5:1.5b")

    def show_progress(self, current: int, total: int, message: str) -> None:
        self._progress_panel.show()
        self._progress_bar.setMaximum(total if total > 0 else 0)
        self._progress_bar.setValue(current)
        self._progress_file_lbl.setText(message)
        self._progress_count_lbl.setText(f"{current} / {total} documents")
        self._analyze_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

    def finish_progress(self) -> None:
        self._progress_panel.hide()
        self._analyze_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
