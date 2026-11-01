"""Profile Discovery Engine (Section 21.10).

Discovers candidate organizations, employers, clients, and domains from scanned
documents and proposes progressive additions to the user's professional profile.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from app.classification.user_profile import UserProfile
from app.database.models import PDFDocument
from app.utils.app_logging import get_logger

logger = get_logger("classification.discovery")


@dataclass
class DiscoveredEntity:
    """An organization or domain discovered from documents that is not yet in the profile."""
    name: str
    entity_type: str  # "organization" or "domain"
    occurrence_count: int
    sample_files: list[str] = field(default_factory=list)
    proposed_role_or_context: str = "Previous Employment"

    @property
    def summary_message(self) -> str:
        if self.entity_type == "organization":
            return f"Organization '{self.name}' appears in {self.occurrence_count} document(s)."
        return f"Domain '{self.name}' appears frequently ({self.occurrence_count} docs) in your files."


class ProfileDiscoveryEngine:
    """Discovers recurring entities and domains from scanned documents."""

    ORG_SUFFIX_REGEX = re.compile(
        r'\b([A-Z][A-Za-z0-9_\-\s]{2,30}?\s+(?:Consulting|Technologies|Solutions|Assurance|Insurance|Laboratoire|Institute|University|Hôpital|Hospital|Ministère|Agency|Inc|SA|SAS|SARL|LLC|GmbH|Foundation|Fondation))\b',
        re.MULTILINE,
    )

    KNOWN_DISCOVERY_DOMAINS = [
        "Cybersecurity", "Bioinformatics", "Fintech", "Robotics", "Telemedicine",
        "Genomics", "Pharmacology", "Computer Vision", "Blockchain", "Quantum Computing",
        "Aerospace", "Renewable Energy", "Supply Chain", "Embedded Systems",
    ]

    def discover_from_documents(
        self,
        documents: list[PDFDocument],
        profile: UserProfile,
        min_occurrences: int = 2,
    ) -> list[DiscoveredEntity]:
        """Analyze analyzed documents to discover candidate organizations and domains."""
        if not documents:
            return []

        # 1. Existing names in profile to exclude
        existing_orgs = set()
        existing_domains = set()

        for act in profile.activities:
            if act.organization:
                existing_orgs.add(act.organization.lower().strip())
            for d in act.domains:
                existing_domains.add(d.lower().strip())

        for d in profile.domains:
            existing_domains.add(d.category.lower().strip())
            for s in d.subcategories:
                existing_domains.add(s.lower().strip())

        org_counts: Counter[str] = Counter()
        org_files: dict[str, list[str]] = {}

        domain_counts: Counter[str] = Counter()
        domain_files: dict[str, list[str]] = {}

        # 2. Scan documents
        for doc in documents:
            filename = doc.file_info.filename
            text = ""
            if doc.content and doc.content.extracted_text:
                text = doc.content.extracted_text[:4000]

            combined = filename + "\n" + text

            # Match organizations
            matches = self.ORG_SUFFIX_REGEX.findall(combined)
            found_doc_orgs = set()
            for m in matches:
                clean_org = m.strip()
                # Exclude common false positives
                if len(clean_org) > 4 and clean_org.lower() not in existing_orgs:
                    if not any(f in clean_org.lower() for f in ("adobe", "microsoft", "google", "apple", "system")):
                        found_doc_orgs.add(clean_org)

            for org in found_doc_orgs:
                org_counts[org] += 1
                if org not in org_files:
                    org_files[org] = []
                if len(org_files[org]) < 3:
                    org_files[org].append(filename)

            # Match domains
            for dom in self.KNOWN_DISCOVERY_DOMAINS:
                if dom.lower() not in existing_domains:
                    if re.search(r'\b' + re.escape(dom.lower()) + r'\b', combined.lower()):
                        domain_counts[dom] += 1
                        if dom not in domain_files:
                            domain_files[dom] = []
                        if len(domain_files[dom]) < 3:
                            domain_files[dom].append(filename)

        # 3. Build discovered list
        discovered: list[DiscoveredEntity] = []

        for org, count in org_counts.most_common(10):
            if count >= min_occurrences:
                discovered.append(DiscoveredEntity(
                    name=org,
                    entity_type="organization",
                    occurrence_count=count,
                    sample_files=org_files.get(org, []),
                    proposed_role_or_context="Previous Employment" if "University" not in org else "Academic Work",
                ))

        for dom, count in domain_counts.most_common(5):
            if count >= min_occurrences:
                discovered.append(DiscoveredEntity(
                    name=dom,
                    entity_type="domain",
                    occurrence_count=count,
                    sample_files=domain_files.get(dom, []),
                ))

        return discovered
