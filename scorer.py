# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Scoring Engine v2.2 (Lokal On-Premise)
Hız (thinking + writing) + Mimari & Temiz Kod + Hata/Deneme + Kütüphane puanlaması.
Her hata/retry toplam skordan %10 ceza.
Kaynak kullanımı (CPU/RAM) veri akışı dahil.
"""

import logging

from config import TARGETS
from validator import validate_tool, count_lines, get_total_file_size, analyze_tool_design
from validator_pro import analyze_pro

logger = logging.getLogger("vibebench.scorer")

# ─── AĞIRLIKLAR v2.1 ────────────────────────────────────────────
WEIGHT_SPEED       = 0.30   # ⏱️ Toplam Hız (thinking + writing)
WEIGHT_ARCH        = 0.30   # 🏛️ Mimari & Temiz Kod
WEIGHT_ERROR_RATIO = 0.25   # ❌ Hata/Deneme Oranı
WEIGHT_LIBRARIES   = 0.15   # 💎 Kütüphane Verimliliği

# v2.1: Her hata/retry için toplam skordan %10 ceza
ERROR_PENALTY_PER_ATTEMPT = 10.0


def _speed_score(total_time, all_times) -> float:
    """Hız puanı — total_time (thinking + writing) üzerinden hesaplanır."""
    if total_time is None:
        return 0.0
    valid = [t for t in all_times if t is not None]
    if not valid:
        return 0.0
    fastest, slowest = min(valid), max(valid)
    if fastest == slowest:
        return 100.0
    return max(0.0, round(100.0 - ((total_time - fastest) / (slowest - fastest)) * 90.0, 1))


def _architecture_score(design: dict, pro_analysis: dict) -> float:
    """Mimari + Temiz Kod birleşik puanı (0-100)."""
    arch = design.get("architecture", "Scripting")
    base = {"OOP": 80, "Functional": 60, "Scripting": 30, "N/A": 0}.get(arch, 0)

    # Bonus: fonksiyon sayısı
    funcs = design.get("total_functions", 0)
    func_bonus = min(funcs * 3, 15)

    # Bonus: sınıf sayısı
    classes = design.get("total_classes", 0)
    class_bonus = min(classes * 5, 10)

    # Ceza: aşırı döngü derinliği
    depth = design.get("max_loop_depth", 0)
    depth_penalty = max(0, (depth - 3) * 5)

    # Mimari taban puanı
    arch_base = min(100.0, base + func_bonus + class_bonus - depth_penalty)

    # Temiz Kod puanı (validator_pro'dan)
    clean_code = pro_analysis.get("clean_code_score", 50.0)

    # %60 mimari + %40 temiz kod
    return min(100.0, round(arch_base * 0.6 + clean_code * 0.4, 1))


def _error_ratio_score(telemetry: dict) -> float:
    """
    Hata/Deneme oranı puanı (0-100).

    v2.1: Her failed_attempt (retry + error) için %10 puan kır.
    - 0 hata, 0 retry → 100 puan
    - Her retry/error -10 puan
    - Minimum 0
    """
    if not telemetry:
        return 50.0  # Telemetri yok → nötr

    retries = telemetry.get("retries", 0)
    errors = telemetry.get("errors", 0)

    total_fails = retries + errors
    score = 100.0 - (total_fails * ERROR_PENALTY_PER_ATTEMPT)

    return max(0.0, round(score, 1))


def _library_score(design: dict) -> float:
    """Kütüphane kullanım zenginliği puanı (0-100)."""
    imports = design.get("all_imports", [])
    count = len(imports)
    if count == 0:
        return 10.0
    return min(100.0, round(count * 12, 1))


def calculate_scores(watcher_results: dict, telemetry_data: dict = None) -> dict:
    """
    Tüm araçlar için nihai skorları hesaplar.

    Args:
        watcher_results: Watcher sonuçları
        telemetry_data: {tool_name: telemetry_summary} (opsiyonel)

    Returns:
        {tool_name: {
            speed_score, arch_score, error_ratio_score, library_score, total_score,
            rank, execution_time, thinking_time, writing_time, total_time,
            line_count, file_size_bytes, status,
            design, pro_analysis, telemetry
        }}
    """
    if telemetry_data is None:
        telemetry_data = {}

    all_total_times = []
    raw = {}

    for tool_name, result in watcher_results.items():
        thinking = result.get("thinking_time")
        writing = result.get("writing_time")
        total_time = result.get("total_time")

        target_dir = TARGETS.get(tool_name, "")
        lines = count_lines(target_dir)
        size = get_total_file_size(target_dir)
        design = analyze_tool_design(tool_name)
        pro = analyze_pro(tool_name)

        all_total_times.append(total_time)
        tele = telemetry_data.get(tool_name, {})
        raw[tool_name] = {
            "execution_time": writing,  # geriye uyumluluk
            "thinking_time": thinking,
            "writing_time": writing,
            "total_time": total_time,
            "line_count": lines,
            "file_size_bytes": size,
            "status": result.get("status", "unknown"),
            "design": design,
            "pro_analysis": pro,
            "telemetry": tele,
            # Kaynak kullanımı (psutil)
            "avg_cpu": tele.get("avg_cpu", 0.0),
            "peak_cpu": tele.get("peak_cpu", 0.0),
            "avg_ram_mb": tele.get("avg_ram_mb", 0.0),
            "peak_ram_mb": tele.get("peak_ram_mb", 0.0),
        }

    scores = {}
    for tool_name, data in raw.items():
        # v2.1: Hız skoru total_time üzerinden
        spd = _speed_score(data["total_time"], all_total_times)
        arch = _architecture_score(data["design"], data["pro_analysis"])
        err = _error_ratio_score(data["telemetry"])
        lib = _library_score(data["design"])

        total = round(
            spd  * WEIGHT_SPEED +
            arch * WEIGHT_ARCH +
            err  * WEIGHT_ERROR_RATIO +
            lib  * WEIGHT_LIBRARIES,
            1,
        )

        scores[tool_name] = {
            **data,
            "speed_score": spd,
            "arch_score": arch,
            "error_ratio_score": err,
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
