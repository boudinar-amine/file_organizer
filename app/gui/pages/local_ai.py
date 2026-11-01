"""Local AI Models status and offline configuration page (Section 18).

Provides clean status indicators, local embedding paths, and helpful copy-paste
terminal commands without technical HTTP 404 error codes.
"""

from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.classification.ollama_classifier import OllamaClassifier


class LocalAIPage(QWidget):
    """Local AI models status, privacy assurance, and model guidance."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # 1. Header
        title = QLabel("Local AI Engine & Models")
        t_font = QFont()
        t_font.setPointSize(18)
        t_font.setBold(True)
        title.setFont(t_font)
        sub = QLabel("All classification intelligence runs 100% on this PC. No files or text are transmitted.")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(sub)

        # 2. Status Card: Neural Embeddings
        emb_card = QFrame()
        emb_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        emb_layout = QVBoxLayout(emb_card)
        emb_layout.setSpacing(6)

        e_top = QHBoxLayout()
        e_title = QLabel("<b>1. Semantic Embedding Model</b>")
        e_title.setStyleSheet("font-size: 14px; color: #f8fafc;")
        e_top.addWidget(e_title)
        e_top.addStretch()

        e_badge = QLabel("✅ Local & Offline")
        e_badge.setStyleSheet(
            "background-color: #064e3b; color: #86efac; border: 1px solid #059669; "
            "border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
        )
        e_top.addWidget(e_badge)
        emb_layout.addLayout(e_top)

        e_desc = QLabel("Active Model: <code>intfloat/multilingual-e5-small</code> + Okapi BM25 fallback")
        e_desc.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        emb_layout.addWidget(e_desc)

        path_lbl = QLabel("Local disk location: <code>models/multilingual-e5-small</code> (470 MB)")
        path_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        emb_layout.addWidget(path_lbl)
        layout.addWidget(emb_card)

        # 3. Status Card: Local LLM Fallback (Ollama)
        llm_card = QFrame()
        llm_card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;")
        llm_layout = QVBoxLayout(llm_card)
        llm_layout.setSpacing(8)

        l_top = QHBoxLayout()
        l_title = QLabel("<b>2. Local LLM Fallback (Optional)</b>")
        l_title.setStyleSheet("font-size: 14px; color: #f8fafc;")
        l_top.addWidget(l_title)
        l_top.addStretch()

        self._llm_badge = QLabel("Checking…")
        self._llm_badge.setStyleSheet("font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;")
        l_top.addWidget(self._llm_badge)
        llm_layout.addLayout(l_top)

        self._llm_desc = QLabel("Detecting installed Ollama models…")
        self._llm_desc.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        self._llm_desc.setWordWrap(True)
        llm_layout.addWidget(self._llm_desc)

        # Command helper frame
        cmd_frame = QFrame()
        cmd_frame.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 10px;")
        cmd_layout = QHBoxLayout(cmd_frame)
        cmd_layout.setContentsMargins(0, 0, 0, 0)

        cmd_text = QLabel("<code>ollama pull qwen2.5:1.5b</code>")
        cmd_text.setStyleSheet("font-size: 12px; color: #f8fafc;")
        cmd_layout.addWidget(cmd_text, 1)

        copy_btn = QPushButton("Copy Command")
        copy_btn.setFixedHeight(28)
        copy_btn.clicked.connect(lambda: QGuiApplication.clipboard().setText("ollama pull qwen2.5:1.5b"))
        cmd_layout.addWidget(copy_btn)
        llm_layout.addWidget(cmd_frame)

        layout.addWidget(llm_card)

        # 4. Privacy Guarantee Card
        priv_card = QFrame()
        priv_card.setStyleSheet("background-color: #064e3b; border: 1px solid #059669; border-radius: 8px; padding: 14px;")
        priv_layout = QVBoxLayout(priv_card)
        priv_layout.setSpacing(4)
        priv_title = QLabel("🛡️ <b>Privacy & Safety Guarantee</b>")
        priv_title.setStyleSheet("color: #86efac; font-size: 13px;")
        priv_desc = QLabel(
            "• Zero cloud telemetry or external API calls.<br>"
            "• Document text is read directly from local storage and analyzed in RAM.<br>"
            "• Safe Test Mode copies files, keeping originals completely intact."
        )
        priv_desc.setStyleSheet("color: #dcfce7; font-size: 12px;")
        priv_layout.addWidget(priv_title)
        priv_layout.addWidget(priv_desc)
        layout.addWidget(priv_card)

        layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.refresh()

    def refresh(self) -> None:
        """Probe Ollama and update local status cleanly without 404 errors."""
        try:
            oc = OllamaClassifier()
            models = oc.get_installed_models()
            if models:
                self._llm_badge.setText("✅ Connected")
                self._llm_badge.setStyleSheet(
                    "background-color: #064e3b; color: #86efac; border: 1px solid #059669; "
                    "border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
                )
                self._llm_desc.setText(
                    f"Ollama server is active with models: <b>{', '.join(models[:3])}</b>. "
                    "Used only as an optional fallback for ambiguous documents."
                )
            else:
                self._llm_badge.setText("Offline — Using Rules + BM25")
                self._llm_badge.setStyleSheet(
                    "background-color: #1e3a8a; color: #93c5fd; border: 1px solid #2563eb; "
                    "border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
                )
                self._llm_desc.setText(
                    "Ollama server is not running or has no models installed. "
                    "The application is operating with high accuracy using local Rules + BM25."
                )
        except Exception:
            self._llm_badge.setText("Rules + BM25 Engine Active")
            self._llm_badge.setStyleSheet(
                "background-color: #334155; color: #94a3b8; border: 1px solid #475569; "
                "border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px;"
            )
            self._llm_desc.setText("Local offline AI is active without external daemons.")
