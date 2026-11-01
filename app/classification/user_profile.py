"""User Profile Knowledge Graph and Multi-Activity Personalization module.

Implements Section 21:
- "Work is a context, not a domain" (multiple employers, roles, projects, domains).
- Three fundamental dimensions: Context (Scope), Relationship, and Content.
- Knowledge Graph representing Organizations, Roles, Periods, Projects, Skills, and Education.
- Professional Activity Profiles (Current, Previous, Research, Consulting, Freelance).
- Context disambiguation: Work vs Learning vs Training vs Reference vs Personal.
- Zero Profile, Basic Profile, and Rich Profile modes.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.utils.app_logging import get_logger

logger = get_logger("classification.profile")


# ===========================================================================
# Core Enums / Constants
# ===========================================================================

class WorkContextType:
    CURRENT_EMPLOYMENT = "Current Employment"
    PREVIOUS_EMPLOYMENT = "Previous Employment"
    CONSULTING = "Consulting"
    FREELANCE = "Freelance"
    RESEARCH = "Research"
    ACADEMIC = "Academic Work"
    GOVERNMENT = "Government / Public Administration"
    PRIVATE_COMPANY = "Private Company"
    NONPROFIT = "Nonprofit / NGO"
    INTERNATIONAL_ORG = "International Organization"
    CLIENT_WORK = "Client Work"
    ASSOCIATION = "Professional Association"
    ENTREPRENEURSHIP = "Business / Entrepreneurship"
    UNKNOWN = "Unknown"


class ScopeType:
    WORK = "Work"
    PERSONAL = "Personal"
    LEARNING = "Learning"
    TRAINING = "Training"
    REFERENCE = "Reference"
    UNKNOWN = "Unknown"


# Default Personal Document Categories (Section 21.1)
DEFAULT_PERSONAL_CATEGORIES = [
    "Finance & Banking",
    "Taxes & Fiscal",
    "Health & Medical",
    "Housing & Property",
    "Insurance (Personal)",
    "Identity & Legal",
    "Travel & Transport",
    "Family & Civil",
    "Vehicles & Automotive",
    "Administrative",
]


# ===========================================================================
# Data Structures
# ===========================================================================

@dataclass
class ProfessionalActivity:
    """A distinct professional role, employer, research project, or consulting activity."""
    organization: str
    work_context: str = WorkContextType.CURRENT_EMPLOYMENT
    role: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: bool = False
    domains: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    strong_markers: list[str] = field(default_factory=list)
    weight_multiplier: float = 2.0

    @property
    def period_display(self) -> str:
        if self.start_year and self.is_current:
            return f"{self.start_year}–Present"
        elif self.start_year and self.end_year:
            return f"{self.start_year}–{self.end_year}"
        elif self.start_year:
            return str(self.start_year)
        elif self.is_current:
            return "Current"
        return "Unspecified"


@dataclass
class EducationEntry:
    """Educational qualification, degree, or research program."""
    institution: str
    degree: str
    field_of_study: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None


@dataclass
class DomainSpec:
    """Specification of a specific domain of work (kept for category-level rule matching)."""
    category: str
    subcategories: list[str]
    keywords: list[str]
    strong_markers: list[str] = field(default_factory=list)
    weight_multiplier: float = 1.8
    subcategory_keywords: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class UserProfile:
    """Complete User Profile Knowledge Graph (Section 21).

    Maintains relationships between People, Organizations, Roles, Domains,
    Projects, Skills, Education, and Time periods.
    """
    name: str
    description: str = ""
    mode: str = "rich"  # "zero", "basic", "rich"
    activities: list[ProfessionalActivity] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    personal_categories: list[str] = field(default_factory=lambda: list(DEFAULT_PERSONAL_CATEGORIES))
    learning_interests: list[str] = field(default_factory=list)
    domains: list[DomainSpec] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        activities = []
        for a in data.get("activities", []):
            activities.append(ProfessionalActivity(
                organization=a.get("organization", ""),
                work_context=a.get("work_context", WorkContextType.CURRENT_EMPLOYMENT),
                role=a.get("role", ""),
                start_year=a.get("start_year"),
                end_year=a.get("end_year"),
                is_current=a.get("is_current", False),
                domains=a.get("domains", []),
                projects=a.get("projects", []),
                skills=a.get("skills", []),
                strong_markers=a.get("strong_markers", []),
                weight_multiplier=a.get("weight_multiplier", 2.0),
            ))

        education = []
        for e in data.get("education", []):
            education.append(EducationEntry(
                institution=e.get("institution", ""),
                degree=e.get("degree", ""),
                field_of_study=e.get("field_of_study", ""),
                start_year=e.get("start_year"),
                end_year=e.get("end_year"),
            ))

        domains = []
        for d in data.get("domains", []):
            domains.append(DomainSpec(
                category=d.get("category", "General"),
                subcategories=d.get("subcategories", []),
                keywords=d.get("keywords", []),
                strong_markers=d.get("strong_markers", []),
                weight_multiplier=d.get("weight_multiplier", 1.8),
                subcategory_keywords=d.get("subcategory_keywords", {}),
            ))

        return cls(
            name=data.get("name", "Default Profile"),
            description=data.get("description", ""),
            mode=data.get("mode", "rich" if activities or domains else "zero"),
            activities=activities,
            education=education,
            personal_categories=data.get("personal_categories", list(DEFAULT_PERSONAL_CATEGORIES)),
            learning_interests=data.get("learning_interests", []),
            domains=domains,
        )

    # ------------------------------------------------------------------
    # Knowledge Graph Matching & Inference
    # ------------------------------------------------------------------

    def match_activity(
        self,
        text: str,
        filename: str = "",
        year: Optional[str] = None,
    ) -> Optional[tuple[ProfessionalActivity, float, dict[str, float]]]:
        """Match document text against the user's professional activities.

        Calculates signals as specified in Section 21.9:
        - Organization match (+0.35)
        - Known project alias (+0.25)
        - Professional domain / skill similarity (+0.18)
        - Professional role context (+0.15)
        - Employment-period / temporal consistency (+0.08)

        Returns:
            Tuple of (matched_activity, total_score, signals_breakdown) or None.
        """
        if not self.activities:
            return None

        clean_text = (filename + " " + text[:3000]).lower()
        doc_year = int(year) if (year and year.isdigit()) else None

        best_activity: Optional[ProfessionalActivity] = None
        best_score = 0.0
        best_signals: dict[str, float] = {}

        for act in self.activities:
            signals: dict[str, float] = {}
            score = 0.0

            # 1. Organization match (+0.35)
            org_lower = act.organization.lower()
            if org_lower and len(org_lower) > 2:
                # Check for exact name or word boundaries
                if org_lower in clean_text:
                    signals["organization_match"] = 0.35
                    score += 0.35
                else:
                    # Acronym check (e.g. OMS, WHO, ANSM)
                    words = org_lower.split()
                    if len(words) > 1:
                        acronym = "".join(w[0] for w in words if w)
                        if len(acronym) >= 3 and re.search(r'\b' + re.escape(acronym) + r'\b', clean_text):
                            signals["organization_match"] = 0.30
                            score += 0.30

            # 2. Known project alias (+0.25)
            for proj in act.projects:
                proj_lower = proj.lower()
                if proj_lower and len(proj_lower) > 3 and proj_lower in clean_text:
                    signals["project_match"] = 0.25
                    score += 0.25
                    break

            # 3. Role context (+0.15)
            if act.role:
                role_lower = act.role.lower()
                # Check keywords in role
                role_words = [w for w in role_lower.split() if len(w) > 3]
                if any(rw in clean_text for rw in role_words):
                    signals["role_match"] = 0.15
                    score += 0.15

            # 4. Domain / skill similarity (+0.18)
            matched_skills = [
                s for s in (act.skills + act.domains)
                if s and len(s) > 2 and s.lower() in clean_text
            ]
            if matched_skills:
                skill_score = min(0.18, len(matched_skills) * 0.06)
                signals["domain_similarity"] = skill_score
                score += skill_score

            # 5. Temporal consistency (+0.08)
            if doc_year is not None:
                start = act.start_year or 1990
                end = 2099 if act.is_current else (act.end_year or 2099)
                if start <= doc_year <= end:
                    signals["temporal_consistency"] = 0.08
                    score += 0.08

            if score > best_score:
                best_score = score
                best_activity = act
                best_signals = signals

        if best_activity and best_score >= 0.25:
            return best_activity, best_score, best_signals
        return None

    def detect_scope(
        self,
        text: str,
        filename: str = "",
        doc_type: str = "",
        matched_activity: Optional[ProfessionalActivity] = None,
    ) -> tuple[str, float, str]:
        """Determine CONTEXT: 'Why do I have this document?' (Section 21.11).

        Distinguishes between:
        - Work
        - Learning
        - Training
        - Reference
        - Personal

        Returns:
            Tuple of (scope, confidence, reason).
        """
        combined = (filename + " " + text[:2500]).lower()

        # 1. Learning (Course, syllabus, assignment, university lecture)
        learning_markers = [
            "syllabus", "lecture notes", "course syllabus", "homework assignment",
            "cours magistral", "travaux dirigés", "td ", "tp noté", "examen final",
            "coursera", "edx", "udemy", "tutorial", "slides for chapter", "lecture 1",
            "lecture 2", "introduction to machine learning course"
        ]
        if any(m in combined for m in learning_markers):
            return ScopeType.LEARNING, 0.90, "Identified learning/course materials or academic syllabus."

        # 2. Training (Certificate of completion, attestation, workshop)
        training_markers = [
            "certificate of completion", "certificate of attendance", "attestation de formation",
            "attestation de stage", "certificat de réussite", "certificat d'aptitude",
            "professional development certificate", "workshop attendance", "ceus earned"
        ]
        if any(m in combined for m in training_markers):
            return ScopeType.TRAINING, 0.92, "Identified training certificate or course completion document."

        # 3. Personal (Taxes, medical prescriptions, personal banking, lease, identity)
        personal_markers = [
            "avis d'impôt", "avis d'imposition", "déclaration de revenus", "tax return 1040",
            "ordonnance médicale", "carte vitale", "feuille de soins", "sécurité sociale relevé",
            "bail d'habitation", "quittance de loyer", "contrat de bail", "relevé de compte personnel",
            "passeport", "carte nationale d'identité", "acte de naissance", "livret de famille"
        ]
        if any(m in combined for m in personal_markers):
            return ScopeType.PERSONAL, 0.94, "Identified personal, civil, tax, or medical document."

        # 4. Reference (Published scientific paper, ISO standard, official manual with DOI/arXiv)
        # Only if NOT matching an internal company project or user's active employer
        reference_markers = [
            "doi:10.", "arxiv:", "ieee transactions", "acm computing surveys",
            "proceedings of the", "published by elsevier", "springer nature",
            "rfc ", "ietf", "iso/iec standard"
        ]
        is_published = any(m in combined for m in reference_markers)
        if is_published:
            # If user's employer or specific internal project is NOT mentioned, it's a reference publication!
            if matched_activity is None or matched_activity.work_context == WorkContextType.RESEARCH:
                if "internal report" not in combined and "confidential" not in combined:
                    return ScopeType.REFERENCE, 0.88, "Identified scientific publication or standard reference document."

        # 5. Work (Internal company report, specifications, meeting minutes, invoices, client work)
        return ScopeType.WORK, 0.85, "Identified professional work, project, or organizational document."


# ===========================================================================
# Pre-configured Profiles
# ===========================================================================

PROFILE_PHD_AI_INSURTECH_HEALTH = UserProfile(
    name="PhD in XAI, Insurtech Data Scientist & Sécurité Sanitaire Engineer",
    description="Multi-activity profile representing research in Explainable AI, Insurtech actuarial analytics, and health safety engineering.",
    mode="rich",
    activities=[
        # Activity 1: Research in Explainable AI
        ProfessionalActivity(
            organization="University / Research Lab",
            work_context=WorkContextType.RESEARCH,
            role="PhD Researcher & AI Engineer",
            is_current=True,
            domains=["Research", "Explainable AI (XAI)", "Machine Learning", "Deep Learning"],
            projects=["XAI Framework", "SHAP Interpretability Benchmark", "Counterfactual Analysis"],
            skills=[
                "explainable ai", "xai", "shap", "shapley values", "lime",
                "counterfactual", "integrated gradients", "interpretability",
                "deep learning", "neural network", "transformer", "pytorch",
                "neurips", "icml", "iclr", "cvpr", "attribution",
            ],
            strong_markers=["explainable ai", "xai", "shapley values", "counterfactual explanation", "neurips"],
            weight_multiplier=2.2,
        ),

        # Activity 2: Data Scientist in Insurtech
        ProfessionalActivity(
            organization="Insurtech Company",
            work_context=WorkContextType.PRIVATE_COMPANY,
            role="Data Scientist",
            is_current=False,
            start_year=2021,
            end_year=2024,
            domains=["Insurtech", "Insurance", "Risk Modeling & Actuarial"],
            projects=["Claims Fraud Model", "Loss Ratio Prediction", "Solvency II Platform"],
            skills=[
                "insurtech", "actuarial", "claims", "claim frequency", "claim severity",
                "risk modeling", "fraud detection", "tarification", "sinistre",
                "solvency ii", "solvabilité ii", "ifrs 17", "loss ratio", "ratio combiné",
            ],
            strong_markers=["insurtech", "solvency ii", "solvabilité ii", "ifrs 17", "fraude à l'assurance"],
            weight_multiplier=2.0,
        ),

        # Activity 3: Étude & Dév en Sécurité Sanitaire
        ProfessionalActivity(
            organization="Sécurité Sanitaire Company",
            work_context=WorkContextType.PRIVATE_COMPANY,
            role="Étude et Dév Engineer",
            is_current=False,
            start_year=2018,
            end_year=2021,
            domains=["Sécurité Sanitaire", "Dispositifs Médicaux", "Veille Sanitaire"],
            projects=["Dossier Technique Marquage CE", "Validation Logicielle Dispositifs Médicaux", "ISO 13485 Compliance"],
            skills=[
                "sécurité sanitaire", "dispositifs médicaux", "medical devices",
                "iso 13485", "iso 14971", "marquage ce", "mdr", "règlement 2017/745",
                "évaluation clinique", "analyse de risques", "matériovigilance", "veille sanitaire",
            ],
            strong_markers=["sécurité sanitaire", "dispositifs médicaux", "iso 13485", "iso 14971", "matériovigilance"],
            weight_multiplier=2.0,
        ),
    ],
    education=[
        EducationEntry(
            institution="University Paris-Saclay",
            degree="Doctor of Philosophy (PhD)",
            field_of_study="Explainable Artificial Intelligence & Machine Learning",
        ),
        EducationEntry(
            institution="Engineering School",
            degree="Master of Science in Engineering",
            field_of_study="Data Science & Software Engineering",
        ),
    ],
    personal_categories=list(DEFAULT_PERSONAL_CATEGORIES),
    learning_interests=["Deep Learning", "Generative AI", "Cloud Architecture"],
    domains=[
        DomainSpec(
            category="Research",
            subcategories=["Explainable AI (XAI)", "Machine Learning", "Deep Learning", "Conference Papers", "Theses & Dissertations"],
            keywords=["explainable ai", "xai", "shap", "lime", "counterfactual", "neurips", "icml", "deep learning"],
            strong_markers=["explainable ai", "xai", "shapley values", "neurips"],
            weight_multiplier=2.2,
            subcategory_keywords={
                "Explainable AI (XAI)": ["explainable ai", "xai", "interpretability", "feature attribution", "shap", "lime", "counterfactual"],
                "Conference Papers": ["neurips", "icml", "iclr", "cvpr", "aaai"],
                "Deep Learning": ["deep learning", "neural network", "transformer", "attention mechanism"],
                "Machine Learning": ["machine learning", "supervised learning", "unsupervised learning"],
                "Theses & Dissertations": ["thesis", "dissertation", "thèse", "phd"],
            },
        ),
        DomainSpec(
            category="Insurtech",
            subcategories=["Claims & Fraud Detection", "Risk Modeling & Actuarial", "Underwriting & Pricing", "Analytics & Metrics", "Regulatory & Solvency"],
            keywords=["insurtech", "actuarial", "claims", "fraud detection", "tarification", "sinistre", "solvency ii"],
            strong_markers=["insurtech", "solvency ii", "fraude à l'assurance"],
            weight_multiplier=2.0,
            subcategory_keywords={
                "Claims & Fraud Detection": ["claims", "claim frequency", "fraud detection", "fraude à l'assurance", "sinistre"],
                "Risk Modeling & Actuarial": ["risk modeling", "actuarial", "loss ratio", "actuariat", "provisionnement"],
                "Underwriting & Pricing": ["underwriting", "pricing", "tarification", "souscription", "prime d'assurance"],
                "Regulatory & Solvency": ["solvency ii", "solvabilité ii", "ifrs 17", "rgpd"],
                "Analytics & Metrics": ["telematics", "churn prediction", "ratio combiné"],
            },
        ),
        DomainSpec(
            category="Sécurité Sanitaire",
            subcategories=["Dispositifs Médicaux", "Normes & Qualité (ISO/HACCP)", "Veille & Risques Sanitaires", "Étude et Développement"],
            keywords=["sécurité sanitaire", "dispositifs médicaux", "iso 13485", "iso 14971", "marquage ce", "mdr"],
            strong_markers=["sécurité sanitaire", "dispositifs médicaux", "iso 13485", "matériovigilance"],
            weight_multiplier=2.0,
            subcategory_keywords={
                "Dispositifs Médicaux": ["dispositifs médicaux", "medical devices", "marquage ce", "mdr", "évaluation clinique"],
                "Normes & Qualité (ISO/HACCP)": ["iso 13485", "iso 14971", "haccp", "normes", "qualité"],
                "Veille & Risques Sanitaires": ["veille sanitaire", "matériovigilance", "biovigilance", "risque microbiologique"],
                "Étude et Développement": ["cahier des charges", "spécifications techniques", "dossier technique"],
            },
        ),
    ],
)

PROFILE_GENERAL_ACADEMIC = UserProfile(
    name="Academic Researcher & Scientist",
    description="Optimized for university research, peer-reviewed articles, grant proposals, and theses.",
    mode="basic",
    activities=[
        ProfessionalActivity(
            organization="University / Research Institute",
            work_context=WorkContextType.RESEARCH,
            role="Researcher / Scientist",
            is_current=True,
            domains=["Research", "Scientific Articles", "Grants & Proposals"],
            projects=["Research Grant", "Journal Publications"],
            skills=["peer-reviewed", "methodology", "doi:10.", "experiment", "references"],
            strong_markers=["doi:10.", "peer-reviewed", "grant proposal"],
            weight_multiplier=1.8,
        )
    ],
    domains=[
        DomainSpec(
            category="Research",
            subcategories=["Scientific Articles", "Grants & Proposals", "Theses", "Data & Benchmarks"],
            keywords=["abstract", "methodology", "doi:", "peer-reviewed", "journal", "experiment", "references"],
            strong_markers=["doi:10.", "peer-reviewed", "grant proposal"],
            weight_multiplier=1.8,
        )
    ],
)

PRESET_PROFILES: dict[str, UserProfile] = {
    "phd_xai_insurtech_health": PROFILE_PHD_AI_INSURTECH_HEALTH,
    "academic_research": PROFILE_GENERAL_ACADEMIC,
}


def get_default_profile() -> UserProfile:
    """Return the default tailored profile for the user."""
    return PROFILE_PHD_AI_INSURTECH_HEALTH
