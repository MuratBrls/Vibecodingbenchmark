# -*- coding: utf-8 -*-
"""
VibeBench Logging & Final Report Module
Tüm süreci logs/ altına kaydeder ve final raporu üretir.
"""

import json
import os
import time
import logging

from config import LOGS_DIR

logger = logging.getLogger("vibebench.logger")


def setup_logging() -> str:
    """
    Logging altyapısını kurar. Log dosyası yolunu döndürür.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"vibebench_{timestamp}.log")

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Dosya handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)-25s │ %(message)s",
        datefmt="%H:%M:%S"
    ))
    root.addHandler(fh)

    # Console handler (sadece WARNING+)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(ch)

    logger.info("VibeBench logging başlatıldı — %s", log_file)
    return log_file


def save_final_report(scores: dict, prompt_text: str, log_file: str) -> str:
    """
    Final raporu JSON olarak kaydeder.

    Returns:
        Rapor dosyası yolu
    """
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(LOGS_DIR, f"report_{timestamp}.json")

        report = {
            "timestamp": timestamp,
            "prompt": prompt_text[:500],
            "log_file": log_file,
            "results": {},
        }

        for tool_name, data in scores.items():
            report["results"][tool_name] = {
                "rank": data["rank"],
                "total_score": data["total_score"],
                "speed_score": data["speed_score"],
                "lines_score": data["lines_score"],
                "validation_score": data["validation_score"],
                "execution_time": data["execution_time"],
                "line_count": data["line_count"],
                "file_size_bytes": data["file_size_bytes"],
                "status": data["status"],
            }

        # Kazanan
        winner = min(scores, key=lambda k: scores[k]["rank"]) if scores else None
        report["winner"] = winner

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("Final rapor kaydedildi: %s", report_file)
        return report_file

    except Exception as e:
        logger.error("Rapor kaydetme hatası: %s", e)
        return ""
