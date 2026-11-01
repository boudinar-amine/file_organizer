"""PDF text and metadata extraction using PyMuPDF (fitz).

This module reads PDF files to extract metadata and textual content.
It does NOT modify any file on disk.

Design notes:
- Large PDFs are not fully read: only a configurable number of pages are
  extracted (default: first 2 pages).
- Scanned PDFs (with no extractable text) are flagged rather than OCR'd.
- The architecture is designed so OCR can be added later as a pluggable step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.database.models import PDFContent, PDFMetadata
from app.utils.app_logging import get_logger

logger = get_logger("extraction")

# Minimum characters of extracted text to consider a page "useful"
_MIN_USEFUL_CHARS = 30

# Default maximum pages to analyze
DEFAULT_MAX_PAGES = 2

def _get_fitz():
    """Import PyMuPDF without triggering deprecation warnings."""
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        import fitz
        return fitz


class PDFExtractor:
    """Extract metadata and text from a PDF file.

    Attributes:
        max_pages: Maximum number of pages to extract text from.
    """

    def __init__(self, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        """Initialize the extractor.

        Args:
            max_pages: Maximum number of pages to analyze for text content.
        """
        self.max_pages = max(1, max_pages)

    def extract_metadata(self, file_path: Path) -> PDFMetadata:
        """Extract PDF metadata (title, author, page count, etc.).

        Args:
            file_path: Path to the PDF file.

        Returns:
            PDFMetadata with whatever fields could be read.
        """
        try:
            fitz = _get_fitz()
        except ImportError:
            logger.error("PyMuPDF (pymupdf/fitz) is not installed.")
            return PDFMetadata()

        try:
            with fitz.open(str(file_path)) as doc:
                meta = doc.metadata or {}
                raw_title = meta.get("title", "").strip() or None
                author = meta.get("author", "").strip() or None
                subject = meta.get("subject", "").strip() or None

                # Detect if the embedded title is missing or generic (e.g. Word export, Untitled)
                title = self._detect_effective_title(doc, raw_title)

                return PDFMetadata(
                    page_count=len(doc),
                    title=title,
                    author=author,
                    subject=subject,
                    creator=meta.get("creator", "").strip() or None,
                    producer=meta.get("producer", "").strip() or None,
                    creation_date=meta.get("creationDate", "").strip() or None,
                    mod_date=meta.get("modDate", "").strip() or None,
                )
        except Exception as e:
            logger.warning("Failed to extract metadata from %s: %s", file_path.name, e)
            return PDFMetadata()

    @staticmethod
    def _detect_effective_title(doc, raw_title: Optional[str]) -> Optional[str]:
        """Return the embedded title if meaningful, otherwise extract the first headline."""
        generic_markers = [
            "microsoft word", "untitled", "document1", "scanner", "scan",
            "sans titre", "nouveau document", "presentation1",
        ]
        is_generic = (
            raw_title is not None
            and any(m in raw_title.lower() for m in generic_markers)
        )

        if raw_title and not is_generic and len(raw_title) > 2:
            return raw_title

        # Attempt to extract the first prominent headline from page 1
        try:
            if len(doc) > 0:
                page = doc[0]
                blocks = page.get_text("blocks")
                for b in blocks:
                    # b: (x0, y0, x1, y1, text, block_no, block_type)
                    if len(b) >= 7 and b[6] == 0:  # text block
                        candidate = b[4].strip().split("\n")[0].strip()
                        # Skip page numbers, short symbols, or pure dates
                        if len(candidate) > 4 and not candidate.isdigit():
                            return candidate[:140]
        except Exception:
            pass

        return raw_title

    def extract_text(self, file_path: Path) -> PDFContent:
        """Extract text from a PDF, limited to self.max_pages pages.

        Strategy:
        1. Extract text from the first `max_pages` pages.
        2. Optionally include the last page (if not already included).
        3. If very little text is found, flag as scanned/OCR-required.

        Args:
            file_path: Path to the PDF file.

        Returns:
            PDFContent with extracted text and scanning flags.
        """
        try:
            fitz = _get_fitz()
        except ImportError:
            logger.error("PyMuPDF (pymupdf/fitz) is not installed.")
            return PDFContent(
                extraction_error="PyMuPDF not installed",
                is_scanned=False,
            )

        try:
            with fitz.open(str(file_path)) as doc:
                total_pages = len(doc)
                if total_pages == 0:
                    return PDFContent(
                        extracted_text="",
                        pages_analyzed=0,
                        total_pages=0,
                        is_scanned=False,
                        extraction_error="PDF has zero pages",
                    )

                pages_to_read = self._select_pages(total_pages)
                text_parts: list[str] = []
                pages_analyzed = 0

                for page_num in pages_to_read:
                    try:
                        page = doc[page_num]
                        page_text = page.get_text("text") or ""
                        if page_text.strip():
                            text_parts.append(
                                f"--- Page {page_num + 1} ---\n{page_text.strip()}"
                            )
                        pages_analyzed += 1
                    except Exception as e:
                        logger.warning(
                            "Error extracting page %d from %s: %s",
                            page_num + 1,
                            file_path.name,
                            e,
                        )

                full_text = "\n\n".join(text_parts)
                is_scanned = self._detect_scanned(full_text, pages_analyzed)

                return PDFContent(
                    extracted_text=full_text,
                    pages_analyzed=pages_analyzed,
                    total_pages=total_pages,
                    is_scanned=is_scanned,
                )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.warning("Failed to extract text from %s: %s", file_path.name, e)
            return PDFContent(
                extraction_error=error_msg,
                is_scanned=False,
            )

    def extract_all(self, file_path: Path) -> tuple[PDFMetadata, PDFContent]:
        """Extract both metadata and text content from a PDF.

        Convenience method that calls extract_metadata and extract_text.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Tuple of (PDFMetadata, PDFContent).
        """
        metadata = self.extract_metadata(file_path)
        content = self.extract_text(file_path)
        # Propagate page count from metadata to content if missing
        if content.total_pages == 0 and metadata.page_count > 0:
            content.total_pages = metadata.page_count
        return metadata, content

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_pages(self, total_pages: int) -> list[int]:
        """Determine which page indices to extract text from.

        Strategy:
        - Always include the first `max_pages` pages (0-indexed).
        - If the last page is not already included, add it.

        Args:
            total_pages: Total number of pages in the PDF.

        Returns:
            Sorted list of unique 0-based page indices.
        """
        pages: set[int] = set()

        # First N pages
        for i in range(min(self.max_pages, total_pages)):
            pages.add(i)

        # Last page (if document is longer)
        if total_pages > 1:
            pages.add(total_pages - 1)

        return sorted(pages)

    @staticmethod
    def _detect_scanned(extracted_text: str, pages_analyzed: int) -> bool:
        """Heuristically detect if a PDF appears to be scanned (image-only).

        A PDF is considered scanned if the extracted text is very short
        relative to the number of pages analyzed.

        Args:
            extracted_text: The combined extracted text.
            pages_analyzed: How many pages were read.

        Returns:
            True if the PDF likely needs OCR.
        """
        if pages_analyzed == 0:
            return True

        stripped = extracted_text.strip()
        # Less than 50 chars per analyzed page → likely scanned
        chars_per_page = len(stripped) / pages_analyzed if pages_analyzed else 0
        return chars_per_page < _MIN_USEFUL_CHARS
