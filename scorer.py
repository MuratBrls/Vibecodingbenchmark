# -*- coding: utf-8 -*-
"""
VibeBench Scoring Engine v1.1
Hız + Mimari Kalite + Kütüphane Kullanımı + Validasyon puanlaması.
"""

import logging

from config import TARGETS
from validator import validate_tool, count_lines, get_total_file_size, analyze_tool_design

logger = logging.getLogger("vibebench.scorer")

# ─── AĞIRLIKLAR ──────────────────────────────────────────────────
WEIGHT_SPEED       = 0.35   # Hız
WEIGHT_VALIDATION  = 0.25   # Syntax/runtime doğruluğu
WEIGHT_ARCH        = 0.25   # Mimari kalite (OOP > Functional > Scripting)
WEIGHT_LIBRARIES   = 0.15   # Kütüphane kullanımı zenginliği


def _speed_score(exec_time, all_times) -> float:
    if exec_time is None:
        return 0.0
    valid = [t for t in all_times if t is not None]
    if not valid:
        return 0.0
    fastest, slowest = min(valid), max(valid)
    if fastest == slowest:
        return 100.0
    return max(0.0, round(100.0 - ((exec_time - fastest) / (slowest - fastest)) * 90.0, 1))


def _validation_score(tool_name: str) -> float:
    try:
        results = validate_tool(tool_name)
        if not results:
            return 0.0
        ok = sum(1 for r in results if r["syntax_ok"] and r["runtime_ok"])
        return round((ok / len(results)) * 100.0, 1)
    except Exception as e:
        logger.error("%s: validasyon skoru hatası — %s", tool_name, e)
        return 0.0


def _architecture_score(design: dict) -> float:
    """Mimari kalite puanı (0-100)."""
    arch = design.get("architecture", "Scripting")
    base = {"OOP": 80, "Functional": 60, "Scripting": 30, "N/A": 0}.get(arch, 0)

    # Bonus: fonksiyon sayısı (iyi yapılandırılmış kod)
    funcs = design.get("total_functions", 0)
    func_bonus = min(funcs * 3, 15)

    # Bonus: sınıf sayısı
    classes = design.get("total_classes", 0)
    class_bonus = min(classes * 5, 10)

    # Ceza: aşırı döngü derinliği
    depth = design.get("max_loop_depth", 0)
    depth_penalty = max(0, (depth - 3) * 5)

    return min(100.0, round(base + func_bonus + class_bonus - depth_penalty, 1))


def _library_score(design: dict) -> float:
    """Kütüphane kullanım zenginliği puanı (0-100)."""
    imports = design.get("all_imports", [])
    # Standart lib hariç harici kütüphaneler daha değerli
    count = len(imports)
    if count == 0:
        return 10.0
    return min(100.0, round(count * 12, 1))


def calculate_scores(watcher_results: dict) -> dict:
    """
    Tüm araçlar için nihai skorları hesaplar.

    Returns:
        {tool_name: {
            speed_score, validation_score, arch_score, library_score, total_score,
            rank, execution_time, line_count, file_size_bytes, status,
            design: {architecture, all_imports, total_functions, ...}
        }}
    """
    all_times = []
    raw = {}

    for tool_name, result in watcher_results.items():
        exec_time = result.get("execution_time")
        target_dir = TARGETS.get(tool_name, "")
        lines = count_lines(target_dir)
        size = get_total_file_size(target_dir)
        design = analyze_tool_design(tool_name)

        all_times.append(exec_time)
        raw[tool_name] = {
            "execution_time": exec_time,
            "line_count": lines,
            "file_size_bytes": size,
            "status": result.get("status", "unknown"),
            "design": design,
        }

    scores = {}
    for tool_name, data in raw.items():
        spd = _speed_score(data["execution_time"], all_times)
        val = _validation_score(tool_name)
        arch = _architecture_score(data["design"])
        lib = _library_score(data["design"])

        total = round(
            spd  * WEIGHT_SPEED +
            val  * WEIGHT_VALIDATION +
            arch * WEIGHT_ARCH +
            lib  * WEIGHT_LIBRARIES,
            1,
        )

        scores[tool_name] = {
            **data,
            "speed_score": spd,
            "validation_score": val,
            "arch_score": arch,
            "library_score": lib,
            "total_score": total,
            "rank": 0,
        }

    ranked = sorted(scores.keys(), key=lambda k: scores[k]["total_score"], reverse=True)
    for i, name in enumerate(ranked, 1):
        scores[name]["rank"] = i

    return scores


def get_winner(scores: dict):
    if not scores:
        return None, None
    winner = min(scores, key=lambda k: scores[k]["rank"])
    return winner, scores[winner]
