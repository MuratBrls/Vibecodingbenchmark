# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Logging & Final Report Module v2.0
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
            "version": "2.0",
            "prompt": prompt_text[:500],
            "log_file": log_file,
            "weights": {
                "speed": 0.30,
                "architecture": 0.30,
                "error_ratio": 0.25,
                "libraries": 0.15,
            },
            "results": {},
        }

        for tool_name, data in scores.items():
            tele = data.get("telemetry", {})
            pro = data.get("pro_analysis", {})
            report["results"][tool_name] = {
                "rank": data["rank"],
                "total_score": data["total_score"],
                "speed_score": data["speed_score"],
                "arch_score": data["arch_score"],
                "error_ratio_score": data["error_ratio_score"],
                "library_score": data["library_score"],
                "execution_time": data["execution_time"],
                "line_count": data["line_count"],
                "file_size_bytes": data["file_size_bytes"],
                "status": data["status"],
                "telemetry": {
                    "saves": tele.get("saves", 0),
                    "retries": tele.get("retries", 0),
                    "errors": tele.get("errors", 0),
                },
                "pro_analysis": {
                    "mccabe_avg": pro.get("mccabe_avg", 0),
                    "pep8_compliance": pro.get("pep8_compliance", 0),
                    "security_count": pro.get("security_count", 0),
                    "clean_code_score": pro.get("clean_code_score", 0),
                },
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
