"""Local Offline CV / Résumé Parser module (Section 21.2).

Extracts candidate professional activities, employers, roles, employment dates,
skills, domains, and education from a user-supplied CV or résumé.
Completely local and offline: no documents or text are ever transmitted externally.
Supports PDF, DOCX, and TXT files.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.classification.user_profile import (
    EducationEntry,
    ProfessionalActivity,
    WorkContextType,
)
from app.utils.app_logging import get_logger

logger = get_logger("extraction.cv")


@dataclass
class CVParsingResult:
    """Extracted profile candidates from a CV/résumé for user review."""
    activities: list[ProfessionalActivity] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    raw_text: str = ""
    source_path: Optional[Path] = None


class CVParser:
    """Local, offline CV and résumé parser."""

    DATE_RANGE_REGEX = re.compile(
        r'(\b(?:19|20)\d{2}\b)\s*(?:[-–—/]|to|à|au)\s*(\b(?:19|20)\d{2}\b|present|actuel|aujourd\'hui|en cours)',
        re.IGNORECASE,
    )
    SINGLE_YEAR_REGEX = re.compile(r'\b(19\d{2}|20\d{2})\b')
    SINCE_REGEX = re.compile(r'(?:since|depuis)\s*(\b(?:19|20)\d{2}\b)', re.IGNORECASE)

    COMMON_ROLES = [
        "Data Scientist", "Machine Learning Engineer", "AI Engineer", "Software Engineer",
        "PhD Researcher", "Researcher", "Research Fellow", "Postdoc",
        "Ingénieur Étude et Développement", "Ingénieur R&D", "Ingénieur Qualité",
        "Public Health Specialist", "Epidemiologist", "Clinical Research Associate",
        "Actuary", "Actuaire", "Risk Analyst", "Financial Analyst",
        "Project Manager", "Chef de Projet", "Consultant", "Tech Lead",
        "Architecte Logiciel", "DevOps Engineer", "Data Analyst",
    ]

    COMMON_DOMAINS = [
        "Explainable AI", "Machine Learning", "Deep Learning", "Artificial Intelligence",
        "Computer Vision", "Natural Language Processing", "NLP", "LLM",
        "Insurtech", "Insurance", "Actuarial Science", "Fraud Detection", "Risk Modeling",
        "Sécurité Sanitaire", "Health Security", "Dispositifs Médicaux", "Medical Devices",
        "Public Health", "Epidemiology", "Pharmacovigilance", "Biomedical Engineering",
        "Software Engineering", "Cloud Computing", "Cybersecurity",
    ]

    COMMON_SKILLS = [
        "Python", "PyTorch", "TensorFlow", "Scikit-Learn", "SHAP", "LIME", "R",
        "SQL", "Git", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
        "ISO 13485", "ISO 14971", "MDR 2017/745", "Marquage CE", "HACCP",
        "Solvency II", "Solvabilité II", "IFRS 17", "C++", "Java", "Linux",
    ]

    def parse_file(self, file_path: Path) -> CVParsingResult:
        """Parse a local CV file (PDF, DOCX, or TXT) and extract profile candidates."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"CV file not found: {path}")

        ext = path.suffix.lower()
        if ext == ".pdf":
            raw_text = self._extract_text_from_pdf(path)
        elif ext == ".docx":
            raw_text = self._extract_text_from_docx(path)
        elif ext in (".txt", ".md"):
            raw_text = self._extract_text_from_txt(path)
        else:
            raise ValueError(f"Unsupported CV file format '{ext}'. Supported: .pdf, .docx, .txt")

        return self._extract_candidates_from_text(raw_text, path)

    def _extract_text_from_pdf(self, path: Path) -> str:
        """Extract full text from PDF using PyMuPDF."""
        try:
            import fitz
        except ImportError:
            try:
                import pymupdf as fitz
            except ImportError:
                raise ImportError("PyMuPDF is required to parse PDF CVs.")

        doc = fitz.open(str(path))
        lines = []
        for page in doc:
            lines.append(page.get_text())
        doc.close()
        return "\n".join(lines)

    def _extract_text_from_docx(self, path: Path) -> str:
        """Extract text from DOCX using standard library zipfile and XML parsing."""
        with zipfile.ZipFile(str(path)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            # Find all text elements <w:t>
            texts = []
            for node in tree.iter():
                if node.tag.endswith("}t") and node.text:
                    texts.append(node.text)
                elif node.tag.endswith("}p"):
                    texts.append("\n")
            return "".join(texts)

    def _extract_text_from_txt(self, path: Path) -> str:
        """Extract text from TXT file with fallback encodings."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1", errors="replace")

    def _extract_candidates_from_text(self, text: str, source_path: Path) -> CVParsingResult:
        """Analyze text to extract candidate activities, education, and skills."""
        result = CVParsingResult(raw_text=text, source_path=source_path)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 1. Detect candidate professional activities
        activities: list[ProfessionalActivity] = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for date ranges (e.g. 2021-2024 or 2024-Present)
            date_match = self.DATE_RANGE_REGEX.search(line) or self.SINCE_REGEX.search(line)
            if date_match:
                start_yr = None
                end_yr = None
                is_curr = False

                if len(date_match.groups()) == 2:
                    start_yr = int(date_match.group(1))
                    end_str = date_match.group(2).lower()
                    if any(c in end_str for c in ("present", "actuel", "aujourd'hui", "en cours")):
                        is_curr = True
                    else:
                        try:
                            end_yr = int(end_str)
                        except ValueError:
                            end_yr = None
                elif len(date_match.groups()) == 1:
                    start_yr = int(date_match.group(1))
                    is_curr = True

                # Inspect surrounding lines (up to 2 before, 2 after) for Organization & Role
                candidate_role = ""
                candidate_org = ""

                surrounding = lines[max(0, i - 2): min(len(lines), i + 3)]
                for surr in surrounding:
                    for known_role in self.COMMON_ROLES:
                        if known_role.lower() in surr.lower():
                            candidate_role = known_role
                            break
                    if candidate_role:
                        break

                for surr in surrounding:
                    # Ignore the line with the date itself
                    if date_match.group(0) in surr:
                        continue
                    if candidate_role and candidate_role.lower() in surr.lower():
                        continue
                    # Organization heuristic: capitalized phrase, 3-40 chars
                    if len(surr) > 3 and len(surr) < 45 and not surr.endswith((".", ":", ";")):
                        candidate_org = surr
                        break

                if candidate_org or candidate_role:
                    org_name = candidate_org or "Professional Organization"
                    # Determine context
                    ctx = WorkContextType.CURRENT_EMPLOYMENT if is_curr else WorkContextType.PREVIOUS_EMPLOYMENT
                    if "universit" in org_name.lower() or "research" in candidate_role.lower() or "phd" in candidate_role.lower():
                        ctx = WorkContextType.RESEARCH

                    activities.append(ProfessionalActivity(
                        organization=org_name,
                        work_context=ctx,
                        role=candidate_role or "Professional Role",
                        start_year=start_yr,
                        end_year=end_yr,
                        is_current=is_curr,
                    ))

            i += 1

        # 2. Extract matched domains and skills
        found_domains = set()
        for d in self.COMMON_DOMAINS:
            if re.search(r'\b' + re.escape(d.lower()) + r'\b', text.lower()):
                found_domains.add(d)

        found_skills = set()
        for s in self.COMMON_SKILLS:
            if re.search(r'\b' + re.escape(s.lower()) + r'\b', text.lower()):
                found_skills.add(s)

        # Distribute detected domains & skills into extracted activities
        for act in activities:
            act.domains = list(found_domains)[:4]
            act.skills = list(found_skills)[:6]

        result.activities = activities
        result.domains = sorted(list(found_domains))
        result.skills = sorted(list(found_skills))

        # 3. Detect candidate education entries
        education_entries: list[EducationEntry] = []
        edu_keywords = ["phd", "doctorat", "master", "msc", "bachelor", "licence", "ingénieur", "diplôme"]
        for idx, line in enumerate(lines):
            line_lower = line.lower()
            if any(k in line_lower for k in edu_keywords):
                # Search year near this line
                year_match = self.SINGLE_YEAR_REGEX.search(line)
                yr = int(year_match.group(1)) if year_match else None

                inst = ""
                # Look 1 line above or below for university name
                for near in lines[max(0, idx - 1): min(len(lines), idx + 2)]:
                    if any(u in near.lower() for u in ("universit", "école", "college", "institute", "polytechnique", "faculty")):
                        inst = near
                        break

                education_entries.append(EducationEntry(
                    institution=inst or "Academic Institution",
                    degree=line[:60],
                    field_of_study="Higher Education",
                    end_year=yr,
                ))

        result.education = education_entries[:4]
        return result

    @staticmethod
    def securely_delete_source_file(file_path: Path) -> bool:
        """Optionally delete the source CV file after profile import for privacy."""
        try:
            p = Path(file_path).resolve()
            if p.exists() and p.is_file():
                p.unlink()
                logger.info("Securely deleted source CV file after import: %s", p)
                return True
        except Exception as e:
            logger.warning("Failed to delete source CV file %s: %s", file_path, e)
        return False
