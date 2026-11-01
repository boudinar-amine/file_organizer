"""Unit tests for Section 21: User Profile Knowledge Graph and Context Disambiguation.

Validates:
1. Multi-Activity Knowledge Graph representations.
2. Context (Scope) vs Relationship vs Content distinction.
3. Activity matching with organization, role, project alias, and temporal consistency.
4. Destination folder planning for Work, Personal, Learning, Training, and Reference.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.classification.classifier import Classifier
from app.classification.user_profile import (
    EducationEntry,
    ProfessionalActivity,
    ScopeType,
    UserProfile,
    WorkContextType,
    get_default_profile,
)
from app.database.models import (
    ClassificationResult,
    PDFContent,
    PDFDocument,
    PDFFileInfo,
    PDFMetadata,
)
from app.organizer.planner import OrganizationPlanner


class TestSection21KnowledgeGraph(unittest.TestCase):
    """Test User Profile Knowledge Graph structure and activity matching."""

    def setUp(self) -> None:
        self.profile = UserProfile(
            name="Multi-Activity Career Profile",
            mode="rich",
            activities=[
                ProfessionalActivity(
                    organization="Company A",
                    work_context=WorkContextType.PREVIOUS_EMPLOYMENT,
                    role="Data Scientist",
                    start_year=2018,
                    end_year=2021,
                    domains=["Insurtech", "Insurance"],
                    projects=["Claims Fraud Detection"],
                    skills=["python", "actuarial", "claims"],
                ),
                ProfessionalActivity(
                    organization="Company B",
                    work_context=WorkContextType.PREVIOUS_EMPLOYMENT,
                    role="Senior Data Scientist",
                    start_year=2021,
                    end_year=2024,
                    domains=["Insurtech", "Machine Learning"],
                    projects=["Risk Scoring Platform"],
                    skills=["risk modeling", "solvency ii", "machine learning"],
                ),
                ProfessionalActivity(
                    organization="Organization C",
                    work_context=WorkContextType.CURRENT_EMPLOYMENT,
                    role="Public Health Specialist",
                    start_year=2024,
                    is_current=True,
                    domains=["Public Health", "Epidemiology"],
                    projects=["National Surveillance System"],
                    skills=["epidemiology", "surveillance", "public health"],
                ),
            ],
            education=[
                EducationEntry(
                    institution="University Paris-Saclay",
                    degree="PhD",
                    field_of_study="Artificial Intelligence",
                    end_year=2018,
                )
            ],
        )

    def test_organization_and_project_matching(self) -> None:
        text = "This report details the Claims Fraud Detection model developed for Company A."
        res = self.profile.match_activity(text=text, filename="fraud_model.pdf", year="2020")
        self.assertIsNotNone(res)
        act, score, signals = res
        self.assertEqual(act.organization, "Company A")
        self.assertEqual(act.role, "Data Scientist")
        self.assertIn("organization_match", signals)
        self.assertIn("project_match", signals)
        self.assertIn("temporal_consistency", signals)

    def test_temporal_disambiguation(self) -> None:
        # Both Company A (2018-2021) and Company B (2021-2024) share Data Scientist role in Insurtech.
        # A 2019 document with role & domain should match Company A due to temporal consistency
        res_2019 = self.profile.match_activity(
            text="Work report by Data Scientist in Insurtech on claims modeling.",
            filename="report_2019.pdf",
            year="2019",
        )
        self.assertIsNotNone(res_2019)
        self.assertEqual(res_2019[0].organization, "Company A")

        # A 2023 document with role & domain should match Company B
        res_2023 = self.profile.match_activity(
            text="Work report by Senior Data Scientist in Insurtech on risk scoring.",
            filename="scoring_platform.pdf",
            year="2023",
        )
        self.assertIsNotNone(res_2023)
        self.assertEqual(res_2023[0].organization, "Company B")

    def test_scope_detection_learning_vs_training_vs_personal(self) -> None:
        # Learning
        scope, conf, _ = self.profile.detect_scope(
            text="University Course Syllabus - Introduction to Machine Learning. Homework assignment 1.",
            filename="CS101_Syllabus.pdf",
        )
        self.assertEqual(scope, ScopeType.LEARNING)

        # Training
        scope, conf, _ = self.profile.detect_scope(
            text="Certificate of Completion. Awarded for successful participation in Deep Learning Workshop.",
            filename="Workshop_Certificate.pdf",
        )
        self.assertEqual(scope, ScopeType.TRAINING)

        # Personal
        scope, conf, _ = self.profile.detect_scope(
            text="Direction Générale des Finances Publiques. Avis d'impôt 2024 sur les revenus de l'année 2023.",
            filename="Avis_Impot_2024.pdf",
        )
        self.assertEqual(scope, ScopeType.PERSONAL)


class TestSection21DestinationPlanning(unittest.TestCase):
    """Test folder destination planning reflecting Section 21.8 structure."""

    def setUp(self) -> None:
        self.output_root = Path("C:/Organized")
        self.planner = OrganizationPlanner(self.output_root)

    def test_work_with_organization_destination(self) -> None:
        doc = PDFDocument(
            file_info=PDFFileInfo(Path("C:/report.pdf"), "report.pdf", ".pdf", 1000),
            classification=ClassificationResult(
                document_type="Report",
                category="Public Health",
                subcategory="Epidemiology",
                organization="Organization A",
                scope="Work",
            ),
        )
        self.planner.plan([doc])
        self.assertIsNotNone(doc.suggested_path)
        expected = self.output_root / "Work" / "Organization A" / "Public Health" / "Epidemiology" / "report.pdf"
        self.assertEqual(doc.suggested_path, expected)

    def test_learning_destination(self) -> None:
        doc = PDFDocument(
            file_info=PDFFileInfo(Path("C:/syllabus.pdf"), "syllabus.pdf", ".pdf", 1000),
            classification=ClassificationResult(
                document_type="Course Material",
                category="Artificial Intelligence",
                subcategory="Deep Learning",
                scope="Learning",
            ),
        )
        self.planner.plan([doc])
        self.assertIsNotNone(doc.suggested_path)
        expected = self.output_root / "Learning" / "Artificial Intelligence" / "Deep Learning" / "syllabus.pdf"
        self.assertEqual(doc.suggested_path, expected)

    def test_personal_destination(self) -> None:
        doc = PDFDocument(
            file_info=PDFFileInfo(Path("C:/tax_return.pdf"), "tax_return.pdf", ".pdf", 1000),
            classification=ClassificationResult(
                document_type="Tax Notice",
                category="Taxes",
                subcategory="Income Tax",
                scope="Personal",
            ),
        )
        self.planner.plan([doc])
        self.assertIsNotNone(doc.suggested_path)
        expected = self.output_root / "Personal" / "Taxes" / "Income Tax" / "tax_return.pdf"
        self.assertEqual(doc.suggested_path, expected)


if __name__ == "__main__":
    unittest.main()
