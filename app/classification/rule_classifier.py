"""Comprehensive bilingual (English / French) multi-domain document classifier.

Features:
1. Multi-domain taxonomy:
   - Public Health (WHO/OMS, Epidemiology, Pharmacovigilance, Vaccines, Health Systems)
   - Administration (Invoices, Procurement, Contracts, Correspondence, HR)
   - Research & Science (Scientific Articles, Research Reports, Theses)
   - Legal & Regulatory (Laws, Decrees, Regulations, Directives, Compliance)
   - Strategy & Governance (Strategic Plans, Action Plans, Roadmaps, Frameworks)
   - Finance & Economy (Budgets, Financial Reports, Audits)
   - Guides & Technical (User Manuals, Procedures/SOPs, Specifications)
   - Meetings & Events (Minutes/Procès-Verbaux, Presentations, Agendas)
   - Personal & Civil (Identity, Insurance, Housing, Certificates)

2. Orthogonal Document Type Detection:
   Identifies document type independently of domain (Report, Strategy, Law,
   Regulation, Procedure, Meeting Document, Presentation, Invoice, Guide, etc.).

3. Multi-Zone Weighted Evidence Scoring:
   - Filename zone: 3.0x weight
   - Title / Header zone: 2.5x weight
   - Lead paragraph / Executive summary (first 600 chars): 1.8x weight
   - Body text: 1.0x weight

4. Bilingual French & English recognition with organization alias normalization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from app.classification.user_profile import UserProfile, get_default_profile
from app.database.models import (
    ClassificationResult,
    PDFContent,
    PDFFileInfo,
    PDFMetadata,
)
from app.utils.app_logging import get_logger

logger = get_logger("classification.rules")


# ===========================================================================
# Taxonomy: (Keywords, Category, Subcategory, Primary Doc Type)
# ===========================================================================

_DOMAIN_TAXONOMY: list[dict] = [
    # ── Public Health / Santé Publique ──
    {
        "category": "Public Health",
        "subcategory": "WHO",
        "default_type": "WHO Document",
        "keywords": [
            "world health organization", "who", "wha", "health assembly",
            "executive board", "director-general", "organisation mondiale de la santé",
            "oms", "assemblée mondiale de la santé", "conseil exécutif",
            "directeur général", "a78/", "a77/", "a76/", "eb154/", "eb152/",
        ],
        "strong_markers": ["a78/", "a77/", "wha", "eb154/", "organisation mondiale de la santé", "world health organization"],
    },
    {
        "category": "Public Health",
        "subcategory": "Epidemiology",
        "default_type": "Epidemiology Report",
        "keywords": [
            "epidemiology", "epidemiological", "epidemic", "pandemic", "outbreak",
            "surveillance", "transmission", "pathogen", "infectious disease",
            "incidence", "prevalence", "morbidity", "mortality rate",
            "épidémiologie", "épidémiologique", "épidémie", "pandémie",
            "flambée", "surveillance épidémiologique", "maladie infectieuse",
            "taux d'incidence", "prévalence", "morbidité", "mortalité",
            "veille sanitaire", "alerte sanitaire",
        ],
        "strong_markers": ["bulletin épidémiologique", "surveillance épidémiologique", "epidemiological record", "outbreak surveillance"],
    },
    {
        "category": "Public Health",
        "subcategory": "Pharmacovigilance",
        "default_type": "Safety Report",
        "keywords": [
            "pharmacovigilance", "adverse drug reaction", "drug safety",
            "adverse event", "adr", "post-marketing surveillance", "pv",
            "risk management plan", "signal detection", "side effects",
            "pharmacovigilance", "effets indésirables", "sécurité du médicament",
            "événement indésirable", "surveillance post-commercialisation",
            "plan de gestion des risques", "pgr", "détection de signaux",
            "tolérance médicamenteuse", "iatrogénie",
        ],
        "strong_markers": ["pharmacovigilance", "adverse drug reaction", "effets indésirables", "plan de gestion des risques"],
    },
    {
        "category": "Public Health",
        "subcategory": "Vaccination",
        "default_type": "Vaccination Report",
        "keywords": [
            "vaccination", "vaccine", "immunization", "booster dose", "efficacy",
            "vaccinal coverage", "vaccine schedule", "antigen", "mrna",
            "vaccination", "vaccin", "immunisation", "couverture vaccinale",
            "calendrier vaccinal", "dose de rappel", "immunogénicité",
        ],
        "strong_markers": ["calendrier vaccinal", "vaccine schedule", "couverture vaccinale", "immunization coverage"],
    },
    {
        "category": "Public Health",
        "subcategory": "Health Systems",
        "default_type": "Health Policy Document",
        "keywords": [
            "health system", "universal health coverage", "primary health care",
            "hospital", "healthcare delivery", "sanitary crisis", "patient safety",
            "système de santé", "couverture santé universelle", "csu",
            "soins de santé primaires", "hôpital", "sécurité des patients",
            "parcours de soins", "offre de soins", "organisation des soins",
        ],
        "strong_markers": ["couverture santé universelle", "universal health coverage", "soins de santé primaires"],
    },

    # ── Research & Science / Recherche & Sciences ──
    {
        "category": "Research",
        "subcategory": "Scientific Articles",
        "default_type": "Scientific Article",
        "keywords": [
            "abstract", "introduction", "materials and methods", "methodology",
            "results", "discussion", "references", "doi:", "peer-reviewed",
            "journal", "pmid:", "author affiliations", "acknowledgments",
            "résumé", "matériel et méthodes", "méthodologie", "résultats",
            "références bibliographiques", "revue scientifique", "article scientifique",
        ],
        "strong_markers": ["doi:10.", "pmid:", "arxiv:", "materials and methods", "matériel et méthodes"],
    },
    {
        "category": "Research",
        "subcategory": "Reports",
        "default_type": "Research Paper",
        "keywords": [
            "research report", "study report", "scientific findings",
            "investigation report", "working paper", "preliminary study",
            "rapport de recherche", "rapport d'étude", "document de travail",
            "étude clinique", "enquête scientifique",
        ],
        "strong_markers": ["rapport de recherche", "research report", "working paper"],
    },
    {
        "category": "Research",
        "subcategory": "Theses",
        "default_type": "Thesis",
        "keywords": [
            "doctoral thesis", "phd thesis", "dissertation", "master thesis",
            "thèse de doctorat", "mémoire de master", "soutenance",
            "directeur de thèse", "jury de thèse",
        ],
        "strong_markers": ["thèse de doctorat", "doctoral thesis", "phd thesis", "soutenu publiquement le"],
    },

    # ── Administration / Administration ──
    {
        "category": "Administration",
        "subcategory": "Invoices",
        "default_type": "Invoice",
        "keywords": [
            "invoice", "billing", "payment due", "total amount", "amount due",
            "tax invoice", "subtotal", "remittance", "iban", "swift",
            "facture", "facturation", "montant total", "total ttc", "total ht",
            "tva", "échéance de paiement", "bon de commande", "devis",
            "règlement", "coordonnées bancaires",
        ],
        "strong_markers": ["facture n°", "invoice no", "total ttc", "total ht", "amount due", "iban", "swift"],
    },
    {
        "category": "Administration",
        "subcategory": "Procurement",
        "default_type": "Procurement Document",
        "keywords": [
            "procurement", "tender", "bid", "rfp", "request for proposal",
            "bidding documents", "call for tenders", "vendor", "specifications",
            "marchés publics", "appel d'offres", "cahier des charges",
            "soumission", "dossier de consultation", "attribution du marché",
            "avis d'appel public", "cctp", "ccap",
        ],
        "strong_markers": ["appel d'offres", "request for proposal", "cahier des charges", "avis d'appel public", "tender notice"],
    },
    {
        "category": "Administration",
        "subcategory": "Contracts",
        "default_type": "Contract",
        "keywords": [
            "contract", "agreement", "terms and conditions", "signatories",
            "memorandum of understanding", "mou", "nda", "confidentiality",
            "contrat", "accord", "convention", "clauses", "signataires",
            "protocole d'accord", "accord-cadre", "avenant",
        ],
        "strong_markers": ["protocole d'accord", "accord-cadre", "memorandum of understanding", "entre les soussignés", "terms and conditions"],
    },
    {
        "category": "Administration",
        "subcategory": "Correspondence",
        "default_type": "Correspondence",
        "keywords": [
            "dear sir", "dear madam", "to whom it may concern", "sincerely",
            "regards", "letterhead", "correspondence",
            "monsieur le directeur", "madame la directrice", "veuillez agréer",
            "cordialement", "courrier", "lettre officielle", "accusé de réception",
        ],
        "strong_markers": ["veuillez agréer", "dear sir", "dear madam", "to whom it may concern", "accusé de réception"],
    },
    {
        "category": "Administration",
        "subcategory": "Human Resources",
        "default_type": "HR Document",
        "keywords": [
            "human resources", "recruitment", "job description", "payroll",
            "leave request", "employee", "onboarding", "performance review",
            "ressources humaines", "recrutement", "fiche de poste", "bulletin de paie",
            "demande de congés", "contrat de travail", "entretien annuel",
        ],
        "strong_markers": ["fiche de poste", "bulletin de paie", "contrat de travail", "job description", "payroll"],
    },

    # ── Legal & Regulatory / Juridique & Réglementaire ──
    {
        "category": "Legal",
        "subcategory": "Regulations",
        "default_type": "Regulation",
        "keywords": [
            "regulation", "regulatory", "compliance", "directive", "standard",
            "mandatory requirement", "enactment", "decree",
            "règlement", "réglementation", "conformité", "directive européenne",
            "décret", "arrêté", "circulaire", "norme", "disposition légale",
            "article 1er", "vu le code", "le ministre de",
        ],
        "strong_markers": ["décret n°", "arrêté du", "directive européenne", "vu le code", "règlement (ue)"],
    },
    {
        "category": "Legal",
        "subcategory": "Laws",
        "default_type": "Law",
        "keywords": [
            "legislation", "statute", "act of parliament", "legal framework",
            "penal code", "civil code", "constitutional",
            "loi n°", "législation", "texte de loi", "promulguée",
            "code pénal", "code civil", "code de la santé publique",
            "assemblée nationale", "sénat", "journal officiel",
        ],
        "strong_markers": ["loi n°", "journal officiel", "code de la santé publique", "act of parliament"],
    },

    # ── Strategy & Governance / Stratégie & Gouvernance ──
    {
        "category": "Strategy",
        "subcategory": "Strategic Plans",
        "default_type": "Strategy Document",
        "keywords": [
            "strategy", "strategic plan", "roadmap", "vision 2030", "vision 2025",
            "strategic priorities", "framework", "action plan", "milestones",
            "stratégie", "plan stratégique", "feuille de route", "axes stratégiques",
            "plan d'action", "orientations stratégiques", "objectifs stratégiques",
            "cadre stratégique", "schéma directeur",
        ],
        "strong_markers": ["plan stratégique", "strategic plan", "feuille de route", "roadmap", "schéma directeur"],
    },

    # ── Guides & Technical / Guides & Technique ──
    {
        "category": "Guides",
        "subcategory": "Manuals",
        "default_type": "Manual",
        "keywords": [
            "user guide", "user manual", "instruction manual", "quick start",
            "how to", "installation guide", "getting started", "handbook",
            "guide d'utilisation", "manuel utilisateur", "guide pratique",
            "notice d'utilisation", "prise en main", "guide d'installation",
        ],
        "strong_markers": ["user guide", "user manual", "guide d'utilisation", "manuel d'utilisation", "notice d'instructions"],
    },
    {
        "category": "Guides",
        "subcategory": "Procedures",
        "default_type": "Procedure",
        "keywords": [
            "procedure", "standard operating procedure", "sop", "protocol",
            "workflow", "step-by-step", "process flow", "operational guide",
            "procédure", "mode opératoire", "protocole opératoire",
            "consignes de sécurité", "procédure opérationnelle normalisée",
            "démarche qualité",
        ],
        "strong_markers": ["standard operating procedure", "mode opératoire", "protocole opératoire", "sop"],
    },

    # ── Meetings / Réunions ──
    {
        "category": "Meetings",
        "subcategory": "Meeting Documents",
        "default_type": "Meeting Document",
        "keywords": [
            "minutes", "meeting minutes", "agenda", "attendees", "board meeting",
            "committee", "action items", "adjournment",
            "procès-verbal", "compte-rendu", "ordre du jour", "participants",
            "relevé de décisions", "conseil d'administration", "séance",
            "comité de pilotage", "copil",
        ],
        "strong_markers": ["procès-verbal", "meeting minutes", "compte-rendu de réunion", "ordre du jour", "relevé de décisions"],
    },
    {
        "category": "Meetings",
        "subcategory": "Presentations",
        "default_type": "Presentation",
        "keywords": [
            "presentation", "slides", "powerpoint", "keynote", "slide 1",
            "webinar", "speaker", "diaporama", "présentation", "support de cours",
            "formation", "diapositive",
        ],
        "strong_markers": ["diaporama", "support de présentation", "slide deck", "presentation slides"],
    },

    # ── Finance / Finance ──
    {
        "category": "Finance",
        "subcategory": "Reports",
        "default_type": "Financial Report",
        "keywords": [
            "financial report", "fiscal year", "budget", "balance sheet",
            "income statement", "cash flow", "audit report", "expenditure",
            "rapport financier", "exercice fiscal", "bilan comptable",
            "compte de résultat", "flux de trésorerie", "audit financier",
            "budget prévisionnel", "dépenses", "recettes",
        ],
        "strong_markers": ["bilan comptable", "compte de résultat", "financial statements", "rapport financier"],
    },

    # ── Personal & Civil / Personnel & Vie Quotidienne ──
    {
        "category": "Personal",
        "subcategory": "Certificates",
        "default_type": "Certificate",
        "keywords": [
            "certificate", "certification", "attestation", "diploma",
            "attestation sur l'honneur", "certificat médical", "justificatif",
            "attestation d'assurance", "relevé de notes",
        ],
        "strong_markers": ["attestation sur l'honneur", "certificat médical", "certificate of completion"],
    },
]

# ===========================================================================
# Explicit Document Type Patterns (Orthogonal to Domain)
# ===========================================================================

_DOCUMENT_TYPES: list[tuple[str, list[str]]] = [
    ("WHO Document", ["world health organization", "organisation mondiale de la santé", "wha", "eb154", "eb152", "a78/", "a77/"]),
    ("Scientific Article", ["doi:10.", "abstract", "résumé", "materials and methods", "matériel et méthodes", "peer-review", "references cited"]),
    ("Strategy", ["strategic plan", "plan stratégique", "feuille de route", "roadmap", "vision 2030", "orientations stratégiques"]),
    ("Regulation", ["décret", "arrêté", "directive", "règlement (ue)", "circulaire", "conformité réglementaire"]),
    ("Law", ["loi n°", "act of parliament", "code civil", "code pénal", "code de la santé"]),
    ("Procedure", ["standard operating procedure", "sop", "mode opératoire", "protocole opératoire", "procédure"]),
    ("Meeting Document", ["compte-rendu", "procès-verbal", "meeting minutes", "ordre du jour", "agenda"]),
    ("Presentation", ["diaporama", "presentation", "slides", "support de présentation"]),
    ("Invoice", ["facture", "invoice", "devis", "total ttc", "total ht", "amount due", "montant dû"]),
    ("Procurement Document", ["appel d'offres", "cahier des charges", "request for proposal", "tender", "marché public"]),
    ("Manual", ["user manual", "user guide", "manuel d'utilisation", "guide d'utilisation", "notice d'instructions"]),
    ("Contract", ["contrat", "accord-cadre", "protocole d'accord", "convention", "agreement", "memorandum of understanding"]),
    ("Financial Report", ["bilan comptable", "financial statement", "compte de résultat", "budget prévisionnel", "rapport financier"]),
    ("Correspondence", ["lettre", "courrier", "dear sir", "veuillez agréer", "accusé de réception"]),
    ("Report", ["rapport", "report", "bilan annuel", "annual report", "synthèse", "évaluation"]),
]

# ===========================================================================
# Organization Aliases & Normalization
# ===========================================================================

_ORG_ALIASES: dict[str, str] = {
    # Public Health / International
    "who": "World Health Organization",
    "oms": "World Health Organization",
    "world health organization": "World Health Organization",
    "organisation mondiale de la santé": "World Health Organization",
    "un": "United Nations",
    "onu": "United Nations",
    "united nations": "United Nations",
    "nations unies": "United Nations",
    "unicef": "UNICEF",
    "cdc": "CDC",
    "centers for disease control": "CDC",
    "fda": "FDA",
    "food and drug administration": "FDA",
    "ema": "European Medicines Agency (EMA)",
    "european medicines agency": "European Medicines Agency (EMA)",
    "agence européenne des médicaments": "European Medicines Agency (EMA)",
    "ansm": "ANSM",
    "agence nationale de sécurité du médicament": "ANSM",
    "has": "Haute Autorité de Santé (HAS)",
    "haute autorité de santé": "Haute Autorité de Santé (HAS)",
    "santé publique france": "Santé Publique France",
    "inserm": "Inserm",
    "cnrs": "CNRS",
    "ecdc": "ECDC",
    "pasteur": "Institut Pasteur",
    "institut pasteur": "Institut Pasteur",
    # Economics / Governance
    "oecd": "OECD",
    "ocde": "OECD",
    "world bank": "World Bank",
    "banque mondiale": "World Bank",
    "unesco": "UNESCO",
    "eu": "European Union",
    "ue": "European Union",
    "union européenne": "European Union",
}


class RuleClassifier:
    """Advanced bilingual (EN/FR) multi-domain document classifier with user profile guidance."""

    def __init__(self, user_profile: Optional[UserProfile] = None) -> None:
        self.user_profile: Optional[UserProfile] = user_profile

    def set_profile(self, profile: Optional[UserProfile]) -> None:
        """Update active user profile."""
        self.user_profile = profile

    def classify(
        self,
        file_info: PDFFileInfo,
        metadata: Optional[PDFMetadata],
        content: Optional[PDFContent],
    ) -> ClassificationResult:
        """Classify a PDF document using multi-zone weighted evidence scoring.

        Args:
            file_info: Basic file info (filename, size, path).
            metadata: PDF metadata (title, author, subject).
            content: Extracted textual content.

        Returns:
            Populated ClassificationResult with confidence score and explanation.
        """
        # 1. Prepare multi-zone text buckets
        filename_zone = file_info.filename.lower().replace("_", " ").replace("-", " ")
        parent_zone = file_info.path.parent.name.lower()

        title_zone = ""
        if metadata and metadata.title:
            title_zone += f" {metadata.title.lower()}"
        if metadata and metadata.subject:
            title_zone += f" {metadata.subject.lower()}"

        full_extracted = content.extracted_text.lower() if (content and content.extracted_text) else ""
        lead_zone = full_extracted[:600]
        body_zone = full_extracted[600:4000]

        # 2. Compile evaluation rules (User Profile domains first, then General Taxonomy)
        evaluation_rules: list[dict] = []
        if self.user_profile and self.user_profile.domains:
            for domain in self.user_profile.domains:
                for subcat in domain.subcategories:
                    # Prefer explicitly defined subcategory keywords if available
                    if domain.subcategory_keywords and subcat in domain.subcategory_keywords:
                        kws = list(domain.subcategory_keywords[subcat])
                    else:
                        subcat_words = [w.lower() for w in subcat.split() if len(w) > 3]
                        specific_kws = [k for k in domain.keywords if any(sw in k for sw in subcat_words)]
                        kws = specific_kws if len(specific_kws) >= 2 else domain.keywords

                    default_type = "Scientific Article" if domain.category == "Research" else (
                        "Technical Specification" if "Sécurité" in domain.category else "Report"
                    )
                    evaluation_rules.append({
                        "category": domain.category,
                        "subcategory": subcat,
                        "default_type": default_type,
                        "keywords": kws,
                        "strong_markers": domain.strong_markers,
                        "multiplier": domain.weight_multiplier,
                        "is_profile": True,
                    })

        for r in _DOMAIN_TAXONOMY:
            item = dict(r)
            item["multiplier"] = 1.0
            item["is_profile"] = False
            evaluation_rules.append(item)

        # 3. Evaluate Domain Categories with Weighted Zone Scoring
        best_category = "Unknown"
        best_subcategory = "Unknown"
        best_doc_type = "Unknown"
        best_score = 0.0
        best_matched_terms: list[str] = []

        for rule in evaluation_rules:
            category = rule["category"]
            subcategory = rule["subcategory"]
            keywords = rule["keywords"]
            strong_markers = rule.get("strong_markers", [])
            multiplier = rule.get("multiplier", 1.0)

            rule_score = 0.0
            hits: list[str] = []

            for kw in keywords:
                kw_lower = kw.lower()
                hit_in_rule = False

                # Zone 1: Filename (weight 3.0)
                if kw_lower in filename_zone:
                    rule_score += 3.0
                    hit_in_rule = True

                # Zone 2: Title / Header (weight 2.5)
                if title_zone and kw_lower in title_zone:
                    rule_score += 2.5
                    hit_in_rule = True

                # Zone 3: Lead text / Executive summary (weight 1.8)
                if lead_zone and kw_lower in lead_zone:
                    rule_score += 1.8
                    hit_in_rule = True

                # Zone 4: Body text (weight 1.0)
                if body_zone and kw_lower in body_zone:
                    rule_score += 1.0
                    hit_in_rule = True

                if hit_in_rule:
                    hits.append(kw)

            # Bonus for strong canonical markers
            for marker in strong_markers:
                m_lower = marker.lower()
                if (
                    m_lower in filename_zone
                    or (title_zone and m_lower in title_zone)
                    or (lead_zone and m_lower in lead_zone)
                ):
                    rule_score += 3.5
                    if marker not in hits:
                        hits.append(marker)

            # Apply domain priority multiplier
            rule_score *= multiplier

            if rule_score > best_score:
                best_score = rule_score
                best_category = category
                best_subcategory = subcategory
                best_doc_type = rule["default_type"]
                best_matched_terms = hits

        # 3. Detect Precise Document Type (Orthogonal analysis)
        detected_doc_type = self._detect_document_type(
            filename_zone, title_zone, lead_zone, body_zone, best_doc_type
        )

        # 4. Detect Organization
        combined_text = f"{filename_zone} {title_zone} {lead_zone} {body_zone}"
        organization = self._detect_organization(combined_text)

        # 5. Detect Year
        raw_full = f"{file_info.filename} {metadata.title if metadata else ''} {content.extracted_text if content else ''}"
        year = self._detect_year(raw_full)

        # 6. Detect Topic / Subject
        topic = self._detect_topic(metadata, lead_zone)

        # 7. Formulate Confidence Score
        confidence, reason = self._compute_confidence(
            best_score,
            best_category,
            best_matched_terms,
            metadata,
            content,
            detected_doc_type,
            organization,
        )

        # 8. Section 21: Context (Scope) & Relationship (Activity, Role, Project)
        work_context = ""
        role = ""
        project = ""
        signals_dict: dict = {
            "matched_keywords": best_matched_terms,
            "rule_score": round(best_score, 2),
        }

        matched_activity = None
        if self.user_profile:
            match_res = self.user_profile.match_activity(full_extracted, file_info.filename, year)
            if match_res:
                matched_activity, act_score, act_signals = match_res
                signals_dict.update(act_signals)
                if not organization:
                    organization = matched_activity.organization
                work_context = matched_activity.work_context
                role = matched_activity.role
                for p in matched_activity.projects:
                    if p.lower() in full_extracted or p.lower() in filename_zone:
                        project = p
                        break
                if not project and matched_activity.projects:
                    project = matched_activity.projects[0]

            scope, scope_conf, scope_reason = self.user_profile.detect_scope(
                full_extracted, file_info.filename, detected_doc_type, matched_activity
            )
        else:
            scope = "Work"
            scope_reason = "Default scope"

        signals_dict["scope"] = scope
        if work_context:
            signals_dict["work_context"] = work_context
        if role:
            signals_dict["role"] = role
        if project:
            signals_dict["project"] = project

        return ClassificationResult(
            document_type=detected_doc_type,
            category=best_category,
            subcategory=best_subcategory,
            topic=topic,
            organization=organization,
            year=year,
            confidence=round(confidence, 2),
            reason=reason,
            classifier_used="rules (bilingual)",
            scope=scope,
            work_context=work_context,
            role=role,
            project=project,
            extracted_signals=signals_dict,
        )

    # ------------------------------------------------------------------
    # Document Type Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_document_type(
        filename_zone: str,
        title_zone: str,
        lead_zone: str,
        body_zone: str,
        fallback_type: str,
    ) -> str:
        """Identify the document type using specific structural indicators."""
        best_type = fallback_type
        highest_weight = 0.0

        for doc_type, markers in _DOCUMENT_TYPES:
            type_score = 0.0
            for m in markers:
                m_lower = m.lower()
                if m_lower in filename_zone:
                    type_score += 3.0
                if title_zone and m_lower in title_zone:
                    type_score += 2.5
                if lead_zone and m_lower in lead_zone:
                    type_score += 1.5
                if body_zone and m_lower in body_zone:
                    type_score += 0.8

            if type_score > highest_weight and type_score >= 2.0:
                highest_weight = type_score
                best_type = doc_type

        return best_type

    # ------------------------------------------------------------------
    # Organization, Year & Topic
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_organization(text_lower: str) -> str:
        """Match and normalize organization names and acronyms."""
        sorted_aliases = sorted(_ORG_ALIASES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, text_lower):
                return _ORG_ALIASES[alias]
        return ""

    @staticmethod
    def _detect_year(text: str) -> str:
        """Extract a valid 4-digit calendar year (1990–2039)."""
        matches = re.findall(r"\b(199\d|20[0-3]\d)\b", text)
        if matches:
            return str(max(int(y) for y in matches))
        return ""

    @staticmethod
    def _detect_topic(metadata: Optional[PDFMetadata], lead_zone: str) -> str:
        """Extract a descriptive document topic."""
        if metadata and metadata.subject:
            return metadata.subject.strip()
        if metadata and metadata.title:
            return metadata.title.strip()

        if lead_zone:
            lines = [l.strip() for l in lead_zone.split("\n") if len(l.strip()) > 5]
            if lines:
                return lines[0][:100]
        return ""

    # ------------------------------------------------------------------
    # Confidence Formulation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence(
        score: float,
        category: str,
        matched_terms: list[str],
        metadata: Optional[PDFMetadata],
        content: Optional[PDFContent],
        doc_type: str,
        organization: str,
    ) -> tuple[float, str]:
        """Compute final confidence and a clear human explanation."""
        if category == "Unknown" or score < 1.5:
            return 0.20, "No definitive domain keywords found."

        base_conf = 0.50 + min(score * 0.05, 0.40)

        if organization and category in ("Public Health", "Legal", "Research"):
            base_conf = min(base_conf + 0.06, 0.95)

        if doc_type not in ("Unknown", "Other", "Report"):
            base_conf = min(base_conf + 0.04, 0.96)

        if content and content.is_scanned:
            return 0.35, "Limited text detected — Scanned / OCR required"

        terms_summary = ", ".join(list(dict.fromkeys(matched_terms))[:4])
        reason = f"Identified {doc_type} in {category} based on: {terms_summary}"
        if organization:
            reason += f" ({organization})"

        return min(base_conf, 0.96), reason
