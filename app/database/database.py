"""SQLite database manager for the PDF Organizer.

Handles all database operations: creating tables, inserting records,
querying, and supporting undo operations via the transaction log.

This module is the ONLY place that talks to SQLite — no other module
should import sqlite3 directly.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from app.database.models import (
    ClassificationResult,
    FileOperation,
    FileStatus,
    OperationType,
    PDFDocument,
    PDFFileInfo,
    PDFMetadata,
    PDFContent,
)
from app.utils.app_logging import get_logger
from app.utils.paths import get_db_path

logger = get_logger("database")


class DatabaseManager:
    """Manages the SQLite database for the PDF Organizer.

    Attributes:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize the database manager.

        Args:
            db_path: Path to the database file. Defaults to the standard
                     app data location.
        """
        self.db_path = db_path or get_db_path()
        self._ensure_tables()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that yields a database connection.

        Commits on clean exit, rolls back on exception.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_tables(self) -> None:
        """Create database tables if they do not exist."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT,
                    modified_at TEXT,
                    page_count INTEGER DEFAULT 0,
                    pdf_title TEXT,
                    pdf_author TEXT,
                    pdf_subject TEXT,
                    extracted_text_preview TEXT,
                    is_scanned INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    document_type TEXT,
                    category TEXT,
                    subcategory TEXT,
                    topic TEXT,
                    organization TEXT,
                    year TEXT,
                    confidence REAL DEFAULT 0.0,
                    reason TEXT,
                    classifier_used TEXT,
                    scope TEXT DEFAULT 'Work',
                    work_context TEXT,
                    role TEXT,
                    project TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES files(id)
                );

                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    original_path TEXT NOT NULL,
                    new_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    operation_type TEXT NOT NULL,
                    classification_summary TEXT,
                    confidence REAL DEFAULT 0.0,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed',
                    batch_id TEXT,
                    FOREIGN KEY (file_id) REFERENCES files(id)
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    parent_id INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES categories(id)
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            # Ensure batch_id column exists on older databases
            try:
                conn.execute("ALTER TABLE operations ADD COLUMN batch_id TEXT")
            except Exception:
                pass

            # Ensure Section 21 classification columns exist on older databases
            for col in ("scope", "work_context", "role", "project"):
                try:
                    conn.execute(f"ALTER TABLE classifications ADD COLUMN {col} TEXT")
                except Exception:
                    pass
        logger.info("Database tables ensured at %s", self.db_path)

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    def insert_file(self, doc: PDFDocument) -> int:
        """Insert or update a scanned PDF file record.

        Args:
            doc: The PDFDocument to store.

        Returns:
            The database row ID.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO files (
                    path, filename, extension, size_bytes,
                    created_at, modified_at, page_count,
                    pdf_title, pdf_author, pdf_subject,
                    extracted_text_preview, is_scanned, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    filename=excluded.filename,
                    size_bytes=excluded.size_bytes,
                    modified_at=excluded.modified_at,
                    page_count=excluded.page_count,
                    pdf_title=excluded.pdf_title,
                    pdf_author=excluded.pdf_author,
                    pdf_subject=excluded.pdf_subject,
                    extracted_text_preview=excluded.extracted_text_preview,
                    is_scanned=excluded.is_scanned,
                    status=excluded.status
                """,
                (
                    str(doc.file_info.path),
                    doc.file_info.filename,
                    doc.file_info.extension,
                    doc.file_info.size_bytes,
                    doc.file_info.created_at.isoformat() if doc.file_info.created_at else None,
                    doc.file_info.modified_at.isoformat() if doc.file_info.modified_at else None,
                    doc.metadata.page_count if doc.metadata else 0,
                    doc.metadata.title if doc.metadata else None,
                    doc.metadata.author if doc.metadata else None,
                    doc.metadata.subject if doc.metadata else None,
                    doc.content.extracted_text[:500] if doc.content else None,
                    1 if (doc.content and doc.content.is_scanned) else 0,
                    doc.status.value,
                ),
            )
            return cursor.lastrowid or 0

    # ------------------------------------------------------------------
    # Classifications
    # ------------------------------------------------------------------

    def insert_classification(self, file_id: int, result: ClassificationResult) -> int:
        """Store a classification result for a file.

        Args:
            file_id: The database ID of the file.
            result: The classification result.

        Returns:
            The classification row ID.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO classifications (
                    file_id, document_type, category, subcategory,
                    topic, organization, year, confidence, reason,
                    classifier_used, scope, work_context, role, project
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    result.document_type,
                    result.category,
                    result.subcategory,
                    result.topic,
                    result.organization,
                    result.year,
                    result.confidence,
                    result.reason,
                    result.classifier_used,
                    result.scope,
                    result.work_context,
                    result.role,
                    result.project,
                ),
            )
            return cursor.lastrowid or 0

    # ------------------------------------------------------------------
    # Operations (transaction log)
    # ------------------------------------------------------------------

    def log_operation(self, op: FileOperation, file_id: Optional[int] = None) -> int:
        """Log a file move/copy/undo operation.

        Args:
            op: The operation record.
            file_id: Optional database ID of the file.

        Returns:
            The operation row ID.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO operations (
                    file_id, original_path, new_path, filename,
                    file_size, operation_type, classification_summary,
                    confidence, timestamp, status, batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    str(op.original_path),
                    str(op.new_path),
                    op.filename,
                    op.file_size,
                    op.operation_type.value,
                    op.classification_summary,
                    op.confidence,
                    op.timestamp.isoformat(),
                    op.status,
                    op.batch_id or "",
                ),
            )
            return cursor.lastrowid or 0

    def get_last_batch_operations(self) -> list[dict]:
        """Get the completed operations from the most recent active batch.

        Returns:
            List of operation dicts from the newest batch, or empty list.
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT batch_id FROM operations
                WHERE status = 'completed' AND batch_id != ''
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
            if not row or not row["batch_id"]:
                return []

            batch_id = row["batch_id"]
            rows = conn.execute(
                """
                SELECT * FROM operations
                WHERE batch_id = ? AND status = 'completed'
                ORDER BY id DESC
                """,
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_operations_undone(self, operation_ids: list[int]) -> None:
        """Mark operations as undone in the transaction log.

        Args:
            operation_ids: List of operation row IDs to mark.
        """
        if not operation_ids:
            return
        with self._connect() as conn:
            placeholders = ",".join("?" for _ in operation_ids)
            conn.execute(
                f"UPDATE operations SET status = 'undone' WHERE id IN ({placeholders})",
                operation_ids,
            )

    def get_last_operations(self, limit: int = 50) -> list[dict]:
        """Get the most recent operations from the transaction log.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of operation dicts, newest first.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM operations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_setting(self, key: str, default: str = "") -> str:
        """Read a setting value.

        Args:
            key: The setting key.
            default: Default value if the key doesn't exist.

        Returns:
            The setting value string.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Write a setting value.

        Args:
            key: The setting key.
            value: The setting value.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value),
            )

    # ------------------------------------------------------------------
    # Cleanup / utility
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        """Delete all data from all tables. Use with caution (testing only)."""
        with self._connect() as conn:
            for table in ("operations", "classifications", "files", "categories", "settings"):
                conn.execute(f"DELETE FROM {table}")
        logger.warning("All database tables cleared.")
