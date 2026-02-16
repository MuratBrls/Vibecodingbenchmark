# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Pre-Check Module v2.0
Benchmark başlamadan önce hedef klasörlerin yazma izinlerini denetler.
"""

import os
import tempfile
import logging

from config import TARGETS

logger = logging.getLogger("vibebench.precheck")


def _check_write_permission(target_dir: str) -> tuple:
    """
    Klasöre yazma izni olup olmadığını test eder.

    Returns:
        (success: bool, error_message: str | None)
    """
    try:
        # Klasörü oluştur (yoksa)
        os.makedirs(target_dir, exist_ok=True)

        # Geçici dosya oluştur ve sil
        test_file = os.path.join(target_dir, ".vibebench_write_test")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("write_permission_test")
        os.remove(test_file)

        return True, None

    except PermissionError:
        return False, f"Yazma izni yok: {target_dir}"
    except OSError as e:
        return False, f"Dosya sistemi hatası: {e}"
    except Exception as e:
        return False, f"Beklenmeyen hata: {e}"


def run_pre_checks() -> dict:
    """
    Tüm hedef klasörler için ön kontrolleri çalıştırır.

    Returns:
        {
            "all_ok": bool,
            "results": {tool_name: {"ok": bool, "path": str, "error": str|None}}
        }
    """
    results = {}
    all_ok = True

    for tool_name, target_dir in TARGETS.items():
        ok, error = _check_write_permission(target_dir)
        results[tool_name] = {
            "ok": ok,
            "path": target_dir,
            "error": error,
        }
        if ok:
            logger.info("✅ %s: yazma izni OK — %s", tool_name, target_dir)
        else:
            logger.error("❌ %s: %s", tool_name, error)
            all_ok = False

    return {
        "all_ok": all_ok,
        "results": results,
    }
