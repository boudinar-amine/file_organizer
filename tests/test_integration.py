"""Integration test for the full analysis pipeline on test_documents/.

Verifies:
1. Scanner discovers all test PDFs (including subfolders).
2. Extractor reads text and metadata properly.
3. Classifier detects document types, categories, organizations, and years.
4. Scanned PDF without text is flagged as 'ocr_required'.
5. Corrupted PDF is caught gracefully as 'error' without crashing.
6. Planner produces correct hierarchical destinations.
7. CRITICAL: No original files are moved, renamed, or modified.
8. Database stores file records, classifications, and operations.
"""

from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.classification.classifier import Classifier
from app.database.database import DatabaseManager
from app.database.models import FileStatus, PDFDocument
from app.extraction.pdf_extractor import PDFExtractor
from app.organizer.planner import OrganizationPlanner
from app.scanner.pdf_scanner import PDFScanner


class TestFullPipelineIntegration(unittest.TestCase):
    """End-to-end pipeline integration test."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_docs_dir = _project_root / "test_documents"
        cls.test_output_dir = _project_root / "test_output" / "Organized"
        cls.test_db_path = _project_root / "test_output" / "test_organizer.db"

        # Record original modification times and file sizes for safety verification
        cls.original_file_stats = {}
        for p in cls.test_docs_dir.rglob("*.pdf"):
            cls.original_file_stats[str(p)] = (p.stat().st_size, p.stat().st_mtime)

    def test_end_to_end_analysis(self) -> None:
        """Run the complete pipeline without moving any files."""
        # Step 1: Scan
        scanner = PDFScanner(self.test_docs_dir, include_subfolders=True)
        file_infos = scanner.scan()
        self.assertGreaterEqual(len(file_infos), 15, "Should discover at least 15 test PDFs (including French & bilingual docs)")

        extractor = PDFExtractor(max_pages=2)
        classifier = Classifier(use_ollama=False)
        planner = OrganizationPlanner(self.test_output_dir)

        documents: list[PDFDocument] = []
        for file_info in file_infos:
            doc = PDFDocument(file_info=file_info)
            try:
                metadata, content = extractor.extract_all(file_info.path)
                doc.metadata = metadata
                doc.content = content

                classification = classifier.classify(file_info, metadata, content)
                doc.classification = classification

                if content.extraction_error:
                    doc.status = FileStatus.ERROR
                    doc.error_message = content.extraction_error
                elif content.is_scanned:
                    doc.status = FileStatus.OCR_REQUIRED
                elif classification.needs_review:
                    doc.status = FileStatus.PENDING
                else:
                    doc.status = FileStatus.ANALYZED
            except Exception as e:
                doc.status = FileStatus.ERROR
                doc.error_message = str(e)

            documents.append(doc)

        # Step 2: Plan
        planner.plan(documents)

        # Step 3: Verify individual document classifications
        by_name = {d.file_info.filename: d for d in documents}

        # WHO document
        who_doc = by_name["A78_13_Health_Emergency_Preparedness.pdf"]
        self.assertEqual(who_doc.classification.category, "Public Health")
        self.assertEqual(who_doc.classification.subcategory, "WHO")
        self.assertEqual(who_doc.classification.organization, "World Health Organization")
        self.assertIn("Public Health", str(who_doc.suggested_path))
        self.assertIn("WHO", str(who_doc.suggested_path))

        # Epidemiology
        epi_doc = by_name["Weekly_Epidemiological_Record_2025.pdf"]
        self.assertEqual(epi_doc.classification.category, "Public Health")
        self.assertEqual(epi_doc.classification.subcategory, "Epidemiology")
        self.assertEqual(epi_doc.classification.year, "2025")

        # Pharmacovigilance (nested in subfolder)
        pv_doc = by_name["Drug_Safety_Pharmacovigilance_Review.pdf"]
        self.assertEqual(pv_doc.classification.category, "Public Health")
        self.assertEqual(pv_doc.classification.subcategory, "Pharmacovigilance")

        # Scientific article
        sci_doc = by_name["Nature_Article_Genomic_Sequencing.pdf"]
        self.assertEqual(sci_doc.classification.category, "Research")

        # Invoice
        inv_doc = by_name["Invoice_INV-2024-9041.pdf"]
        self.assertEqual(inv_doc.classification.category, "Administration")
        self.assertEqual(inv_doc.classification.subcategory, "Invoices")

        # User Guide
        guide_doc = by_name["QuickStart_User_Manual_v3.pdf"]
        self.assertEqual(guide_doc.classification.category, "Guides")
        self.assertEqual(guide_doc.classification.subcategory, "Manuals")

        # French Invoice
        fr_inv = by_name["Facture_Prestation_Conseil_2024.pdf"]
        self.assertEqual(fr_inv.classification.category, "Administration")
        self.assertEqual(fr_inv.classification.subcategory, "Invoices")
        self.assertEqual(fr_inv.classification.document_type, "Invoice")

        # French Epidemiology
        fr_epi = by_name["Bulletin_Surveillance_Epidemiologique_2024.pdf"]
        self.assertEqual(fr_epi.classification.category, "Public Health")
        self.assertEqual(fr_epi.classification.subcategory, "Epidemiology")
        self.assertEqual(fr_epi.classification.organization, "Santé Publique France")

        # French Sanitary Decree
        fr_dec = by_name["Decret_2024_Dispositions_Sanitaires.pdf"]
        self.assertEqual(fr_dec.classification.category, "Legal")
        self.assertEqual(fr_dec.classification.subcategory, "Regulations")
        self.assertEqual(fr_dec.classification.document_type, "Regulation")

        # French Strategic Plan
        fr_strat = by_name["Plan_Strategique_National_Sante_2030.pdf"]
        self.assertEqual(fr_strat.classification.category, "Strategy")
        self.assertEqual(fr_strat.classification.subcategory, "Strategic Plans")
        self.assertEqual(fr_strat.classification.document_type, "Strategy")

        # French Meeting Minutes
        fr_pv = by_name["PV_Reunion_Comite_Pilotage_2024.pdf"]
        self.assertEqual(fr_pv.classification.category, "Meetings")
        self.assertEqual(fr_pv.classification.subcategory, "Meeting Documents")
        self.assertEqual(fr_pv.classification.document_type, "Meeting Document")

        # Specialized PhD in XAI document
        if "NeurIPS_2024_Explainable_AI_SHAP_Counterfactuals.pdf" in by_name:
            xai_doc = by_name["NeurIPS_2024_Explainable_AI_SHAP_Counterfactuals.pdf"]
            self.assertEqual(xai_doc.classification.category, "Research")
            self.assertEqual(xai_doc.classification.subcategory, "Explainable AI (XAI)")

        # Specialized Insurtech document
        if "Rapport_Actuariat_Insurtech_Tarification_Sinistres.pdf" in by_name:
            ins_doc = by_name["Rapport_Actuariat_Insurtech_Tarification_Sinistres.pdf"]
            self.assertEqual(ins_doc.classification.category, "Insurtech")

        # Specialized Sécurité Sanitaire document
        if "Dossier_Technique_Dispositifs_Medicaux_ISO13485_MDR.pdf" in by_name:
            dm_doc = by_name["Dossier_Technique_Dispositifs_Medicaux_ISO13485_MDR.pdf"]
            self.assertEqual(dm_doc.classification.category, "Sécurité Sanitaire")

        # Scanned PDF (detected as OCR required)
        scan_doc = by_name["Scanned_Archive_Record_1998.pdf"]
        self.assertEqual(scan_doc.status, FileStatus.OCR_REQUIRED)
        self.assertTrue(scan_doc.content.is_scanned)

        # Corrupted PDF (handled gracefully as Error)
        corrupt_doc = by_name["corrupted_document.pdf"]
        self.assertEqual(corrupt_doc.status, FileStatus.ERROR)

        # Step 4: CRITICAL SAFETY CHECK
        # Ensure no original file was modified, moved, or deleted
        for path_str, (orig_size, orig_mtime) in self.original_file_stats.items():
            p = Path(path_str)
            self.assertTrue(p.exists(), f"Original file must still exist: {p}")
            self.assertEqual(p.stat().st_size, orig_size, f"File size must not change: {p}")
            self.assertEqual(p.stat().st_mtime, orig_mtime, f"Modification time must not change: {p}")

        # Ensure no output directory was created or populated by analysis
        if self.test_output_dir.exists():
            files_in_output = list(self.test_output_dir.rglob("*.pdf"))
            self.assertEqual(len(files_in_output), 0, "No files should be moved during analysis")

    def test_database_persistence(self) -> None:
        """Verify storing file and classification records in SQLite."""
        if self.test_db_path.exists():
            self.test_db_path.unlink()

        db = DatabaseManager(self.test_db_path)

        # Insert a sample doc
        scanner = PDFScanner(self.test_docs_dir, include_subfolders=False)
        files = scanner.scan()
        self.assertGreater(len(files), 0)

        extractor = PDFExtractor(max_pages=2)
        meta, content = extractor.extract_all(files[0].path)

        doc = PDFDocument(
            file_info=files[0],
            metadata=meta,
            content=content,
            status=FileStatus.ANALYZED,
        )

        file_id = db.insert_file(doc)
        self.assertGreater(file_id, 0)

        from app.database.models import ClassificationResult
        cls_result = ClassificationResult(
            document_type="Report",
            category="Public Health",
            subcategory="WHO",
            confidence=0.92,
            reason="Matched keywords: world health organization",
            classifier_used="rules",
        )
        cls_id = db.insert_classification(file_id, cls_result)
        self.assertGreater(cls_id, 0)

        # Clean up test db
        if self.test_db_path.exists():
            self.test_db_path.unlink()


if __name__ == "__main__":
    unittest.main()
