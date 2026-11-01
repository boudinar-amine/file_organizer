"""Tests for the PDF Scanner, Extractor, and Classifier.

These tests create temporary PDF files to verify the analysis pipeline
without touching any real documents.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


class TestPDFScanner(unittest.TestCase):
    """Tests for app.scanner.pdf_scanner.PDFScanner."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        # Create some fake PDF files (just empty files with .pdf extension)
        self.pdf_files: list[Path] = []
        for name in ["report.pdf", "invoice.pdf", "readme.txt", "notes.pdf"]:
            p = Path(self.temp_dir) / name
            p.write_bytes(b"%PDF-1.4 fake" if name.endswith(".pdf") else b"text")
            if name.endswith(".pdf"):
                self.pdf_files.append(p)

        # Subdirectory with one PDF
        sub = Path(self.temp_dir) / "subdir"
        sub.mkdir()
        sub_pdf = sub / "sub_report.pdf"
        sub_pdf.write_bytes(b"%PDF-1.4 fake sub")
        self.pdf_files.append(sub_pdf)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_finds_pdfs(self) -> None:
        from app.scanner.pdf_scanner import PDFScanner

        scanner = PDFScanner(Path(self.temp_dir), include_subfolders=True)
        results = scanner.scan()

        filenames = {r.filename for r in results}
        self.assertIn("report.pdf", filenames)
        self.assertIn("invoice.pdf", filenames)
        self.assertIn("notes.pdf", filenames)
        self.assertIn("sub_report.pdf", filenames)
        # .txt file should NOT be found
        self.assertNotIn("readme.txt", filenames)

    def test_scan_no_subfolders(self) -> None:
        from app.scanner.pdf_scanner import PDFScanner

        scanner = PDFScanner(Path(self.temp_dir), include_subfolders=False)
        results = scanner.scan()

        filenames = {r.filename for r in results}
        # Root PDFs should be found
        self.assertIn("report.pdf", filenames)
        # Subdirectory PDF should NOT be found
        self.assertNotIn("sub_report.pdf", filenames)

    def test_scan_empty_directory(self) -> None:
        from app.scanner.pdf_scanner import PDFScanner

        empty_dir = tempfile.mkdtemp()
        try:
            scanner = PDFScanner(Path(empty_dir))
            results = scanner.scan()
            self.assertEqual(len(results), 0)
        finally:
            os.rmdir(empty_dir)

    def test_scan_nonexistent_directory(self) -> None:
        from app.scanner.pdf_scanner import PDFScanner

        with self.assertRaises(FileNotFoundError):
            PDFScanner(Path("/nonexistent/path/12345"))

    def test_file_info_fields(self) -> None:
        from app.scanner.pdf_scanner import PDFScanner

        scanner = PDFScanner(Path(self.temp_dir))
        results = scanner.scan()

        for info in results:
            self.assertTrue(info.path.exists())
            self.assertEqual(info.extension, ".pdf")
            self.assertGreater(info.size_bytes, 0)
            self.assertTrue(info.filename.endswith(".pdf"))

    def test_count_pdfs(self) -> None:
        from app.scanner.pdf_scanner import PDFScanner

        scanner = PDFScanner(Path(self.temp_dir), include_subfolders=True)
        count = scanner.count_pdfs()
        self.assertEqual(count, 4)  # 3 root + 1 subdirectory


class TestPDFExtractor(unittest.TestCase):
    """Tests for app.extraction.pdf_extractor.PDFExtractor."""

    @classmethod
    def setUpClass(cls) -> None:
        """Check if PyMuPDF is available."""
        try:
            import pymupdf as fitz
            cls.has_fitz = True
            cls.fitz = fitz
        except ImportError:
            try:
                import fitz
                cls.has_fitz = True
                cls.fitz = fitz
            except ImportError:
                cls.has_fitz = False
                cls.fitz = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_pdf(self, filename: str, text: str = "Hello World") -> Path:
        """Create a simple PDF with text content using PyMuPDF."""
        fitz = self.fitz
        path = Path(self.temp_dir) / filename
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
        doc.set_metadata({
            "title": "Test Document",
            "author": "Test Author",
            "subject": "Testing",
        })
        doc.save(str(path))
        doc.close()
        return path

    def _create_empty_pdf(self, filename: str) -> Path:
        """Create a PDF with zero text (simulates a scanned PDF)."""
        fitz = self.fitz
        path = Path(self.temp_dir) / filename
        doc = fitz.open()
        doc.new_page()
        doc.save(str(path))
        doc.close()
        return path

    @unittest.skipUnless(
        lambda: __import__("fitz"),
        "PyMuPDF not installed",
    )
    def test_extract_metadata(self) -> None:
        if not self.has_fitz:
            self.skipTest("PyMuPDF not installed")

        from app.extraction.pdf_extractor import PDFExtractor

        path = self._create_test_pdf("test_meta.pdf")
        extractor = PDFExtractor(max_pages=2)
        metadata = extractor.extract_metadata(path)

        self.assertEqual(metadata.title, "Test Document")
        self.assertEqual(metadata.author, "Test Author")
        self.assertEqual(metadata.subject, "Testing")
        self.assertEqual(metadata.page_count, 1)

    @unittest.skipUnless(
        lambda: __import__("fitz"),
        "PyMuPDF not installed",
    )
    def test_extract_text(self) -> None:
        if not self.has_fitz:
            self.skipTest("PyMuPDF not installed")

        from app.extraction.pdf_extractor import PDFExtractor

        path = self._create_test_pdf("test_text.pdf", "World Health Organization Report 2025")
        extractor = PDFExtractor(max_pages=2)
        content = extractor.extract_text(path)

        self.assertIn("World Health Organization", content.extracted_text)
        self.assertFalse(content.is_scanned)
        self.assertEqual(content.pages_analyzed, 1)

    @unittest.skipUnless(
        lambda: __import__("fitz"),
        "PyMuPDF not installed",
    )
    def test_detect_scanned_pdf(self) -> None:
        if not self.has_fitz:
            self.skipTest("PyMuPDF not installed")

        from app.extraction.pdf_extractor import PDFExtractor

        path = self._create_empty_pdf("scanned.pdf")
        extractor = PDFExtractor(max_pages=2)
        content = extractor.extract_text(path)

        self.assertTrue(content.is_scanned)

    @unittest.skipUnless(
        lambda: __import__("fitz"),
        "PyMuPDF not installed",
    )
    def test_extract_all(self) -> None:
        if not self.has_fitz:
            self.skipTest("PyMuPDF not installed")

        from app.extraction.pdf_extractor import PDFExtractor

        path = self._create_test_pdf("test_all.pdf", "Invoice for payment")
        extractor = PDFExtractor(max_pages=2)
        metadata, content = extractor.extract_all(path)

        self.assertIsNotNone(metadata)
        self.assertIsNotNone(content)
        self.assertEqual(metadata.title, "Test Document")
        self.assertIn("Invoice", content.extracted_text)

    def test_corrupted_pdf(self) -> None:
        from app.extraction.pdf_extractor import PDFExtractor

        path = Path(self.temp_dir) / "corrupted.pdf"
        path.write_bytes(b"This is not a PDF file at all")

        extractor = PDFExtractor(max_pages=2)
        metadata = extractor.extract_metadata(path)
        content = extractor.extract_text(path)

        # Should not crash — should return defaults
        self.assertEqual(metadata.page_count, 0)
        self.assertIsNotNone(content.extraction_error)


class TestRuleClassifier(unittest.TestCase):
    """Tests for app.classification.rule_classifier.RuleClassifier."""

    def _make_file_info(self, filename: str) -> "PDFFileInfo":
        from app.database.models import PDFFileInfo
        return PDFFileInfo(
            path=Path(f"C:/test/{filename}"),
            filename=filename,
            extension=".pdf",
            size_bytes=1024,
        )

    def _make_content(self, text: str) -> "PDFContent":
        from app.database.models import PDFContent
        return PDFContent(
            extracted_text=text,
            pages_analyzed=1,
            total_pages=1,
            is_scanned=False,
        )

    def test_who_document(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("A78_13_final.pdf")
        content = self._make_content(
            "World Health Organization Seventy-eighth World Health Assembly "
            "Health emergency preparedness 2025"
        )
        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Public Health")
        self.assertEqual(result.subcategory, "WHO")
        self.assertGreater(result.confidence, 0.5)
        self.assertEqual(result.organization, "World Health Organization")

    def test_invoice(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("invoice_2024.pdf")
        content = self._make_content("Invoice Total amount due Payment billing")

        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Administration")
        self.assertEqual(result.subcategory, "Invoices")
        self.assertGreater(result.confidence, 0.5)

    def test_scientific_article(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("research_paper.pdf")
        content = self._make_content(
            "Abstract Introduction Methodology Results Conclusion References "
            "doi:10.1234/journal.2024.001"
        )

        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Research")
        self.assertGreater(result.confidence, 0.5)

    def test_unknown_document(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("xyz123.pdf")
        content = self._make_content("random gibberish no keywords match")

        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Unknown")
        self.assertLess(result.confidence, 0.65)

    def test_scanned_pdf_caps_confidence(self) -> None:
        from app.classification.rule_classifier import RuleClassifier
        from app.database.models import PDFContent

        classifier = RuleClassifier()
        file_info = self._make_file_info("scan001.pdf")
        content = PDFContent(
            extracted_text="",
            pages_analyzed=1,
            total_pages=1,
            is_scanned=True,
        )

        result = classifier.classify(file_info, None, content)
        self.assertLessEqual(result.confidence, 0.40)

    def test_year_detection(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("report_2025.pdf")
        content = self._make_content("Report published in 2025 about something")

        result = classifier.classify(file_info, None, content)
        self.assertEqual(result.year, "2025")

    def test_french_who_document(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("A78_Rapport_OMS.pdf")
        content = self._make_content(
            "Organisation mondiale de la santé\nSoixante-dix-huitième Assemblée mondiale de la santé\n"
            "Préparation et riposte aux urgences sanitaires 2024"
        )
        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Public Health")
        self.assertEqual(result.subcategory, "WHO")
        self.assertEqual(result.organization, "World Health Organization")
        self.assertEqual(result.year, "2024")
        self.assertGreater(result.confidence, 0.70)

    def test_french_invoice(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("Facture_F2024_089.pdf")
        content = self._make_content("Facture n° 2024-089 Montant Total TTC 1500 EUR TVA 20% Règlement par virement IBAN")

        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Administration")
        self.assertEqual(result.subcategory, "Invoices")
        self.assertEqual(result.document_type, "Invoice")
        self.assertGreater(result.confidence, 0.70)

    def test_french_decree_regulation(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("Decret_2024_104.pdf")
        content = self._make_content(
            "Décret n° 2024-104 du 15 mars 2024 relatif à la conformité sanitaire.\n"
            "Le Premier ministre, sur le rapport du ministre de la santé, Vu le code de la santé publique, Article 1er"
        )

        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Legal")
        self.assertEqual(result.subcategory, "Regulations")
        self.assertEqual(result.document_type, "Regulation")
        self.assertGreater(result.confidence, 0.70)

    def test_french_strategy_plan(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("Plan_Strategique_Sante_2030.pdf")
        content = self._make_content("Plan stratégique national et feuille de route 2030. Orientations stratégiques et axes prioritaires.")

        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Strategy")
        self.assertEqual(result.subcategory, "Strategic Plans")
        self.assertEqual(result.document_type, "Strategy")
        self.assertGreater(result.confidence, 0.70)

    def test_french_meeting_minutes(self) -> None:
        from app.classification.rule_classifier import RuleClassifier

        classifier = RuleClassifier()
        file_info = self._make_file_info("PV_Conseil_Administration_2024.pdf")
        content = self._make_content(
            "Procès-verbal de la réunion du Conseil d'Administration. Date: 12 janvier 2024.\n"
            "Ordre du jour: 1. Approbation du compte-rendu précédent. Participants et relevé de décisions."
        )

        result = classifier.classify(file_info, None, content)

        self.assertEqual(result.category, "Meetings")
        self.assertEqual(result.subcategory, "Meeting Documents")
        self.assertEqual(result.document_type, "Meeting Document")
        self.assertGreater(result.confidence, 0.70)


class TestValidators(unittest.TestCase):
    """Tests for app.utils.validators."""

    def test_validate_folder_path_valid(self) -> None:
        from app.utils.validators import validate_folder_path
        ok, msg = validate_folder_path(tempfile.gettempdir())
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_validate_folder_path_empty(self) -> None:
        from app.utils.validators import validate_folder_path
        ok, msg = validate_folder_path("")
        self.assertFalse(ok)
        self.assertIn("empty", msg.lower())

    def test_validate_folder_path_nonexistent(self) -> None:
        from app.utils.validators import validate_folder_path
        ok, msg = validate_folder_path("/nonexistent/directory/12345")
        self.assertFalse(ok)

    def test_sanitize_folder_name(self) -> None:
        from app.utils.validators import sanitize_folder_name
        self.assertEqual(sanitize_folder_name("Public Health"), "Public Health")
        self.assertEqual(sanitize_folder_name("Test<>Folder"), "Test_Folder")
        self.assertEqual(sanitize_folder_name(""), "Uncategorized")
        self.assertEqual(sanitize_folder_name("..."), "Uncategorized")

    def test_validate_json_classification(self) -> None:
        from app.utils.validators import validate_json_classification

        good = {
            "document_type": "Report",
            "category": "Public Health",
            "subcategory": "WHO",
            "confidence": 0.95,
        }
        ok, msg, data = validate_json_classification(good)
        self.assertTrue(ok)
        self.assertIsNotNone(data)

        bad = {"document_type": "Report"}  # missing fields
        ok, msg, data = validate_json_classification(bad)
        self.assertFalse(ok)


class TestOrganizationPlanner(unittest.TestCase):
    """Tests for app.organizer.planner.OrganizationPlanner."""

    def test_plan_creates_destinations(self) -> None:
        from app.database.models import (
            ClassificationResult,
            FileStatus,
            PDFDocument,
            PDFFileInfo,
        )
        from app.organizer.planner import OrganizationPlanner

        output_root = Path("C:/test_output/Organized")
        planner = OrganizationPlanner(output_root)

        doc = PDFDocument(
            file_info=PDFFileInfo(
                path=Path("C:/Downloads/report.pdf"),
                filename="report.pdf",
                extension=".pdf",
                size_bytes=1024,
            ),
            classification=ClassificationResult(
                category="Public Health",
                subcategory="WHO",
                confidence=0.9,
            ),
            status=FileStatus.ANALYZED,
        )

        result = planner.plan([doc])

        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].suggested_path)
        dest = result[0].suggested_path
        self.assertIn("Public Health", str(dest))
        self.assertIn("WHO", str(dest))
        self.assertTrue(str(dest).endswith("report.pdf"))

    def test_plan_unknown_goes_to_review(self) -> None:
        from app.database.models import (
            ClassificationResult,
            FileStatus,
            PDFDocument,
            PDFFileInfo,
        )
        from app.organizer.planner import OrganizationPlanner

        output_root = Path("C:/test_output/Organized")
        planner = OrganizationPlanner(output_root)

        doc = PDFDocument(
            file_info=PDFFileInfo(
                path=Path("C:/Downloads/unknown.pdf"),
                filename="unknown.pdf",
                extension=".pdf",
                size_bytes=512,
            ),
            classification=ClassificationResult(
                category="Unknown",
                subcategory="Unknown",
                confidence=0.2,
            ),
            status=FileStatus.PENDING,
        )

        result = planner.plan([doc])
        self.assertIn("Review", str(result[0].suggested_path))


class TestDataModels(unittest.TestCase):
    """Tests for app.database.models data classes."""

    def test_confidence_levels(self) -> None:
        from app.database.models import ConfidenceLevel

        self.assertEqual(ConfidenceLevel.from_score(0.90), ConfidenceLevel.HIGH)
        self.assertEqual(ConfidenceLevel.from_score(0.75), ConfidenceLevel.MEDIUM)
        self.assertEqual(ConfidenceLevel.from_score(0.40), ConfidenceLevel.LOW)

    def test_pdf_file_info_size_human(self) -> None:
        from app.database.models import PDFFileInfo

        info = PDFFileInfo(
            path=Path("test.pdf"),
            filename="test.pdf",
            extension=".pdf",
            size_bytes=1536,
        )
        self.assertIn("KB", info.size_human)

    def test_pdf_content_has_usable_text(self) -> None:
        from app.database.models import PDFContent

        empty = PDFContent(extracted_text="   ")
        self.assertFalse(empty.has_usable_text)

        useful = PDFContent(extracted_text="A" * 100)
        self.assertTrue(useful.has_usable_text)

    def test_classification_needs_review(self) -> None:
        from app.database.models import ClassificationResult

        high = ClassificationResult(confidence=0.90)
        self.assertFalse(high.needs_review)

        low = ClassificationResult(confidence=0.40)
        self.assertTrue(low.needs_review)


if __name__ == "__main__":
    unittest.main()
