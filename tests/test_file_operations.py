"""Unit tests for FileMover and UndoManager.

Validates:
1. Safe COPY mode (source preserved, target created).
2. Safe MOVE mode (source moved, target verified).
3. Conflict detection (no overwriting under SKIP_AND_FLAG).
4. Auto-rename conflict resolution (no overwriting under AUTO_RENAME).
5. Undo of COPY operations (removes copy, preserves source).
6. Undo of MOVE operations (restores file to original path).
7. Safety check: Never overwrite an existing file during undo.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.database.database import DatabaseManager
from app.database.models import (
    ClassificationResult,
    FileStatus,
    OperationType,
    PDFDocument,
    PDFFileInfo,
)
from app.organizer.file_mover import (
    ConflictResolution,
    FileMover,
)
from app.organizer.undo_manager import UndoManager


class TestFileMoverAndUndo(unittest.TestCase):
    """Test safe file operations and reversal."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.temp_dir / "source"
        self.source_dir.mkdir()
        self.target_dir = self.temp_dir / "organized"
        self.db_path = self.temp_dir / "test.db"
        self.db = DatabaseManager(self.db_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_doc(self, name: str, content: str = "PDF content") -> PDFDocument:
        p = self.source_dir / name
        p.write_text(content, encoding="utf-8")

        info = PDFFileInfo(
            path=p,
            filename=name,
            extension=".pdf",
            size_bytes=p.stat().st_size,
        )
        doc = PDFDocument(
            file_info=info,
            classification=ClassificationResult(
                category="Public Health",
                subcategory="WHO",
                confidence=0.95,
            ),
            status=FileStatus.APPROVED,
            suggested_path=self.target_dir / "Public Health" / "WHO" / name,
        )
        return doc

    def test_copy_mode_preserves_source(self) -> None:
        """Test COPY mode: destination created, source untouched."""
        doc = self._create_sample_doc("report.pdf")
        mover = FileMover(db=self.db, operation_type=OperationType.COPY)

        result = mover.process_document(doc, batch_id="batch_1")

        self.assertTrue(result.success)
        self.assertEqual(doc.status, FileStatus.COPIED)
        self.assertTrue(doc.file_info.path.exists(), "Source must still exist in COPY mode")
        self.assertTrue(result.destination_path.exists(), "Target must exist")
        self.assertEqual(
            result.destination_path.read_text(encoding="utf-8"),
            doc.file_info.path.read_text(encoding="utf-8"),
        )

        # Check database log
        ops = self.db.get_last_batch_operations()
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]["operation_type"], "copy")

    def test_move_mode_moves_file(self) -> None:
        """Test MOVE mode: file transferred to destination, source removed."""
        doc = self._create_sample_doc("move_me.pdf")
        source_path = doc.file_info.path
        mover = FileMover(db=self.db, operation_type=OperationType.MOVE)

        result = mover.process_document(doc, batch_id="batch_2")

        self.assertTrue(result.success)
        self.assertEqual(doc.status, FileStatus.MOVED)
        self.assertFalse(source_path.exists(), "Source must no longer exist after MOVE")
        self.assertTrue(result.destination_path.exists(), "Target must exist")

    def test_conflict_skip_and_flag(self) -> None:
        """Test conflict prevention: existing destination is never overwritten."""
        doc = self._create_sample_doc("conflict.pdf", "NEW content")
        # Pre-create destination with different content
        dest = doc.suggested_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("PRE-EXISTING content", encoding="utf-8")

        mover = FileMover(
            db=self.db,
            operation_type=OperationType.COPY,
            conflict_resolution=ConflictResolution.SKIP_AND_FLAG,
        )

        result = mover.process_document(doc, batch_id="batch_3")

        self.assertFalse(result.success)
        self.assertTrue(result.conflict_detected)
        self.assertEqual(doc.status, FileStatus.CONFLICT)
        # Verify existing file was NOT overwritten
        self.assertEqual(dest.read_text(encoding="utf-8"), "PRE-EXISTING content")

    def test_conflict_auto_rename(self) -> None:
        """Test auto-rename on conflict: creates 'name (1).pdf' without overwrite."""
        doc = self._create_sample_doc("auto_rename.pdf", "NEW content")
        dest = doc.suggested_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("EXISTING content", encoding="utf-8")

        mover = FileMover(
            db=self.db,
            operation_type=OperationType.COPY,
            conflict_resolution=ConflictResolution.AUTO_RENAME,
        )

        result = mover.process_document(doc, batch_id="batch_4")

        self.assertTrue(result.success)
        self.assertTrue(result.was_renamed)
        self.assertIn("auto_rename (1).pdf", str(result.destination_path))
        # Original destination still contains old content
        self.assertEqual(dest.read_text(encoding="utf-8"), "EXISTING content")
        # Renamed destination contains new content
        self.assertEqual(result.destination_path.read_text(encoding="utf-8"), "NEW content")

    def test_undo_move_operation(self) -> None:
        """Test undoing a MOVE: file restored to original location."""
        doc = self._create_sample_doc("undo_move.pdf", "Important data")
        orig_path = doc.file_info.path
        mover = FileMover(db=self.db, operation_type=OperationType.MOVE)
        res = mover.process_document(doc, batch_id="batch_undo_1")
        self.assertTrue(res.success)
        self.assertFalse(orig_path.exists())

        # Now undo
        undo_mgr = UndoManager(db=self.db)
        self.assertTrue(undo_mgr.can_undo())

        undo_res = undo_mgr.undo_last_batch()
        self.assertTrue(undo_res.success)
        self.assertEqual(undo_res.undone_count, 1)

        # File is back at original path
        self.assertTrue(orig_path.exists())
        self.assertFalse(res.destination_path.exists())
        self.assertEqual(orig_path.read_text(encoding="utf-8"), "Important data")

        # Database shows undone
        ops = self.db.get_last_batch_operations()
        self.assertEqual(len(ops), 0, "Batch operations should no longer be active")

    def test_undo_copy_operation(self) -> None:
        """Test undoing a COPY: copy is deleted, original remains."""
        doc = self._create_sample_doc("undo_copy.pdf", "Copy test")
        orig_path = doc.file_info.path
        mover = FileMover(db=self.db, operation_type=OperationType.COPY)
        res = mover.process_document(doc, batch_id="batch_undo_2")
        self.assertTrue(res.success)

        # Undo
        undo_mgr = UndoManager(db=self.db)
        undo_res = undo_mgr.undo_last_batch()

        self.assertTrue(undo_res.success)
        self.assertEqual(undo_res.undone_count, 1)
        self.assertTrue(orig_path.exists(), "Original must still exist")
        self.assertFalse(res.destination_path.exists(), "Copy must be removed")

    def test_undo_prevents_overwrite_if_file_exists(self) -> None:
        """Test safety invariant: never overwrite an existing file during undo."""
        doc = self._create_sample_doc("safe_undo.pdf", "Original")
        orig_path = doc.file_info.path
        mover = FileMover(db=self.db, operation_type=OperationType.MOVE)
        res = mover.process_document(doc, batch_id="batch_undo_3")
        self.assertTrue(res.success)

        # Someone created a new file at the original path externally
        orig_path.write_text("Interfering new file", encoding="utf-8")

        undo_mgr = UndoManager(db=self.db)
        undo_res = undo_mgr.undo_last_batch()

        self.assertFalse(undo_res.success)
        self.assertEqual(undo_res.failed_count, 1)
        # Original file wasn't overwritten
        self.assertEqual(orig_path.read_text(encoding="utf-8"), "Interfering new file")
        # Organized file was not deleted
        self.assertTrue(res.destination_path.exists())


if __name__ == "__main__":
    unittest.main()
