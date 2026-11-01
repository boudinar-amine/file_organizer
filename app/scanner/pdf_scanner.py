"""PDF file scanner — recursively discovers PDF files in a directory.

This module ONLY scans the filesystem to find PDF files and collect
basic file information. It does NOT read PDF content or modify files.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Generator

from app.database.models import PDFFileInfo
from app.utils.app_logging import get_logger

logger = get_logger("scanner")


class PDFScanner:
    """Recursively scans a directory for PDF files.

    Attributes:
        root: The root directory to scan.
        include_subfolders: Whether to scan subdirectories recursively.
    """

    SUPPORTED_EXTENSIONS = {".pdf"}

    def __init__(self, root: Path, include_subfolders: bool = True) -> None:
        """Initialize the scanner.

        Args:
            root: The root directory to scan.
            include_subfolders: Whether to scan subdirectories.

        Raises:
            FileNotFoundError: If root does not exist.
            NotADirectoryError: If root is not a directory.
        """
        self.root = root.resolve()
        self.include_subfolders = include_subfolders

        if not self.root.exists():
            raise FileNotFoundError(f"Directory not found: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.root}")

    def scan(self) -> list[PDFFileInfo]:
        """Scan the root directory and return a list of PDF file info objects.

        Returns:
            List of PDFFileInfo for every PDF found.
        """
        results: list[PDFFileInfo] = []
        for info in self._iter_pdfs():
            results.append(info)
        logger.info("Scan complete: found %d PDF(s) in %s", len(results), self.root)
        return results

    def scan_generator(self) -> Generator[PDFFileInfo, None, None]:
        """Yield PDFFileInfo objects one at a time (for progress reporting).

        Yields:
            PDFFileInfo for each discovered PDF.
        """
        yield from self._iter_pdfs()

    def count_pdfs(self) -> int:
        """Quickly count PDFs without collecting metadata.

        Returns:
            Number of PDF files found.
        """
        count = 0
        pattern = "**/*.pdf" if self.include_subfolders else "*.pdf"
        for p in self.root.glob(pattern):
            if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                count += 1
        return count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _iter_pdfs(self) -> Generator[PDFFileInfo, None, None]:
        """Internal generator that walks the directory tree.

        Yields:
            PDFFileInfo for each valid PDF file found.
        """
        pattern = "**/*.pdf" if self.include_subfolders else "*.pdf"

        for file_path in self.root.glob(pattern):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            try:
                info = self._build_file_info(file_path)
                yield info
            except PermissionError:
                logger.warning("Permission denied: %s", file_path)
            except OSError as e:
                logger.warning("OS error scanning %s: %s", file_path, e)

    @staticmethod
    def _build_file_info(path: Path) -> PDFFileInfo:
        """Build a PDFFileInfo from a file path.

        Args:
            path: Absolute path to the PDF file.

        Returns:
            Populated PDFFileInfo dataclass.
        """
        stat = path.stat()
        created_at = None
        modified_at = None

        try:
            created_at = datetime.fromtimestamp(stat.st_ctime)
        except (OSError, ValueError):
            pass

        try:
            modified_at = datetime.fromtimestamp(stat.st_mtime)
        except (OSError, ValueError):
            pass

        return PDFFileInfo(
            path=path.resolve(),
            filename=path.name,
            extension=path.suffix.lower(),
            size_bytes=stat.st_size,
            created_at=created_at,
            modified_at=modified_at,
        )
