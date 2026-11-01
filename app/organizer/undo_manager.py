"""Undo manager — restores moved or copied files to their original locations.

Uses the SQLite transaction log to track operations and reverse them safely.

CRITICAL SAFETY INVARIANTS:
1. Before moving a file back, verify `original_path` does NOT exist to prevent overwrite.
2. For COPY operations, safely remove the copy at `new_path` (original file is untouched).
3. If a conflict or error occurs, log it and continue with remaining files without data loss.
4. Update the SQLite transaction log to mark operations as 'undone'.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.database.database import DatabaseManager
from app.database.models import OperationType
from app.utils.app_logging import get_logger

logger = get_logger("organizer.undo")


@dataclass
class UndoResult:
    """Summary result of an undo batch execution."""
    success: bool
    undone_count: int = 0
    failed_count: int = 0
    errors: list[str] = field(default_factory=list)
    batch_id: str = ""


class UndoManager:
    """Reverses file operations using the SQLite transaction log.

    Attributes:
        db: DatabaseManager instance connected to the transaction log.
    """

    def __init__(self, db: Optional[DatabaseManager] = None) -> None:
        self.db = db or DatabaseManager()

    def can_undo(self) -> bool:
        """Check if there is an active batch of operations eligible for undo."""
        ops = self.db.get_last_batch_operations()
        return len(ops) > 0

    def get_last_batch_summary(self) -> Optional[dict]:
        """Return metadata about the most recent active batch."""
        ops = self.db.get_last_batch_operations()
        if not ops:
            return None
        return {
            "batch_id": ops[0].get("batch_id", ""),
            "count": len(ops),
            "timestamp": ops[0].get("timestamp", ""),
            "operation_type": ops[0].get("operation_type", ""),
        }

    def undo_last_batch(self) -> UndoResult:
        """Undo the most recent organization batch.

        Reverses moved files back to their original paths or removes copies.
        Commits status='undone' to the database.

        Returns:
            UndoResult summary.
        """
        ops = self.db.get_last_batch_operations()
        if not ops:
            logger.warning("No active operations found to undo.")
            return UndoResult(success=True, undone_count=0, failed_count=0, errors=["No operations to undo"])

        batch_id = ops[0].get("batch_id", "")
        undone_ids: list[int] = []
        errors: list[str] = []

        logger.info("Starting undo for batch %s (%d file(s))", batch_id, len(ops))

        for row in ops:
            op_id = row["id"]
            orig_path = Path(row["original_path"])
            new_path = Path(row["new_path"])
            op_type = row["operation_type"]

            try:
                if op_type == OperationType.MOVE.value:
                    self._undo_move(orig_path, new_path)
                elif op_type == OperationType.COPY.value:
                    self._undo_copy(orig_path, new_path)
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")

                undone_ids.append(op_id)
                logger.info("Undone %s: %s", op_type, orig_path.name)

            except Exception as e:
                err_msg = f"Cannot undo {orig_path.name}: {e}"
                logger.error(err_msg)
                errors.append(err_msg)

        # Update database statuses for all successfully reversed operations
        if undone_ids:
            self.db.mark_operations_undone(undone_ids)

        success = len(errors) == 0
        logger.info(
            "Undo complete for batch %s: %d reversed, %d failed",
            batch_id,
            len(undone_ids),
            len(errors),
        )

        return UndoResult(
            success=success,
            undone_count=len(undone_ids),
            failed_count=len(errors),
            errors=errors,
            batch_id=batch_id,
        )

    # ------------------------------------------------------------------
    # Internal Handlers
    # ------------------------------------------------------------------

    @staticmethod
    def _undo_move(orig_path: Path, new_path: Path) -> None:
        """Reverse a MOVE: move file from new_path back to orig_path."""
        if not new_path.exists():
            raise FileNotFoundError(f"File at organized location not found: {new_path}")

        # CRITICAL SAFETY: Never overwrite an existing file during undo
        if orig_path.exists():
            raise FileExistsError(
                f"Cannot restore {orig_path.name}: a file already exists at original location {orig_path}"
            )

        orig_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(new_path), str(orig_path))

        # Clean up empty parent directories in organized structure
        try:
            parent = new_path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except Exception:
            pass

    @staticmethod
    def _undo_copy(orig_path: Path, new_path: Path) -> None:
        """Reverse a COPY: remove the copy at new_path."""
        if new_path.exists():
            new_path.unlink()

        # Clean up empty parent directories in organized structure
        try:
            parent = new_path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except Exception:
            pass
