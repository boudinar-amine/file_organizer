"""User Profile and Knowledge Graph management page (Section 14, 15, 16, 17).

Features:
- Three-dimensional model tabs (Context, Relationship, Content)
- Multi-activity career cards (PhD XAI, Insurtech, Health Security)
- Local, offline CV/Résumé Guided Import (PDF/DOCX/TXT) with Accept/Edit/Ignore
- Non-blocking Progressive Entity Discovery suggestions
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.classification.profile_discovery import DiscoveredEntity
from app.classification.user_profile import (
    PRESET_PROFILES,
    PROFILE_PHD_AI_INSURTECH_HEALTH,
    ProfessionalActivity,
    UserProfile,
    WorkContextType,
    get_default_profile,
)
from app.extraction.cv_parser import CVParser


class ActivityCard(QFrame):
    """Card representing a single professional, academic, or consulting activity."""

    deleted = Signal(object)

    def __init__(self, activity: ProfessionalActivity, parent=None) -> None:
        super().__init__(parent)
        self.activity = activity
        self.setStyleSheet(
            "ActivityCard { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px; } "
            "ActivityCard:hover { border-color: #475569; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: Role & Organization
        top = QHBoxLayout()
        role_lbl = QLabel(f"<b>{activity.role}</b> — {activity.organization}")
        role_lbl.setStyleSheet("font-size: 13px; color: #f8fafc;")
        top.addWidget(role_lbl, 1)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setStyleSheet(
            "QPushButton { border: none; color: #94a3b8; font-weight: bold; } "
            "QPushButton:hover { color: #f87171; background-color: #450a0a; border-radius: 4px; }"
        )
        del_btn.clicked.connect(lambda: self.deleted.emit(self.activity))
        top.addWidget(del_btn)
        layout.addLayout(top)

        # Subtitle: Context & Years
        ctx = activity.work_context or "Employment"
        years = activity.period_display
        ctx_lbl = QLabel(f"Context: {ctx} • {years}")
        ctx_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(ctx_lbl)

        # Domains & Signals
        doms_str = ", ".join(activity.domains) if activity.domains else "General"
        tags_lbl = QLabel(f"🏷️ Domains: {doms_str}")
        tags_lbl.setStyleSheet("color: #60a5fa; font-size: 11px; font-weight: 500;")
        layout.addWidget(tags_lbl)


class ProfilePage(QWidget):
    """Knowledge profile management and offline CV importer page."""

    profileSaved = Signal(object)  # Emits updated UserProfile

    def __init__(self, current_profile: Optional[UserProfile] = None, parent=None) -> None:
        super().__init__(parent)
        self._profile: UserProfile = current_profile or get_default_profile()
        self._discovered: list[DiscoveredEntity] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # 1. Page Header
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Your Knowledge Profile")
        t_font = QFont()
        t_font.setPointSize(18)
        t_font.setBold(True)
        title.setFont(t_font)
        sub = QLabel("The profile helps the organizer understand why documents matter to you. It remains entirely local.")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_row.addLayout(title_box)
        top_row.addStretch()

        self._profile_btn = QPushButton("Save Knowledge Profile")
        self._profile_btn.setProperty("class", "primary")
        self._profile_btn.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: 700; padding: 6px 20px; border-radius: 6px;"
        )
        self._profile_btn.clicked.connect(self._on_save_profile)
        top_row.addWidget(self._profile_btn)
        layout.addLayout(top_row)

        # 2. Progressive Discovery Notification Banner (Section 17)
        self._discovery_frame = QFrame()
        self._discovery_frame.setStyleSheet("background-color: #1e3a8a; border: 1px solid #2563eb; border-radius: 8px; padding: 12px;")
        disc_layout = QHBoxLayout(self._discovery_frame)
        self._discovery_text = QLabel("💡 <b>Suggestions:</b> No entity suggestions yet.")
        self._discovery_text.setStyleSheet("color: #93c5fd; font-size: 12px;")
        self._add_suggestion_btn = QPushButton("Add to Known")
        self._add_suggestion_btn.setFixedHeight(28)
        self._add_suggestion_btn.clicked.connect(self._on_accept_top_suggestion)
        disc_layout.addWidget(self._discovery_text, 1)
        disc_layout.addWidget(self._add_suggestion_btn)
        self._discovery_frame.hide()
        layout.addWidget(self._discovery_frame)

        # 3. Multi-Tab Conceptual Model (Section 15)
        tabs = QTabWidget()

        # Tab A: Professional & Academic Activities
        act_tab = QWidget()
        act_layout = QVBoxLayout(act_tab)
        act_layout.setContentsMargins(14, 14, 14, 14)
        act_layout.setSpacing(10)

        act_top = QHBoxLayout()
        act_top.addWidget(QLabel("<b>Career & Academic History</b> (Work is a context, not a single domain)"))
        act_top.addStretch()
        self._add_act_btn = QPushButton("+ Add Activity")
        self._add_act_btn.clicked.connect(self._on_add_activity_dialog)
        act_top.addWidget(self._add_act_btn)
        act_layout.addLayout(act_top)

        self._cards_layout = QVBoxLayout()
        self._cards_layout.setSpacing(8)
        act_layout.addLayout(self._cards_layout)
        act_layout.addStretch()
        tabs.addTab(act_tab, "Activities & History")

        # Tab B: Guided CV / Résumé Importer (Section 16)
        cv_tab = QWidget()
        cv_layout = QVBoxLayout(cv_tab)
        cv_layout.setContentsMargins(14, 14, 14, 14)
        cv_layout.setSpacing(10)

        cv_box = QFrame()
        cv_box.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;")
        cv_box_layout = QVBoxLayout(cv_box)
        cv_box_layout.setSpacing(6)
        cv_title = QLabel("<b>Local Offline CV / Résumé Importer</b>")
        cv_desc = QLabel("Import a PDF, DOCX, or TXT résumé to automatically extract career activities without cloud transmission.")
        cv_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        cv_box_layout.addWidget(cv_title)
        cv_box_layout.addWidget(cv_desc)

        cv_btn_row = QHBoxLayout()
        self._import_cv_btn = QPushButton("📄 Select CV / Résumé to Import")
        self._import_cv_btn.setFixedHeight(34)
        self._import_cv_btn.clicked.connect(self._on_import_cv)
        cv_btn_row.addWidget(self._import_cv_btn)

        self._delete_source_check = QCheckBox("Securely delete source CV file after successful import")
        self._delete_source_check.setStyleSheet("color: #94a3b8; font-size: 11px;")
        cv_btn_row.addSpacing(16)
        cv_btn_row.addWidget(self._delete_source_check)
        cv_btn_row.addStretch()
        cv_box_layout.addLayout(cv_btn_row)
        cv_layout.addWidget(cv_box)

        self._cv_results_lbl = QLabel("")
        self._cv_results_lbl.setStyleSheet("color: #4ade80; font-weight: 600; font-size: 12px;")
        cv_layout.addWidget(self._cv_results_lbl)
        cv_layout.addStretch()
        tabs.addTab(cv_tab, "Import CV / Résumé")

        layout.addWidget(tabs)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._render_activities()

    @property
    def profile_btn(self) -> QPushButton:
        return self._profile_btn

    def get_profile(self) -> UserProfile:
        return self._profile

    def set_profile(self, profile: UserProfile) -> None:
        self._profile = profile
        self._render_activities()

    def set_discovered_entities(self, entities: list[DiscoveredEntity]) -> None:
        self._discovered = entities
        if entities:
            top = entities[0]
            self._discovery_text.setText(
                f"💡 <b>Suggestion:</b> '<b>{top.name}</b>' appeared in {top.occurrence_count} documents. Add to profile?"
            )
            self._discovery_frame.show()
        else:
            self._discovery_frame.hide()

    def _render_activities(self) -> None:
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for act in self._profile.activities:
            card = ActivityCard(act)
            card.deleted.connect(self._on_delete_activity)
            self._cards_layout.addWidget(card)

    def _on_delete_activity(self, activity: ProfessionalActivity) -> None:
        self._profile.activities = [a for a in self._profile.activities if a != activity]
        self._render_activities()

    def _on_add_activity_dialog(self) -> None:
        act = ProfessionalActivity(
            organization="New Organization",
            role="Specialist",
            domains=["Explainable AI"],
            work_context=WorkContextType.CURRENT_EMPLOYMENT,
            start_year=2024,
            is_current=True,
        )
        self._profile.activities.append(act)
        self._render_activities()

    def _on_import_cv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CV / Résumé to Import", "", "Documents (*.pdf *.docx *.txt)"
        )
        if not path:
            return

        parser = CVParser()
        result = parser.parse_file(Path(path))
        if result.extracted_activities:
            for act in result.extracted_activities:
                self._profile.activities.append(act)
            self._render_activities()
            self._cv_results_lbl.setText(
                f"✅ Found and imported {len(result.extracted_activities)} candidate activities locally."
            )
            if self._delete_source_check.isChecked():
                parser.securely_delete_source_file(Path(path))
        else:
            QMessageBox.information(self, "CV Import", "No clear activities found in document.")

    def _on_accept_top_suggestion(self) -> None:
        if not self._discovered:
            return
        top = self._discovered.pop(0)
        self._profile.organization_aliases[top.name.lower()] = top.name
        self.set_discovered_entities(self._discovered)
        QMessageBox.information(self, "Entity Added", f"Added '{top.name}' to known organizations.")

    def _on_save_profile(self) -> None:
        self.profileSaved.emit(self._profile)
        QMessageBox.information(self, "Profile Saved", f"Profile '{self._profile.name}' updated successfully.")
