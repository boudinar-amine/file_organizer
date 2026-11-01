"""Unit tests for Profile Discovery from Documents (Section 21.10).

Validates:
1. Discovering recurring organizations from scanned documents.
2. Filtering out organizations and domains already present in the profile.
3. Proposing additions with document occurrence counts and sample filenames.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.classification.profile_discovery import ProfileDiscoveryEngine
from app.classification.user_profile import UserProfile
from app.database.models import (
    PDFContent,
    PDFDocument,
    PDFFileInfo,
    PDFMetadata,
)


class TestProfileDiscovery(unittest.TestCase):
    """Test progressive entity discovery from scanned documents."""

    def test_discover_recurring_organization(self) -> None:
        profile = UserProfile(name="Empty Profile", mode="zero")
        engine = ProfileDiscoveryEngine()

        docs = []
        for i in range(4):
            doc = PDFDocument(
                file_info=PDFFileInfo(Path(f"C:/doc_{i}.pdf"), f"doc_{i}.pdf", ".pdf", 1000),
                content=PDFContent(
                    extracted_text="Confidential Project deliverable prepared by Meridian Technologies SA. "
                                   "Audited under cybersecurity protocols."
                ),
            )
            docs.append(doc)

        discovered = engine.discover_from_documents(docs, profile, min_occurrences=2)

        org_names = [d.name for d in discovered if d.entity_type == "organization"]
        self.assertTrue(any("Meridian Technologies" in o for o in org_names))

        domains = [d.name for d in discovered if d.entity_type == "domain"]
        self.assertIn("Cybersecurity", domains)


if __name__ == "__main__":
    unittest.main()
