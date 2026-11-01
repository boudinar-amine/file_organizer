"""Safe file movement and copying engine.

CRITICAL SAFETY RULES:
1. NEVER overwrite an existing file.
2. Default behavior supports COPY (Safe Test Mode) and MOVE.
3. If destination filename exists: detect conflict, do not overwrite.
4. Verify file integrity after copy/move (check target exists and size matches).
5. Never delete source on failed copy.
6. Record every successful operation in SQLite transaction log for undo.
"""

from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from app.database.database import DatabaseManager
from app.database.models import (
    FileOperation,
    FileStatus,
    OperationType,
    PDFDocument,
)
from app.utils.app_logging import get_logger

logger = get_logger("organizer.file_mover")


class ConflictResolution(str, Enum):
    """Strategy when a file with the destination name already exists."""
    SKIP_AND_FLAG = "skip_and_flag"  # Flag as conflict, do not move/copy
    AUTO_RENAME = "auto_rename"      # Append counter: "doc (1).pdf"


@dataclass
class FileOperationResult:
    """Detailed result of a single file move/copy attempt."""
    success: bool
    document: PDFDocument
    source_path: Path
    destination_path: Optional[Path] = None
    operation_type: OperationType = OperationType.COPY
    error: Optional[str] = None
    was_renamed: bool = False
    conflict_detected: bool = False


class FileMover:
    """Executes safe file operations (copy/move) with SQLite transaction logging.

    Attributes:
        db: DatabaseManager instance for transaction logging.
        operation_type: COPY (safe default) or MOVE.
        conflict_resolution: Strategy for handling name collisions.
    """

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        operation_type: OperationType = OperationType.COPY,
        conflict_resolution: ConflictResolution = ConflictResolution.SKIP_AND_FLAG,
    ) -> None:
        self.db = db or DatabaseManager()
        self.operation_type = operation_type
        self.conflict_resolution = conflict_resolution

    def organize_documents(
        self,
        documents: list[PDFDocument],
        batch_id: Optional[str] = None,
    ) -> list[FileOperationResult]:
        """Organize a list of approved documents.

        Args:
            documents: List of PDFDocument objects with populated `suggested_path`.
            batch_id: Optional unique batch identifier for undo grouping.

        Returns:
            List of FileOperationResult objects for each document.
        """
        active_batch_id = batch_id or f"batch_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
        results: list[FileOperationResult] = []

        for doc in documents:
            # Skip invalid, rejected, or ignored documents
            if doc.status in (FileStatus.REJECTED, FileStatus.IGNORED, FileStatus.ERROR):
                continue
            if not doc.suggested_path:
                continue

            result = self.process_document(doc, active_batch_id)
            results.append(result)

        logger.info(
            "Batch %s completed: %d processed, %d succeeded, %d conflicts/errors",
            active_batch_id,
            len(results),
            sum(1 for r in results if r.success),
            sum(1 for r in results if not r.success),
        )
        return results

    def process_document(
        self,
        doc: PDFDocument,
        batch_id: str = "",
    ) -> FileOperationResult:
        """Move or copy a single document to its suggested destination.

        Args:
            doc: The PDFDocument with `suggested_path`.
            batch_id: Batch identifier for undo grouping.

        Returns:
            FileOperationResult indicating outcome.
        """
        source = doc.file_info.path.resolve()
        target = doc.suggested_path.resolve()

        # Pre-flight check 1: Source must exist
        if not source.exists():
            msg = f"Source file does not exist: {source}"
            logger.error(msg)
            doc.status = FileStatus.ERROR
            doc.error_message = msg
            return FileOperationResult(
                success=False,
                document=doc,
                source_path=source,
                destination_path=target,
                operation_type=self.operation_type,
                error=msg,
            )

        # Pre-flight check 2: Source and destination must not be the same path
        if source == target:
            msg = "Source and destination are identical"
            logger.warning("%s for %s", msg, source.name)
            return FileOperationResult(
                success=True,
                document=doc,
                source_path=source,
                destination_path=target,
                operation_type=self.operation_type,
            )

        # Pre-flight check 3: Destination directory creation
        target_dir = target.parent
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            msg = f"Cannot create destination directory {target_dir}: {e}"
            logger.error(msg)
            doc.status = FileStatus.ERROR
            doc.error_message = msg
            return FileOperationResult(
                success=False,
                document=doc,
                source_path=source,
                destination_path=target,
                operation_type=self.operation_type,
                error=msg,
            )

        # Pre-flight check 4: Filename conflict prevention
        was_renamed = False
        if target.exists():
            if self.conflict_resolution == ConflictResolution.SKIP_AND_FLAG:
                msg = f"Filename conflict: {target.name} already exists in destination"
                logger.warning("%s. Skipping file.", msg)
                doc.status = FileStatus.CONFLICT
                doc.error_message = msg
                return FileOperationResult(
                    success=False,
                    document=doc,
                    source_path=source,
                    destination_path=target,
                    operation_type=self.operation_type,
                    error=msg,
                    conflict_detected=True,
                )
            elif self.conflict_resolution == ConflictResolution.AUTO_RENAME:
                target = self._generate_unique_path(target)
                was_renamed = True
                logger.info("Destination renamed to avoid conflict: %s", target.name)

        # Execute safe file movement/copy
        try:
            orig_size = source.stat().st_size

            if self.operation_type == OperationType.MOVE:
                shutil.move(str(source), str(target))
                doc.status = FileStatus.MOVED
            else:
                shutil.copy2(str(source), str(target))
                doc.status = FileStatus.COPIED

            # Verification: Target exists and size matches
            if not target.exists():
                raise FileNotFoundError(f"Verification failed: {target} does not exist after operation")

            new_size = target.stat().st_size
            if new_size != orig_size:
                raise IOError(f"Verification failed: Size mismatch ({orig_size} vs {new_size})")

            # Update document paths
            doc.suggested_path = target

            # Commit to SQLite transaction log
            op = FileOperation(
                original_path=source,
                new_path=target,
                filename=source.name,
                file_size=orig_size,
                operation_type=self.operation_type,
                classification_summary=(
                    f"{doc.classification.category}/{doc.classification.subcategory}"
                    if doc.classification
                    else ""
                ),
                confidence=doc.classification.confidence if doc.classification else 0.0,
                status="completed",
                batch_id=batch_id,
            )
            self.db.log_operation(op, file_id=doc.id)

            logger.info(
                "Successfully %s: %s -> %s",
                "moved" if self.operation_type == OperationType.MOVE else "copied",
                source.name,
                target,
            )

            return FileOperationResult(
                success=True,
                document=doc,
                source_path=source,
                destination_path=target,
                operation_type=self.operation_type,
                was_renamed=was_renamed,
            )

        except Exception as e:
            error_msg = f"Failed to {self.operation_type.value} file: {e}"
            logger.exception("%s for %s", error_msg, source.name)
            doc.status = FileStatus.ERROR
            doc.error_message = error_msg

            return FileOperationResult(
                success=False,
                document=doc,
                source_path=source,
                destination_path=target,
                operation_type=self.operation_type,
                error=error_msg,
            )

    @staticmethod
    def _generate_unique_path(target: Path) -> Path:
        """Generate a safe, unique filename by appending a counter: 'name (1).pdf'."""
        parent = target.parent
        stem = target.stem
        suffix = target.suffix
        counter = 1

        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
