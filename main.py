"""
main.py - Diem chay chinh.

Cach dung:
    python main.py            # chay vong lap, tu quet moi SCAN_INTERVAL giay (Ctrl+C de dung)
    python main.py --once     # quet dung 1 lan roi thoat (dung cho Windows Task Scheduler)
"""
import sys
import time
import logging

from config import config
from database import Database
from dify_client import DifyClient
from scanner import Scanner


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("backend_auto.log", encoding="utf-8"),
        ],
    )


def build_scanner() -> Scanner:
    db = Database(config.DB_PATH)
    client = DifyClient(
        base_url=config.DIFY_BASE_URL,
        api_key=config.DIFY_API_KEY,
        dataset_id=config.DATASET_ID,
        indexing_technique=config.INDEXING_TECHNIQUE,
    )
    return Scanner(db, client)


def main() -> None:
    setup_logging()
    config.validate()
    log = logging.getLogger("main")

    once = "--once" in sys.argv
    scanner = build_scanner()

    log.info("=== Dify Backend Auto ===")
    log.info("Thu muc theo doi : %s", config.WATCH_FOLDER)
    log.info("Dataset ID       : %s", config.DATASET_ID)
    log.info("Che do           : %s", "QUET 1 LAN" if once else f"VONG LAP moi {config.SCAN_INTERVAL}s")

    if once:
        scanner.scan_once()
        log.info("Tong ket DB: %s", scanner.db.stats())
        return

    try:
        while True:
            scanner.scan_once()
            log.info("Tong ket DB: %s", scanner.db.stats())
            log.info("Ngu %d giay truoc lan quet tiep theo...", config.SCAN_INTERVAL)
            time.sleep(config.SCAN_INTERVAL)
    except KeyboardInterrupt:
        log.info("Da dung boi nguoi dung (Ctrl+C).")


if __name__ == "__main__":
    main()
