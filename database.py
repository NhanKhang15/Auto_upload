"""
database.py - Lop truy cap SQLite luu trang thai cac file da/dang/that bai khi day len Dify.

Khoa chong trung = content_hash (SHA-256 cua noi dung file).
Trang thai (status):
    pending  : da ghi nhan, dang goi API (de retry neu crash giua chung)
    success  : da day len Dify thanh cong
    failed   : goi API loi -> lan quet sau se thu lai
"""
import sqlite3
from datetime import datetime
from contextlib import contextmanager

_SCHEMA = """
CREATE TABLE IF NOT EXISTS uploaded_files (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path        TEXT NOT NULL,
    file_name        TEXT NOT NULL,
    content_hash     TEXT NOT NULL,
    file_size        INTEGER,
    dataset_id       TEXT,
    dify_document_id TEXT,
    dify_batch       TEXT,
    api_type         TEXT,
    status           TEXT NOT NULL,
    error_message    TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_hash ON uploaded_files(content_hash);
CREATE INDEX IF NOT EXISTS idx_status ON uploaded_files(status);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # ---- Tra cuu chong trung ----
    def is_already_uploaded(self, content_hash: str) -> bool:
        """True neu noi dung nay da day len Dify thanh cong roi."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM uploaded_files WHERE content_hash = ? AND status = 'success'",
                (content_hash,),
            ).fetchone()
            return row is not None

    def get_by_hash(self, content_hash: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM uploaded_files WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()

    # ---- Ghi trang thai ----
    def mark_pending(
        self, file_path: str, file_name: str, content_hash: str,
        file_size: int, dataset_id: str, api_type: str,
    ) -> None:
        """Ghi/ghi de mot row o trang thai 'pending' truoc khi goi API."""
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO uploaded_files
                    (file_path, file_name, content_hash, file_size, dataset_id,
                     api_type, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    file_path=excluded.file_path,
                    file_name=excluded.file_name,
                    file_size=excluded.file_size,
                    dataset_id=excluded.dataset_id,
                    api_type=excluded.api_type,
                    status='pending',
                    error_message=NULL,
                    updated_at=excluded.updated_at
                """,
                (file_path, file_name, content_hash, file_size, dataset_id, api_type, now, now),
            )

    def mark_success(self, content_hash: str, document_id: str, batch: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE uploaded_files
                   SET status='success', dify_document_id=?, dify_batch=?,
                       error_message=NULL, updated_at=?
                   WHERE content_hash=?""",
                (document_id, batch, _now(), content_hash),
            )

    def mark_failed(self, content_hash: str, error_message: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE uploaded_files
                   SET status='failed', error_message=?, updated_at=?
                   WHERE content_hash=?""",
                (error_message[:1000], _now(), content_hash),
            )

    # ---- Thong ke ----
    def stats(self) -> dict:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS c FROM uploaded_files GROUP BY status"
            ).fetchall()
            return {r["status"]: r["c"] for r in rows}
