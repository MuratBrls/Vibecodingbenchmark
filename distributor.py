# -*- coding: utf-8 -*-
"""
VibeBench Broadcast Module
Prompt metnini tüm hedef klasörlere task_input.txt olarak eşzamanlı dağıtır.
"""

import json
import os
import time
import glob
import logging

from config import TARGETS, TASK_INPUT_FILE, STATUS_FILE, WATCHED_EXTENSIONS

logger = logging.getLogger("vibebench.distributor")


def _clean_source_files(target_dir: str) -> int:
    """Hedef klasördeki eski kaynak kod dosyalarını siler."""
    removed = 0
    try:
        for ext in WATCHED_EXTENSIONS:
            for f in glob.glob(os.path.join(target_dir, f"*{ext}")):
                os.remove(f)
                removed += 1
    except OSError as e:
        logger.warning("Temizleme hatası (%s): %s", target_dir, e)
    return removed


def distribute_prompt(prompt_text: str, clean: bool = True) -> dict:
    """
    Prompt metnini tüm hedef klasörlere dağıtır.

    Returns:
        {tool_name: {"success": bool, "start_time": float, "error": str|None}}
    """
    results = {}
    start_time = time.time()

    for tool_name, target_dir in TARGETS.items():
        entry = {"success": False, "start_time": start_time, "error": None}
        try:
            os.makedirs(target_dir, exist_ok=True)

            if clean:
                cleaned = _clean_source_files(target_dir)
                if cleaned:
                    logger.info("%s: %d eski dosya silindi", tool_name, cleaned)

            # task_input.txt yaz
            with open(os.path.join(target_dir, TASK_INPUT_FILE), "w", encoding="utf-8") as f:
                f.write(prompt_text)

            # status.json yaz
            status_data = {
                "status": "pending",
                "start_time": start_time,
                "end_time": None,
                "execution_time": None,
                "tool": tool_name,
            }
            with open(os.path.join(target_dir, STATUS_FILE), "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)

            entry["success"] = True
            logger.info("%s: task_input.txt dağıtıldı", tool_name)

        except Exception as e:
            entry["error"] = str(e)
            logger.error("%s: dağıtım hatası — %s", tool_name, e)

        results[tool_name] = entry

    return results
