"""
config.py - Doc cau hinh tu file .env va kiem tra hop le.
"""
import os
import sys
from dotenv import load_dotenv

# Nap bien moi truong tu .env (nam cung thu muc voi file nay)
load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _split_exts(raw: str) -> set[str]:
    """Chuyen chuoi '.pdf,.docx' thanh set {'.pdf', '.docx'} (chu thuong)."""
    exts = set()
    for part in raw.split(","):
        part = part.strip().lower()
        if not part:
            continue
        if not part.startswith("."):
            part = "." + part
        exts.add(part)
    return exts


class Config:
    # Dify
    DIFY_BASE_URL: str = _get("DIFY_BASE_URL", "http://localhost").rstrip("/")
    DIFY_API_KEY: str = _get("DIFY_API_KEY")
    DATASET_ID: str = _get("DATASET_ID")

    # Quet thu muc
    WATCH_FOLDER: str = _get("WATCH_FOLDER")
    SCAN_INTERVAL: int = int(_get("SCAN_INTERVAL", "300") or "300")
    ALLOWED_EXTENSIONS: set[str] = _split_exts(
        _get("ALLOWED_EXTENSIONS", ".pdf,.docx,.txt")
    )
    TEXT_EXTENSIONS: set[str] = _split_exts(_get("TEXT_EXTENSIONS", ".txt,.md"))

    # Xu ly Dify
    INDEXING_TECHNIQUE: str = _get("INDEXING_TECHNIQUE", "high_quality")

    # OCR cho PDF scan
    ENABLE_OCR: bool = _get("ENABLE_OCR", "true").lower() in ("1", "true", "yes")
    OCR_LANGUAGES: str = _get("OCR_LANGUAGES", "vie+eng")
    # Thu muc chua *.traineddata (vie/eng/osd). De trong = dung mac dinh cua Tesseract.
    TESSDATA_PREFIX: str = _get("TESSDATA_PREFIX", "./tessdata")
    # De trong = tu dong do o cac vi tri cai dat mac dinh tren Windows.
    TESSERACT_DIR: str = _get("TESSERACT_DIR")
    GHOSTSCRIPT_DIR: str = _get("GHOSTSCRIPT_DIR")

    # Khac
    DB_PATH: str = _get("DB_PATH", "./uploaded_files.db")
    LOG_LEVEL: str = _get("LOG_LEVEL", "INFO").upper()

    @classmethod
    def validate(cls) -> None:
        """Kiem tra cac gia tri bat buoc, thoat neu thieu."""
        errors = []
        if not cls.DIFY_API_KEY or cls.DIFY_API_KEY.startswith("dataset-xxxx"):
            errors.append("DIFY_API_KEY chua duoc dien trong .env")
        if not cls.DATASET_ID or cls.DATASET_ID == "your-dataset-id-here":
            errors.append("DATASET_ID chua duoc dien trong .env")
        if not cls.WATCH_FOLDER:
            errors.append("WATCH_FOLDER chua duoc dien trong .env")
        elif not os.path.isdir(cls.WATCH_FOLDER):
            errors.append(f"WATCH_FOLDER khong ton tai: {cls.WATCH_FOLDER}")

        if errors:
            print("[CONFIG] Loi cau hinh:")
            for e in errors:
                print(f"   - {e}")
            sys.exit(1)


config = Config()
