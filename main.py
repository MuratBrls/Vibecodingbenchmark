# -*- coding: utf-8 -*-
"""
dfdfdfdf
VibeBench — Main CLI v1.1
Signal Trigger protokolü ile modülleri orkestre eder.
"""

import argparse
import json
import os
import sys
import time
import logging

from rich.panel import Panel
from rich.text import Text
from rich.live import Live

from config import WATCH_TIMEOUT, TARGETS, STATUS_FILE, LOGS_DIR, START_SIGNAL_FILE
from distributor import distribute_prompt
from watcher import BenchmarkWatcher
from scorer import calculate_scores, get_winner
from bench_logger import setup_logging, save_final_report
from dashboard import (
    build_live_table,
    print_final,
    print_banner,
    console,
)

logger = logging.getLogger("vibebench.main")


# ═══════════════════════════════════════════════════════════════════
#  RUN KOMUTU
# ═══════════════════════════════════════════════════════════════════

def cmd_run(args):
    """Benchmark: dağıt → izle (signal trigger) → skorla → raporla."""

    prompt_text = args.prompt
    no_clean    = args.no_clean
    timeout     = args.timeout

    # ── 0. LOGGING ──────────────────────────────────────────────
    log_file = setup_logging()
    print_banner()
    logger.info("Benchmark v1.1 başlatıldı — prompt: %s", prompt_text[:100])

    # ── 1. DAĞITIM ──────────────────────────────────────────────
    console.print(Panel(
        f"📝 Prompt: [bright_white]{prompt_text[:120]}{'...' if len(prompt_text) > 120 else ''}[/]",
        title="[bold]1 · Prompt Dağıtımı[/]",
        border_style="bright_green",
    ))

    dist_results = distribute_prompt(prompt_text, clean=not no_clean)
    start_time = list(dist_results.values())[0]["start_time"]

    all_ok = True
    for tool, info in dist_results.items():
        if info["success"]:
            console.print(f"  ✅ [bright_green]{tool}[/] — task_input.txt dağıtıldı")
        else:
            console.print(f"  ❌ [bright_red]{tool}[/] — HATA: {info['error']}")
            all_ok = False

    if not all_ok:
        console.print("\n[bright_red]⛔ Dağıtım hatası! İşlem durduruluyor.[/]")
        sys.exit(1)

    console.print()

    # ── 2. SIGNAL TRIGGER BİLGİ ────────────────────────────────
    console.print(Panel(
        "👁️  Dosya izleme başlatılıyor...\n\n"
        "   📋 [bold]AI Görev Protokolü:[/]\n"
        f"   [bright_cyan]1.[/] Klasöre [bold]{START_SIGNAL_FILE}[/] oluştur → kronometre başlar\n"
        "   [bright_cyan]2.[/] Kodu yaz ve klasöre kaydet → kronometre durur\n"
        f"   [bright_cyan]3.[/] İşlem bittikten sonra [bold]{START_SIGNAL_FILE}[/] sil\n\n"
        f"   ⏰ Timeout: {timeout}sn\n"
        "   📊 Puanlama: 35% Hız + 25% Validasyon + 25% Mimari + 15% Kütüphane",
        title="[bold]2 · Signal Trigger İzleme[/]",
        border_style="bright_yellow",
    ))
    console.print()

    # ── 3. WATCHER ──────────────────────────────────────────────
    watcher = BenchmarkWatcher(start_time=start_time)
    watcher.start()

    # ── 4. CANLI DASHBOARD ──────────────────────────────────────
    try:
        with Live(
            build_live_table(watcher.handlers, start_time),
            refresh_per_second=2,
            console=console,
        ) as live:
            deadline = start_time + timeout
            while time.time() < deadline:
                live.update(build_live_table(watcher.handlers, start_time))
                if all(h.completed for h in watcher.handlers.values()):
                    live.update(build_live_table(watcher.handlers, start_time))
                    break
                time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[bright_yellow]⚠️  İzleme durduruldu (Ctrl+C).[/]\n")
        logger.warning("İzleme kullanıcı tarafından durduruldu")
    finally:
        watcher.stop()

    # ── 5. SKORLAMA ─────────────────────────────────────────────
    console.print(Panel(
        "🧮 Skorlar hesaplanıyor...\n"
        "   • Syntax & Runtime doğrulaması\n"
        "   • Mimari analizi (OOP / Functional / Scripting)\n"
        "   • Kütüphane taraması\n"
        "   • Karmaşıklık değerlendirmesi",
        title="[bold]3 · Derin Analiz & Skorlama[/]",
        border_style="bright_cyan",
    ))

    watcher_results = watcher.get_results()
    scores = calculate_scores(watcher_results)

    # ── 6. RAPOR ────────────────────────────────────────────────
    report_path = save_final_report(scores, prompt_text, log_file)

    winner_name, winner_data = get_winner(scores)
    if winner_name:
        logger.info("🏆 KAZANAN: %s (skor: %.1f, net süre: %s)",
                     winner_name, winner_data["total_score"],
                     f"{winner_data['execution_time']:.3f}s" if winner_data["execution_time"] else "N/A")

    # ── 7. FİNAL ───────────────────────────────────────────────
    print_final(scores, report_path)


# ═══════════════════════════════════════════════════════════════════
#  STATUS KOMUTU
# ═══════════════════════════════════════════════════════════════════

def cmd_status(args):
    print_banner()
    console.print(Panel("📊 Mevcut Durum", border_style="bright_cyan"))
    console.print()

    for tool_name, target_dir in TARGETS.items():
        status_path = os.path.join(target_dir, STATUS_FILE)
        if os.path.isfile(status_path):
            try:
                with open(status_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                status = data.get("status", "unknown")
                net = data.get("net_execution_time") or data.get("execution_time")
                t_str = f"{net:.3f}sn" if net else "—"
                files = ", ".join(data.get("detected_files", [])) or "—"
                console.print(f"  🔧 [bold]{tool_name}[/]: {status} | Net süre: {t_str} | Dosyalar: {files}")
            except Exception as e:
                console.print(f"  🔧 [bold]{tool_name}[/]: [red]Okuma hatası: {e}[/]")
        else:
            console.print(f"  🔧 [bold]{tool_name}[/]: [dim]Henüz veri yok[/]")
    console.print()

    if os.path.isdir(LOGS_DIR):
        reports = sorted(
            [f for f in os.listdir(LOGS_DIR) if f.startswith("report_") and f.endswith(".json")],
            reverse=True,
        )
        if reports:
            console.print(f"  📄 Son rapor: [dim]{os.path.join(LOGS_DIR, reports[0])}[/]")
            console.print()


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="vibebench",
        description="⚡ VibeBench — Multi-AI Coding Benchmark Tool v1.1 (Signal Trigger)",
    )
    sub = parser.add_subparsers(dest="command", help="Komutlar")

    p_run = sub.add_parser("run", help="Benchmark başlat")
    p_run.add_argument("prompt", type=str, help="Dağıtılacak prompt metni")
    p_run.add_argument("--no-clean", action="store_true", help="Eski dosyaları silme")
    p_run.add_argument("--timeout", type=int, default=WATCH_TIMEOUT,
                        help=f"Zaman aşımı (varsayılan: {WATCH_TIMEOUT}sn)")
    p_run.set_defaults(func=cmd_run)

    p_st = sub.add_parser("status", help="Mevcut durumu göster")
    p_st.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        console.print(f"\n[bold bright_red]⛔ Kritik hata: {e}[/]")
        logger.exception("Kritik hata")
        sys.exit(1)


if __name__ == "__main__":
    main()
