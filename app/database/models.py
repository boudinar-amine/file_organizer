"""Data models used throughout the application.

These are plain dataclasses — they carry data between layers and are NOT
tied to any database ORM. The database layer maps them to/from SQLite rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class FileStatus(str, Enum):
    """Processing status of a scanned PDF."""
    PENDING = "pending"
    ANALYZED = "analyzed"
    APPROVED = "approved"
    REJECTED = "rejected"
    IGNORED = "ignored"
    MOVED = "moved"
    COPIED = "copied"
    CONFLICT = "conflict"
    ERROR = "error"
    OCR_REQUIRED = "ocr_required"


class ConfidenceLevel(str, Enum):
    """Human-readable confidence bucket."""
    HIGH = "high"          # 0.85 – 1.00
    MEDIUM = "medium"      # 0.65 – 0.84
    LOW = "low"            # 0.00 – 0.64

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.85:
            return cls.HIGH
        elif score >= 0.65:
            return cls.MEDIUM
        return cls.LOW


class OperationType(str, Enum):
    """Type of file operation recorded in the transaction log."""
    MOVE = "move"
    COPY = "copy"
    UNDO = "undo"


@dataclass
class PDFFileInfo:
    """Information collected by the scanner about a single PDF file."""
    path: Path
    filename: str
    extension: str
    size_bytes: int
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    @property
    def size_human(self) -> str:
        """Return a human-readable file size string."""
        size = self.size_bytes
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


@dataclass
class PDFMetadata:
    """Metadata extracted from a PDF document."""
    page_count: int = 0
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    mod_date: Optional[str] = None


@dataclass
class PDFContent:
    """Text content extracted from a PDF document."""
    extracted_text: str = ""
    pages_analyzed: int = 0
    total_pages: int = 0
    is_scanned: bool = False
    extraction_error: Optional[str] = None

    @property
    def has_usable_text(self) -> bool:
        """Check if meaningful text was extracted."""
        stripped = self.extracted_text.strip()
        # Consider text usable if it has at least 50 non-whitespace chars
        return len(stripped) >= 50


@dataclass
class ClassificationResult:
    """Result of classifying a single PDF document across Context, Relationship, and Content."""
    document_type: str = "Unknown"
    category: str = "Unknown"
    subcategory: str = "Unknown"
    topic: str = ""
    organization: str = ""
    year: str = ""
    confidence: float = 0.0
    reason: str = ""
    classifier_used: str = ""
    # Section 21: Three fundamental dimensions
    scope: str = "Work"              # Context: Work, Personal, Learning, Training, Reference
    work_context: str = ""          # Relationship: Current Employment, Previous Employment, Consulting, Research, etc.
    role: str = ""                  # Inferred or matched professional role
    project: str = ""               # Inferred or matched project alias
    extracted_signals: dict = field(default_factory=dict)  # Signal weights breakdown

    @property
    def confidence_level(self) -> ConfidenceLevel:
        return ConfidenceLevel.from_score(self.confidence)

    @property
    def needs_review(self) -> bool:
        return self.confidence < 0.65


@dataclass
class PDFDocument:
    """Complete representation of a PDF document through the pipeline.

    Aggregates scan info, metadata, content, and classification.
    """
    file_info: PDFFileInfo
    metadata: Optional[PDFMetadata] = None
    content: Optional[PDFContent] = None
    classification: Optional[ClassificationResult] = None
    status: FileStatus = FileStatus.PENDING
    suggested_path: Optional[Path] = None
    error_message: Optional[str] = None
    id: Optional[int] = None


@dataclass
class FileOperation:
    """Record of a file move/copy operation for the transaction log."""
    original_path: Path
    new_path: Path
    filename: str
    file_size: int
    operation_type: OperationType
    classification_summary: str = ""
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "completed"
    batch_id: str = ""
    id: Optional[int] = None
