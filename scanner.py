"""
scanner.py - Quet thu muc, tinh hash, quyet dinh push hay bo qua, goi Dify.
"""
import os
import hashlib
import logging

from config import config
from database import Database
from dify_client import DifyClient
from ocr import pdf_has_text, ocr_pdf

log = logging.getLogger("scanner")


def sha256_of_file(path: str, chunk_size: int = 1 << 20) -> str:
    """Tinh SHA-256 cua noi dung file (doc theo tung khoi 1MB de tiet kiem RAM)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


class Scanner:
    def __init__(self, db: Database, client: DifyClient):
        self.db = db
        self.client = client

    def _iter_files(self):
        """Duyet de quy WATCH_FOLDER, tra ve cac (duong_dan, duoi) co duoi hop le."""
        for root, _dirs, files in os.walk(config.WATCH_FOLDER):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in config.ALLOWED_EXTENSIONS:
                    yield os.path.join(root, name), ext

    def _push_one(self, file_path: str, ext: str, content_hash: str) -> bool:
        """Day 1 file len Dify. Tra ve True neu thanh cong."""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        is_text = ext in config.TEXT_EXTENSIONS
        api_type = "text" if is_text else "file"

        # Danh dau 'pending' truoc khi goi API (idempotent neu crash giua chung)
        self.db.mark_pending(
            file_path, file_name, content_hash, file_size,
            config.DATASET_ID, api_type,
        )

        temp_ocr = None
        try:
            if is_text:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                result = self.client.create_by_text(name=file_name, text=text)
            else:
                upload_path = file_path
                # PDF scan (khong co lop text) -> OCR truoc khi day
                if config.ENABLE_OCR and ext == ".pdf" and not pdf_has_text(file_path):
                    log.info("  [OCR] PDF scan, dang OCR tieng Viet: %s", file_name)
                    temp_ocr = ocr_pdf(file_path, config.OCR_LANGUAGES)
                    upload_path = temp_ocr
                # Giu ten goc cua khach du file thuc te la ban OCR tam
                result = self.client.create_by_file(upload_path, display_name=file_name)

            self.db.mark_success(content_hash, result["document_id"], result["batch"])
            log.info("  [OK] day thanh cong: %s (doc_id=%s)", file_name, result["document_id"])
            return True
        except Exception as e:
            # Bat rong vi OCR (ocrmypdf) co the nem nhieu loai loi khac nhau.
            self.db.mark_failed(content_hash, str(e))
            log.error("  [LOI] %s -> %s", file_name, e)
            return False
        finally:
            if temp_ocr and os.path.exists(temp_ocr):
                try:
                    os.remove(temp_ocr)
                except OSError:
                    pass

    def scan_once(self) -> dict:
        """Quet 1 lan. Tra ve thong ke lan quet."""
        result = {"new": 0, "skipped": 0, "failed": 0, "total": 0}
        log.info("Bat dau quet: %s", config.WATCH_FOLDER)

        for file_path, ext in self._iter_files():
            result["total"] += 1
            try:
                content_hash = sha256_of_file(file_path)
            except OSError as e:
                log.error("  [LOI] khong doc duoc file %s -> %s", file_path, e)
                result["failed"] += 1
                continue

            # Chong trung: noi dung nay da push thanh cong roi -> bo qua
            if self.db.is_already_uploaded(content_hash):
                result["skipped"] += 1
                log.debug("  [SKIP] da push: %s", os.path.basename(file_path))
                continue

            if self._push_one(file_path, ext, content_hash):
                result["new"] += 1
            else:
                result["failed"] += 1

        log.info(
            "Ket thuc quet: tong=%d, moi=%d, bo qua=%d, loi=%d",
            result["total"], result["new"], result["skipped"], result["failed"],
        )
        return result
