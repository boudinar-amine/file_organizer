"""Domain Personalization and User Profile Dialog (Section 21).

Implements:
- Multi-Activity Professional Profiles (Current, Previous, Research, Consulting, Freelance).
- Local Offline CV/Résumé import (PDF, DOCX, TXT) with candidate review (Accept, Edit, Delete).
- Context disambiguation (Work, Learning, Training, Reference, Personal).
- Personal document categories and learning interests.
- Progressive entity discovery from scanned documents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.classification.profile_discovery import DiscoveredEntity, ProfileDiscoveryEngine
from app.classification.user_profile import (
    DEFAULT_PERSONAL_CATEGORIES,
    PRESET_PROFILES,
    PROFILE_GENERAL_ACADEMIC,
    PROFILE_PHD_AI_INSURTECH_HEALTH,
    DomainSpec,
    EducationEntry,
    ProfessionalActivity,
    UserProfile,
    WorkContextType,
    get_default_profile,
)
from app.extraction.cv_parser import CVParser, CVParsingResult
from app.utils.paths import get_config_path


class ProfileDialog(QDialog):
    """Complete Profile Setup and Knowledge Graph Manager."""

    profile_changed = Signal(UserProfile)

    def __init__(
        self,
        current_profile: Optional[UserProfile] = None,
        discovered_candidates: Optional[list[DiscoveredEntity]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("User Profile & Professional Activity Knowledge Graph")
        self.setMinimumSize(940, 680)
        self.resize(1020, 720)

        self._active_profile: UserProfile = current_profile or get_default_profile()
        self._activities: list[ProfessionalActivity] = list(self._active_profile.activities)
        self._education: list[EducationEntry] = list(self._active_profile.education)
        self._personal_categories: list[str] = list(self._active_profile.personal_categories)
        self._learning_interests: list[str] = list(self._active_profile.learning_interests)
        self._domains: list[DomainSpec] = list(self._active_profile.domains)
        self._discovered: list[DiscoveredEntity] = discovered_candidates or []
        self._cv_parser = CVParser()

        self._build_ui()
        self._refresh_all_views()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Header Banner
        header = QFrame()
        header.setStyleSheet(
            "QFrame { background-color: #f0fdf4; border: 1px solid #bbf7d0; "
            "border-radius: 8px; padding: 10px; }"
        )
        h_layout = QVBoxLayout(header)
        h_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title = QLabel("👤  Professional Profile & Context Knowledge Graph")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #14532d;")
        title_row.addWidget(title)
        title_row.addStretch()

        preset_label = QLabel("Preset:")
        title_row.addWidget(preset_label)
        self._preset_combo = QComboBox()
        self._preset_combo.addItem("⭐ PhD in XAI, Insurtech & Sécurité Sanitaire", "phd")
        self._preset_combo.addItem("🔬 Academic Researcher & Scientist", "academic")
        self._preset_combo.addItem("🌐 Zero Profile (No Prior Bias)", "zero")
        self._preset_combo.addItem("✏️ Custom Configured Profile", "custom")
        self._preset_combo.currentIndexChanged.connect(self._on_preset_dropdown_changed)
        title_row.addWidget(self._preset_combo)

        h_layout.addLayout(title_row)

        desc = QLabel(
            "<b>Work is a context, not a domain.</b> Define your employers, research roles, consulting activities, "
            "or import your CV locally. This provides prior knowledge to accurately route documents."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #166534; font-size: 11px;")
        h_layout.addWidget(desc)

        main_layout.addWidget(header)

        # 2. Tab Widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("QTabBar::tab { font-weight: bold; padding: 6px 14px; }")

        # Tab 1: Activities & Employers
        self._tab_activities = self._build_activities_tab()
        self._tabs.addTab(self._tab_activities, "🏢 Professional Activities & Employers")

        # Tab 2: Local CV Import
        self._tab_cv = self._build_cv_import_tab()
        self._tabs.addTab(self._tab_cv, "📄 Import CV / Résumé (Local & Offline)")

        # Tab 3: Learning & Personal Categories
        self._tab_personal = self._build_personal_tab()
        self._tabs.addTab(self._tab_personal, "🎓 Learning & 📁 Personal Categories")

        # Tab 4: Discovered from Documents
        self._tab_discovery = self._build_discovery_tab()
        self._tabs.addTab(self._tab_discovery, f"🔍 Discovered Entities ({len(self._discovered)})")

        main_layout.addWidget(self._tabs, 1)

        # 3. Bottom Action Buttons
        btn_row = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setFixedHeight(34)
        reset_btn.clicked.connect(self._on_reset_profile)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("💾  Save & Apply Profile")
        save_btn.setFixedHeight(34)
        save_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; font-weight: bold; "
            "border-radius: 4px; padding: 0 20px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
        save_btn.clicked.connect(self._on_save_and_apply)
        btn_row.addWidget(save_btn)

        main_layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Tab 1: Professional Activities & Employers
    # ------------------------------------------------------------------

    def _build_activities_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        info = QLabel(
            "Maintain distinct profiles for each stage of your career (Current Employer, Previous Employers, "
            "Research, Consulting, or Freelance). Dates provide temporal support without overriding document content."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(info)

        self._activities_table = QTableWidget()
        self._activities_table.setColumnCount(5)
        self._activities_table.setHorizontalHeaderLabels([
            "Organization", "Context / Type", "Role / Title", "Period", "Domains & Projects"
        ])
        self._activities_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._activities_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._activities_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._activities_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._activities_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._activities_table.setAlternatingRowColors(True)
        self._activities_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._activities_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ Add Activity / Employer")
        add_btn.clicked.connect(self._on_add_activity)
        btn_row.addWidget(add_btn)

        edit_btn = QPushButton("✏️ Edit Selected")
        edit_btn.clicked.connect(self._on_edit_activity)
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ Remove Selected")
        del_btn.clicked.connect(self._on_remove_activity)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return widget

    # ------------------------------------------------------------------
    # Tab 2: Local Offline CV / Résumé Import
    # ------------------------------------------------------------------

    def _build_cv_import_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        box = QFrame()
        box.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(6)

        label = QLabel("<b>Import CV or Résumé (100% Offline & Private)</b>")
        box_layout.addWidget(label)
        sub = QLabel(
            "Select your CV in PDF, Word (DOCX), or Text format. The application will analyze it locally on your PC "
            "to extract candidate employers, job titles, employment dates, skills, and education."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #64748b; font-size: 11px;")
        box_layout.addWidget(sub)

        file_row = QHBoxLayout()
        self._cv_path_input = QLineEdit()
        self._cv_path_input.setPlaceholderText("Select a CV file (.pdf, .docx, .txt)...")
        file_row.addWidget(self._cv_path_input, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_cv)
        file_row.addWidget(browse_btn)

        self._extract_cv_btn = QPushButton("⚡ Extract Profile Candidates")
        self._extract_cv_btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 4px 14px;")
        self._extract_cv_btn.clicked.connect(self._on_extract_cv)
        file_row.addWidget(self._extract_cv_btn)

        box_layout.addLayout(file_row)

        # Privacy option
        self._delete_cv_check = QCheckBox("Securely delete source CV file after profile extraction (Privacy Option)")
        self._delete_cv_check.setChecked(False)
        box_layout.addWidget(self._delete_cv_check)

        layout.addWidget(box)

        # Extracted Candidates Table
        cands_label = QLabel("<b>Extracted Profile Candidates:</b> (Review, Accept, or Edit before adding to Knowledge Graph)")
        layout.addWidget(cands_label)

        self._candidates_table = QTableWidget()
        self._candidates_table.setColumnCount(4)
        self._candidates_table.setHorizontalHeaderLabels(["Entity Type", "Extracted Organization / Name", "Role / Details", "Period / Dates"])
        self._candidates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._candidates_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self._candidates_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._candidates_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._candidates_table.setAlternatingRowColors(True)
        self._candidates_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._candidates_table)

        cand_btn_row = QHBoxLayout()
        accept_btn = QPushButton("✅ Accept Selected Candidate")
        accept_btn.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold;")
        accept_btn.clicked.connect(self._on_accept_candidate)
        cand_btn_row.addWidget(accept_btn)

        accept_all_btn = QPushButton("✅ Accept All Candidates")
        accept_all_btn.clicked.connect(self._on_accept_all_candidates)
        cand_btn_row.addWidget(accept_all_btn)

        cand_btn_row.addStretch()
        layout.addLayout(cand_btn_row)

        self._parsed_candidates: Optional[CVParsingResult] = None
        return widget

    # ------------------------------------------------------------------
    # Tab 3: Learning & Personal Categories
    # ------------------------------------------------------------------

    def _build_personal_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Learning Background Group
        learning_group = QGroupBox("🎓 Learning & Academic Interests (Section 21.1)")
        learning_layout = QVBoxLayout(learning_group)
        learning_desc = QLabel("Topics, courses, or subjects you are currently learning or researching:")
        learning_desc.setStyleSheet("color: #64748b; font-size: 11px;")
        learning_layout.addWidget(learning_desc)

        self._learning_input = QLineEdit()
        self._learning_input.setText(", ".join(self._learning_interests))
        self._learning_input.setPlaceholderText("e.g. Deep Learning, Generative AI, Cloud Architecture, Regulatory Affairs")
        learning_layout.addWidget(self._learning_input)
        layout.addWidget(learning_group)

        # Personal Categories Group
        personal_group = QGroupBox("📁 Personal Document Categories (Section 21.1)")
        personal_layout = QVBoxLayout(personal_group)
        p_desc = QLabel("Select the personal document categories you commonly store (these are kept separate from Work):")
        p_desc.setStyleSheet("color: #64748b; font-size: 11px;")
        personal_layout.addWidget(p_desc)

        self._personal_checkboxes: dict[str, QCheckBox] = {}
        row_layout = QHBoxLayout()
        for idx, cat in enumerate(DEFAULT_PERSONAL_CATEGORIES):
            cb = QCheckBox(cat)
            cb.setChecked(cat in self._personal_categories)
            self._personal_checkboxes[cat] = cb
            row_layout.addWidget(cb)
            if (idx + 1) % 3 == 0 or idx == len(DEFAULT_PERSONAL_CATEGORIES) - 1:
                personal_layout.addLayout(row_layout)
                row_layout = QHBoxLayout()

        layout.addWidget(personal_group)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Tab 4: Progressive Discovery from Documents
    # ------------------------------------------------------------------

    def _build_discovery_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        info = QLabel(
            "The application inspects scanned documents and detects recurring organizations, clients, or domains "
            "that are not currently in your profile. You can progressively add them with one click."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(info)

        self._discovery_table = QTableWidget()
        self._discovery_table.setColumnCount(4)
        self._discovery_table.setHorizontalHeaderLabels(["Entity Name", "Type", "Occurrences", "Sample Documents"])
        self._discovery_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._discovery_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._discovery_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._discovery_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._discovery_table.setAlternatingRowColors(True)
        self._discovery_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._discovery_table)

        btn_row = QHBoxLayout()
        add_disc_btn = QPushButton("➕ Add Selected to Profile")
        add_disc_btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
        add_disc_btn.clicked.connect(self._on_add_discovered)
        btn_row.addWidget(add_disc_btn)

        ignore_disc_btn = QPushButton("Ignore")
        ignore_disc_btn.clicked.connect(self._on_ignore_discovered)
        btn_row.addWidget(ignore_disc_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return widget

    # ------------------------------------------------------------------
    # Data Population & Refresh
    # ------------------------------------------------------------------

    def _refresh_all_views(self) -> None:
        """Populate all tables from current data."""
        # 1. Activities Table
        self._activities_table.setRowCount(0)
        for row, act in enumerate(self._activities):
            self._activities_table.insertRow(row)

            org_item = QTableWidgetItem(f"🏢 {act.organization}")
            org_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self._activities_table.setItem(row, 0, org_item)

            ctx_item = QTableWidgetItem(act.work_context)
            self._activities_table.setItem(row, 1, ctx_item)

            role_item = QTableWidgetItem(act.role or "—")
            self._activities_table.setItem(row, 2, role_item)

            period_item = QTableWidgetItem(act.period_display)
            period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._activities_table.setItem(row, 3, period_item)

            doms = ", ".join(act.domains[:2] + act.projects[:2])
            summary_item = QTableWidgetItem(doms or "—")
            self._activities_table.setItem(row, 4, summary_item)

        # 2. Discovery Table
        self._discovery_table.setRowCount(0)
        for row, disc in enumerate(self._discovered):
            self._discovery_table.insertRow(row)
            self._discovery_table.setItem(row, 0, QTableWidgetItem(disc.name))
            self._discovery_table.setItem(row, 1, QTableWidgetItem(disc.entity_type.capitalize()))
            occ_item = QTableWidgetItem(f"{disc.occurrence_count} docs")
            occ_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._discovery_table.setItem(row, 2, occ_item)
            self._discovery_table.setItem(row, 3, QTableWidgetItem(", ".join(disc.sample_files[:3])))

    # ------------------------------------------------------------------
    # Activity Add / Edit / Remove
    # ------------------------------------------------------------------

    def _on_add_activity(self) -> None:
        """Open dialog to add a new professional activity."""
        self._show_activity_editor()

    def _on_edit_activity(self) -> None:
        """Open editor for selected activity."""
        row = self._activities_table.currentRow()
        if 0 <= row < len(self._activities):
            self._show_activity_editor(self._activities[row], row)

    def _on_remove_activity(self) -> None:
        """Remove selected activity."""
        row = self._activities_table.currentRow()
        if 0 <= row < len(self._activities):
            del self._activities[row]
            self._refresh_all_views()

    def _show_activity_editor(self, activity: Optional[ProfessionalActivity] = None, edit_index: int = -1) -> None:
        """Modal editor dialog for an activity entry."""
        diag = QDialog(self)
        diag.setWindowTitle("Edit Professional Activity" if activity else "Add Professional Activity")
        diag.setMinimumWidth(500)
        vbox = QVBoxLayout(diag)

        # Organization
        vbox.addWidget(QLabel("Organization / Employer / Institution Name:"))
        org_in = QLineEdit(activity.organization if activity else "")
        vbox.addWidget(org_in)

        # Context
        vbox.addWidget(QLabel("Work Context / Relationship:"))
        ctx_combo = QComboBox()
        contexts = [
            WorkContextType.CURRENT_EMPLOYMENT,
            WorkContextType.PREVIOUS_EMPLOYMENT,
            WorkContextType.RESEARCH,
            WorkContextType.CONSULTING,
            WorkContextType.FREELANCE,
            WorkContextType.ACADEMIC,
            WorkContextType.GOVERNMENT,
            WorkContextType.PRIVATE_COMPANY,
            WorkContextType.NONPROFIT,
            WorkContextType.CLIENT_WORK,
        ]
        ctx_combo.addItems(contexts)
        if activity and activity.work_context in contexts:
            ctx_combo.setCurrentText(activity.work_context)
        vbox.addWidget(ctx_combo)

        # Role
        vbox.addWidget(QLabel("Role / Job Title:"))
        role_in = QLineEdit(activity.role if activity else "")
        vbox.addWidget(role_in)

        # Dates
        dates_row = QHBoxLayout()
        dates_row.addWidget(QLabel("Start Year:"))
        start_spin = QSpinBox()
        start_spin.setRange(1970, 2035)
        start_spin.setValue(activity.start_year if (activity and activity.start_year) else 2021)
        dates_row.addWidget(start_spin)

        dates_row.addWidget(QLabel("End Year:"))
        end_spin = QSpinBox()
        end_spin.setRange(1970, 2035)
        end_spin.setValue(activity.end_year if (activity and activity.end_year) else 2024)
        dates_row.addWidget(end_spin)

        curr_check = QCheckBox("Current (Present)")
        curr_check.setChecked(activity.is_current if activity else False)
        dates_row.addWidget(curr_check)
        vbox.addLayout(dates_row)

        # Domains
        vbox.addWidget(QLabel("Associated Domains (comma-separated):"))
        domains_in = QLineEdit(", ".join(activity.domains) if activity else "")
        vbox.addWidget(domains_in)

        # Projects
        vbox.addWidget(QLabel("Key Projects (comma-separated):"))
        proj_in = QLineEdit(", ".join(activity.projects) if activity else "")
        vbox.addWidget(proj_in)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        cancel_b = QPushButton("Cancel")
        cancel_b.clicked.connect(diag.reject)
        btns.addWidget(cancel_b)

        save_b = QPushButton("Save Activity")
        save_b.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
        save_b.clicked.connect(diag.accept)
        btns.addWidget(save_b)
        vbox.addLayout(btns)

        if diag.exec() == QDialog.DialogCode.Accepted:
            org = org_in.text().strip()
            if not org:
                return
            new_act = ProfessionalActivity(
                organization=org,
                work_context=ctx_combo.currentText(),
                role=role_in.text().strip(),
                start_year=start_spin.value(),
                end_year=None if curr_check.isChecked() else end_spin.value(),
                is_current=curr_check.isChecked(),
                domains=[d.strip() for d in domains_in.text().split(",") if d.strip()],
                projects=[p.strip() for p in proj_in.text().split(",") if p.strip()],
            )
            if edit_index >= 0:
                self._activities[edit_index] = new_act
            else:
                self._activities.append(new_act)
            self._refresh_all_views()

    # ------------------------------------------------------------------
    # CV Parsing & Candidate Review (Section 21.2)
    # ------------------------------------------------------------------

    def _on_browse_cv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CV or Résumé File",
            str(Path.home()),
            "CV Documents (*.pdf *.docx *.txt *.md)",
        )
        if file_path:
            self._cv_path_input.setText(file_path)

    def _on_extract_cv(self) -> None:
        path_str = self._cv_path_input.text().strip()
        if not path_str:
            QMessageBox.warning(self, "No File", "Please select a CV file first.")
            return

        cv_file = Path(path_str)
        if not cv_file.exists():
            QMessageBox.warning(self, "Not Found", f"File does not exist: {cv_file}")
            return

        try:
            res = self._cv_parser.parse_file(cv_file)
            self._parsed_candidates = res

            # Populate candidates table
            self._candidates_table.setRowCount(0)
            row = 0

            for act in res.activities:
                self._candidates_table.insertRow(row)
                self._candidates_table.setItem(row, 0, QTableWidgetItem("🏢 Experience"))
                self._candidates_table.setItem(row, 1, QTableWidgetItem(act.organization))
                self._candidates_table.setItem(row, 2, QTableWidgetItem(f"{act.role} ({act.work_context})"))
                self._candidates_table.setItem(row, 3, QTableWidgetItem(act.period_display))
                self._candidates_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, ("activity", act))
                row += 1

            for edu in res.education:
                self._candidates_table.insertRow(row)
                self._candidates_table.setItem(row, 0, QTableWidgetItem("🎓 Education"))
                self._candidates_table.setItem(row, 1, QTableWidgetItem(edu.institution))
                self._candidates_table.setItem(row, 2, QTableWidgetItem(edu.degree))
                self._candidates_table.setItem(row, 3, QTableWidgetItem(str(edu.end_year or "—")))
                self._candidates_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, ("education", edu))
                row += 1

            # Option to delete source file
            if self._delete_cv_check.isChecked():
                self._cv_parser.securely_delete_source_file(cv_file)
                self._cv_path_input.setText(f"[Deleted source file for privacy: {cv_file.name}]")

            QMessageBox.information(
                self,
                "CV Parsing Completed",
                f"Successfully parsed CV offline!\nExtracted {len(res.activities)} career role(s) "
                f"and {len(res.education)} educational qualification(s).\n\n"
                "Review candidates in the table below and click 'Accept' to add them to your profile.",
            )

        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", f"Failed to extract CV: {e}")

    def _on_accept_candidate(self) -> None:
        row = self._candidates_table.currentRow()
        if row < 0:
            return
        item = self._candidates_table.item(row, 0)
        if not item:
            return
        c_type, data = item.data(Qt.ItemDataRole.UserRole)
        if c_type == "activity":
            self._activities.append(data)
        elif c_type == "education":
            self._education.append(data)
        self._candidates_table.removeRow(row)
        self._refresh_all_views()

    def _on_accept_all_candidates(self) -> None:
        if not self._parsed_candidates:
            return
        for act in self._parsed_candidates.activities:
            if not any(a.organization.lower() == act.organization.lower() for a in self._activities):
                self._activities.append(act)
        for edu in self._parsed_candidates.education:
            self._education.append(edu)
        for dom in self._parsed_candidates.domains:
            if not any(d.category.lower() == dom.lower() for d in self._domains):
                self._domains.append(DomainSpec(category=dom, subcategories=["General"], keywords=[dom.lower()]))
        self._candidates_table.setRowCount(0)
        self._refresh_all_views()
        QMessageBox.information(self, "Accepted", "All candidate activities and education have been added to your profile!")

    # ------------------------------------------------------------------
    # Discovery Operations (Section 21.10)
    # ------------------------------------------------------------------

    def _on_add_discovered(self) -> None:
        row = self._discovery_table.currentRow()
        if 0 <= row < len(self._discovered):
            disc = self._discovered[row]
            if disc.entity_type == "organization":
                self._activities.append(ProfessionalActivity(
                    organization=disc.name,
                    work_context=disc.proposed_role_or_context,
                    role="Discovered Activity",
                ))
            else:
                self._domains.append(DomainSpec(
                    category=disc.name,
                    subcategories=["General"],
                    keywords=[disc.name.lower()],
                ))
            del self._discovered[row]
            self._refresh_all_views()

    def _on_ignore_discovered(self) -> None:
        row = self._discovery_table.currentRow()
        if 0 <= row < len(self._discovered):
            del self._discovered[row]
            self._refresh_all_views()

    # ------------------------------------------------------------------
    # Presets & Save
    # ------------------------------------------------------------------

    def _on_preset_dropdown_changed(self, idx: int) -> None:
        data = self._preset_combo.currentData()
        if data == "phd":
            self._apply_preset(PROFILE_PHD_AI_INSURTECH_HEALTH)
        elif data == "academic":
            self._apply_preset(PROFILE_GENERAL_ACADEMIC)
        elif data == "zero":
            self._activities = []
            self._domains = []
            self._refresh_all_views()

    def _apply_preset(self, profile: UserProfile) -> None:
        self._activities = list(profile.activities)
        self._domains = list(profile.domains)
        self._education = list(profile.education)
        self._personal_categories = list(profile.personal_categories)
        self._learning_interests = list(profile.learning_interests)
        self._learning_input.setText(", ".join(self._learning_interests))
        self._refresh_all_views()

    def _on_reset_profile(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset Profile",
            "Do you want to reset your profile to the default PhD / Insurtech / Health preset?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._apply_preset(PROFILE_PHD_AI_INSURTECH_HEALTH)

    def _on_save_and_apply(self) -> None:
        # Collect learning interests
        learn_raw = self._learning_input.text()
        learning_list = [l.strip() for l in learn_raw.split(",") if l.strip()]

        # Collect personal categories
        selected_personal = [cat for cat, cb in self._personal_checkboxes.items() if cb.isChecked()]

        profile = UserProfile(
            name=f"Profile ({len(self._activities)} activities, {len(self._domains)} domains)",
            description="Configured via Profile Setup Assistant",
            mode="rich" if self._activities else ("basic" if self._domains else "zero"),
            activities=self._activities,
            education=self._education,
            personal_categories=selected_personal,
            learning_interests=learning_list,
            domains=self._domains,
        )

        # Save to config.json
        try:
            config_path = get_config_path()
            config_data = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            config_data["user_profile"] = profile.to_dict()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
        except Exception:
            pass

        self._active_profile = profile
        self.profile_changed.emit(profile)
        self.accept()

    def get_profile(self) -> UserProfile:
        return self._active_profile
