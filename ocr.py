"""
ocr.py - Xu ly PDF scan (anh chup, khong co lop text) bang OCR truoc khi day len Dify.

Luong:
    1. pdf_has_text(): kiem tra PDF da co lop chu chua.
    2. Neu CHUA (la PDF scan) -> ocr_pdf() chay ocrmypdf tao ban PDF co lop chu tieng Viet.

YEU CAU CAI DAT HE THONG (khong phai goi pip):
    - Tesseract OCR + goi ngon ngu tieng Viet (vie)
    - Ghostscript
Tren Windows xem huong dan o README.
"""
import os
import glob
import shutil
import logging
import tempfile

from config import config

log = logging.getLogger("ocr")


def setup_ocr_env() -> None:
    """
    Cho backend tim thay tesseract & ghostscript (neu chua nam tren PATH) va tro
    TESSDATA_PREFIX vao thu muc chua *.traineddata. Goi 1 lan khi import module.
    """
    # 1) Thu muc ngon ngu OCR (vie/eng/osd)
    if config.TESSDATA_PREFIX:
        tessdata = os.path.abspath(config.TESSDATA_PREFIX)
        if os.path.isdir(tessdata):
            os.environ["TESSDATA_PREFIX"] = tessdata

    # 2) Tesseract: dung config.TESSERACT_DIR neu co, khong thi do vi tri mac dinh
    tess_candidates = []
    if config.TESSERACT_DIR:
        tess_candidates.append(config.TESSERACT_DIR)
    tess_candidates += [
        r"C:\Program Files\Tesseract-OCR",
        r"C:\Program Files (x86)\Tesseract-OCR",
    ]
    _prepend_to_path_if_has(tess_candidates, "tesseract.exe")

    # 3) Ghostscript: do thu muc bin (gswin64c.exe)
    gs_candidates = []
    if config.GHOSTSCRIPT_DIR:
        gs_candidates.append(config.GHOSTSCRIPT_DIR)
    gs_candidates += glob.glob(r"C:\Program Files\gs\gs*\bin")
    gs_candidates += glob.glob(r"C:\Program Files (x86)\gs\gs*\bin")
    _prepend_to_path_if_has(gs_candidates, "gswin64c.exe", "gswin32c.exe", "gs.exe")


def _prepend_to_path_if_has(dirs: list[str], *exe_names: str) -> None:
    """Neu tim thay 1 trong cac exe trong dir -> them dir vao dau PATH."""
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        if any(os.path.isfile(os.path.join(d, name)) for name in exe_names):
            if d not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            return


def ocr_available() -> tuple[bool, str]:
    """Kiem tra tesseract & ghostscript da san sang chua. Tra ve (ok, thong_bao)."""
    missing = []
    if not shutil.which("tesseract"):
        missing.append("tesseract")
    if not (shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")):
        missing.append("ghostscript")
    if missing:
        return False, "Thieu: " + ", ".join(missing)
    return True, "OK"


# Thiet lap moi truong ngay khi import
setup_ocr_env()


def pdf_has_text(path: str, min_chars: int = 20) -> bool:
    """
    True neu PDF co lop text (doc ra duoc chu) -> day thang, khong can OCR.
    False neu gan nhu rong -> la PDF scan, can OCR.
    Neu khong doc duoc (loi) -> tra True de day nguyen ban (an toan, khong chan file).
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        log.warning("Chua cai pypdf, bo qua buoc kiem tra text. (pip install pypdf)")
        return True

    try:
        reader = PdfReader(path)
        total = 0
        for page in reader.pages:
            total += len((page.extract_text() or "").strip())
            if total >= min_chars:
                return True
        return total >= min_chars
    except Exception as e:
        log.warning("Khong doc duoc text tu %s (%s) -> day nguyen ban", path, e)
        return True


def ocr_pdf(input_path: str, languages: str = "vie+eng") -> str:
    """
    Chay OCR tao ban PDF moi co lop text. Tra ve duong dan file PDF tam (caller phai xoa).
    Nem Exception neu ocrmypdf chua cai hoac OCR loi.
    """
    import ocrmypdf  # lazy import: chi can khi gap PDF scan

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ocr.pdf")
    tmp.close()
    out_path = tmp.name

    # force_ocr=True: ep OCR ngay ca khi co lan text rac;
    # deskew=True: chinh thang trang bi scan nghieng.
    ocrmypdf.ocr(
        input_path,
        out_path,
        language=languages,
        force_ocr=True,
        deskew=True,
        progress_bar=False,
    )
    return out_path
