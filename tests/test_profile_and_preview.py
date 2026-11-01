"""Tests for UserProfile domain personalization and PreviewOrganizationDialog.

Verifies:
1. User profile serialization, presets, and domain specifications.
2. RuleClassifier domain prioritization for PhD in XAI, Insurtech, and Sécurité Sanitaire.
3. PreviewOrganizationDialog tree grouping, search filtering, and inspector updates.
4. ProfileDialog preset switching and custom domain manipulation.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.classification.classifier import Classifier
from app.classification.rule_classifier import RuleClassifier
from app.classification.user_profile import (
    PRESET_PROFILES,
    PROFILE_GENERAL_ACADEMIC,
    PROFILE_PHD_AI_INSURTECH_HEALTH,
    DomainSpec,
    UserProfile,
    get_default_profile,
)
from app.database.models import (
    ClassificationResult,
    ConfidenceLevel,
    FileStatus,
    PDFContent,
    PDFDocument,
    PDFFileInfo,
    PDFMetadata,
)


class TestUserProfile(unittest.TestCase):
    """Test user profile data structures and serialization."""

    def test_default_profile_domains(self) -> None:
        profile = get_default_profile()
        self.assertIn("PhD", profile.name)
        categories = [d.category for d in profile.domains]
        self.assertIn("Research", categories)
        self.assertIn("Insurtech", categories)
        self.assertIn("Sécurité Sanitaire", categories)

    def test_profile_to_and_from_dict(self) -> None:
        profile = PROFILE_PHD_AI_INSURTECH_HEALTH
        data = profile.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["name"], profile.name)

        reloaded = UserProfile.from_dict(data)
        self.assertEqual(reloaded.name, profile.name)
        self.assertEqual(len(reloaded.domains), len(profile.domains))
        self.assertEqual(reloaded.domains[0].category, "Research")


class TestDomainClassification(unittest.TestCase):
    """Test classification guided by the user's domain profile."""

    def setUp(self) -> None:
        self.profile = get_default_profile()
        self.classifier = Classifier(use_ollama=False, user_profile=self.profile)

    def test_xai_research_paper_classified_correctly(self) -> None:
        file_info = PDFFileInfo(
            path=Path("neurips_shap_counterfactual.pdf"),
            filename="neurips_shap_counterfactual.pdf",
            extension=".pdf",
            size_bytes=100000,
        )
        metadata = PDFMetadata(
            title="Feature Attribution via Shapley Values and Counterfactual Explanations",
            author="PhD Researcher",
        )
        content = PDFContent(
            extracted_text="In this paper we present an Explainable AI framework for deep neural networks. "
                           "We evaluate SHAP, integrated gradients, and counterfactual explanations on NeurIPS benchmarks."
        )
        res = self.classifier.classify(file_info, metadata, content)
        self.assertEqual(res.category, "Research")
        self.assertEqual(res.subcategory, "Explainable AI (XAI)")
        self.assertGreaterEqual(res.confidence, 0.80)

    def test_insurtech_risk_modeling_classified_correctly(self) -> None:
        file_info = PDFFileInfo(
            path=Path("rapport_actuariat_fraude_sinistres.pdf"),
            filename="rapport_actuariat_fraude_sinistres.pdf",
            extension=".pdf",
            size_bytes=80000,
        )
        metadata = PDFMetadata(
            title="Modélisation des sinistres et détection de fraude en assurance",
            author="Data Scientist Insurtech",
        )
        content = PDFContent(
            extracted_text="Étude actuarielle sur la fréquence et la sévérité des sinistres. "
                           "Algorithmes de tarification et détection de la fraude à l'assurance sous Solvabilité II."
        )
        res = self.classifier.classify(file_info, metadata, content)
        self.assertEqual(res.category, "Insurtech")
        self.assertIn("Claims", res.subcategory)
        self.assertGreaterEqual(res.confidence, 0.80)

    def test_securite_sanitaire_medical_devices_classified_correctly(self) -> None:
        file_info = PDFFileInfo(
            path=Path("evaluation_clinique_dm_iso13485.pdf"),
            filename="evaluation_clinique_dm_iso13485.pdf",
            extension=".pdf",
            size_bytes=95000,
        )
        metadata = PDFMetadata(
            title="Évaluation Clinique et Analyse de Risques Dispositif Médical",
            author="Ingénieur Sécurité Sanitaire",
        )
        content = PDFContent(
            extracted_text="Dossier technique de sécurité sanitaire selon la norme ISO 13485 et ISO 14971. "
                           "Dispositifs médicaux avec marquage CE et conformité au règlement MDR."
        )
        res = self.classifier.classify(file_info, metadata, content)
        self.assertEqual(res.category, "Sécurité Sanitaire")
        self.assertEqual(res.subcategory, "Dispositifs Médicaux")
        self.assertGreaterEqual(res.confidence, 0.80)


class TestGUIComponentsHeadless(unittest.TestCase):
    """Test PreviewOrganizationDialog and ProfileDialog headless."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_preview_dialog_hierarchy_and_filtering(self) -> None:
        from app.gui.preview_dialog import PreviewOrganizationDialog

        dest_root = Path("C:/Organized")
        doc1 = PDFDocument(
            file_info=PDFFileInfo(Path("C:/xai_paper.pdf"), "xai_paper.pdf", ".pdf", 102400),
            classification=ClassificationResult("Conference Paper", "Research", "Explainable AI (XAI)", 0.95),
            suggested_path=dest_root / "Research" / "Explainable AI (XAI)" / "xai_paper.pdf",
            status=FileStatus.ANALYZED,
        )
        doc2 = PDFDocument(
            file_info=PDFFileInfo(Path("C:/dm_iso13485.pdf"), "dm_iso13485.pdf", ".pdf", 204800),
            classification=ClassificationResult("Clinical Evaluation", "Sécurité Sanitaire", "Dispositifs Médicaux", 0.90),
            suggested_path=dest_root / "Sécurité Sanitaire" / "Dispositifs Médicaux" / "dm_iso13485.pdf",
            status=FileStatus.ANALYZED,
        )

        dialog = PreviewOrganizationDialog(
            documents=[doc1, doc2],
            destination_root=dest_root,
            is_copy_mode=True,
            auto_rename_conflicts=False,
        )

        # Verify tree hierarchy: 2 categories at top level
        self.assertEqual(dialog._tree.topLevelItemCount(), 2)

        # Test search filter
        dialog._on_search_changed("Explainable")
        # Should keep Research visible and hide Sécurité Sanitaire
        cat0 = dialog._tree.topLevelItem(0)
        cat1 = dialog._tree.topLevelItem(1)
        hidden_states = [cat0.isHidden(), cat1.isHidden()]
        self.assertIn(False, hidden_states)  # at least one category visible
        self.assertIn(True, hidden_states)   # at least one category hidden

        # Test clear search
        dialog._on_search_changed("")
        self.assertFalse(cat0.isHidden())
        self.assertFalse(cat1.isHidden())

        dialog.close()

    def test_profile_dialog_presets(self) -> None:
        from app.gui.profile_dialog import ProfileDialog

        dialog = ProfileDialog()
        self.assertGreaterEqual(dialog._activities_table.rowCount(), 1)

        # Switch to academic
        dialog._preset_combo.setCurrentIndex(1)
        dialog._on_preset_dropdown_changed(1)
        self.assertEqual(dialog._activities_table.rowCount(), 1)

        # Switch to zero profile
        dialog._preset_combo.setCurrentIndex(2)
        dialog._on_preset_dropdown_changed(2)
        self.assertEqual(dialog._activities_table.rowCount(), 0)

        dialog.close()


class TestBM25EmbeddingProvider(unittest.TestCase):
    """Test Okapi BM25 probabilistic relevance embedding provider."""

    def test_bm25_encoding_and_normalization(self) -> None:
        import numpy as np
        from app.classification.models.embeddings import (
            BM25EmbeddingProvider,
            ModelProfile,
            get_embedding_provider,
        )

        bm25 = BM25EmbeddingProvider(k1=1.5, b=0.75, max_features=512)
        self.assertEqual(bm25.dimension, 512)
        self.assertIn("bm25", bm25.name.lower())

        texts = [
            "Explainable AI research with SHAP and counterfactual deep neural networks.",
            "Étude actuarielle sur la tarification et détection de fraude sinistre en assurance.",
            "Dossier technique de sécurité sanitaire des dispositifs médicaux marquage CE ISO 13485.",
        ]

        vecs = bm25.encode(texts)
        self.assertEqual(vecs.shape, (3, 512))
        self.assertEqual(vecs.dtype, np.float32)

        # Check unit L2-normalization
        norms = np.linalg.norm(vecs, axis=1)
        for n in norms:
            self.assertAlmostEqual(float(n), 1.0, places=4)

        # Domain discriminability: XAI text must have highest similarity with itself/related text
        xai_query = bm25.encode(["Explainable AI and neural networks"])
        sim_xai = float(np.dot(vecs[0], xai_query[0]))
        sim_insurtech = float(np.dot(vecs[1], xai_query[0]))
        self.assertGreater(sim_xai, sim_insurtech)

        # Factory provider check
        prov = get_embedding_provider(ModelProfile.BM25)
        self.assertIsInstance(prov, BM25EmbeddingProvider)


if __name__ == "__main__":
    unittest.main()
