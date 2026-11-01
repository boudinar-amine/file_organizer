"""Organization planner — proposes a folder structure without moving files.

This module takes classified PDFDocuments and plans where each file should
be moved. It does NOT move any file — that responsibility belongs to
file_mover.py (not yet implemented in Phase 1–3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.database.models import (
    ClassificationResult,
    FileStatus,
    PDFDocument,
)
from app.utils.app_logging import get_logger
from app.utils.validators import sanitize_folder_name

logger = get_logger("organizer.planner")


class OrganizationPlanner:
    """Plans file organization without touching the filesystem.

    Attributes:
        output_root: The root directory where organized files will go.
    """

    def __init__(self, output_root: Path) -> None:
        """Initialize the planner.

        Args:
            output_root: Base directory for the organized folder structure.
        """
        self.output_root = output_root.resolve()

    def plan(self, documents: list[PDFDocument]) -> list[PDFDocument]:
        """Generate a suggested destination path for each document.

        Modifies each document's `suggested_path` in place and returns the
        full list.  Does NOT touch the filesystem.

        Args:
            documents: List of classified PDFDocument objects.

        Returns:
            The same list with `suggested_path` populated.
        """
        for doc in documents:
            if doc.classification is None:
                doc.suggested_path = None
                continue

            if doc.status == FileStatus.ERROR:
                doc.suggested_path = None
                continue

            suggested = self._compute_destination(doc)
            doc.suggested_path = suggested

        logger.info("Planned organization for %d documents.", len(documents))
        return documents

    def _compute_destination(self, doc: PDFDocument) -> Optional[Path]:
        """Compute the destination path for a single document.

        Section 21:
        - Work context: output_root / Work / Organization / Category / Subcategory / filename
        - Other contexts: output_root / Scope / Category / Subcategory / filename
        - General fallback: output_root / Category / Subcategory / filename

        Args:
            doc: The PDFDocument with classification data.

        Returns:
            Suggested destination Path, or None if classification is missing.
        """
        cls = doc.classification
        if cls is None:
            return None

        scope = sanitize_folder_name(cls.scope) if cls.scope else "Work"
        category = sanitize_folder_name(cls.category) if cls.category else "Uncategorized"
        subcategory = sanitize_folder_name(cls.subcategory) if cls.subcategory else "General"
        org = sanitize_folder_name(cls.organization) if cls.organization else ""

        # Skip trivial "Unknown/Unknown" nesting
        if category == "Unknown" and subcategory == "Unknown":
            return self.output_root / "Review" / doc.file_info.filename

        parts: list[str] = []

        if scope in ("Learning", "Training", "Reference", "Personal"):
            parts.append(scope)
            if category != "Unknown":
                parts.append(category)
            if subcategory not in ("Unknown", "General", category):
                parts.append(subcategory)
        else:
            # Scope is Work
            # If an organization is known: Work / Organization / Category / Subcategory
            if org and org not in ("Unknown", "None"):
                parts.extend(["Work", org, category])
                if subcategory not in ("Unknown", "General", category):
                    parts.append(subcategory)
            else:
                # If no organization is specified, route directly to Category / Subcategory
                parts.append(category)
                if subcategory not in ("Unknown", "General", category):
                    parts.append(subcategory)

        dest_dir = self.output_root
        for p in parts:
            dest_dir = dest_dir / p

        return dest_dir / doc.file_info.filename

    def get_planned_structure(self, documents: list[PDFDocument]) -> dict[str, list[str]]:
        """Build a summary of the planned folder structure.

        Returns:
            Dict mapping folder paths to lists of filenames destined for them.
        """
        structure: dict[str, list[str]] = {}
        for doc in documents:
            if doc.suggested_path is None:
                continue
            folder = str(doc.suggested_path.parent)
            if folder not in structure:
                structure[folder] = []
            structure[folder].append(doc.file_info.filename)
        return structure
