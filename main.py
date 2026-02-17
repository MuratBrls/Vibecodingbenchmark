# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Main CLI v2.0
Signal Trigger + Telemetri + Derin Analiz ile modülleri orkestre eder.
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

from config import WATCH_TIMEOUT, TARGETS, STATUS_FILE, LOGS_DIR, START_SIGNAL_FILE, VERSION, APP_NAME
from distributor import distribute_prompt
from watcher import BenchmarkWatcher
from scorer import calculate_scores, get_winner
from bench_logger import setup_logging, save_final_report
from pre_check import run_pre_checks
from html_report import generate_html_report
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
    """Benchmark: pre-check → dağıt → izle (signal trigger + telemetri) → skorla → raporla."""

    prompt_text = args.prompt
    no_clean    = args.no_clean
    timeout     = args.timeout

    # ── 0. LOGGING ──────────────────────────────────────────────
    log_file = setup_logging()
    print_banner()
    logger.info("%s v%s başlatıldı — prompt: %s", APP_NAME, VERSION, prompt_text[:100])

    # ── 0.1 KULLANICI REHBERİ ──────────────────────────────────
    console.print(Panel(
        "[bold bright_yellow]🎯 HOŞ GELDİN![/]\n\n"
        "Black Box Deep Analytics v2.1 — Total Performance sistemi AI araçlarını izlemeye hazır.\n"
        "Hem düşünme (thinking) hem yazma (writing) süreleri ayrı ayrı ölçülür.\n\n"
        "[bold bright_cyan]📋 AI'LARA VERİLECEK KOMUT:[/]\n"
        "[dim]═══════════════════════════════════════════════════════════════════[/]\n"
        '[bright_white]"Önce \'start_signal.json\' oluştur, sonra OOP yapısında\n'
        '\'calculator.py\' yaz, bitince \'start_signal.json\' dosyasını sil.\n'
        'Hızlı ol, telemetri seni izliyor!"[/]\n'
        "[dim]═══════════════════════════════════════════════════════════════════[/]\n\n"
        "[bold bright_green]✅ PROTOKOL ADIMLARI:[/]\n"
        "  [bright_cyan]1.[/] [bold]start_signal.json[/] oluştur → 🧠 düşünme süresi biter, ✍️ yazma başlar\n"
        "  [bright_cyan]2.[/] Kodu yaz ve kaydet → ✍️ yazma süresi durur\n"
        "  [bright_cyan]3.[/] [bold]start_signal.json[/] sil → ✅ protokol tamamlandı\n\n"
        "[bold bright_magenta]📊 PUANLAMA SİSTEMİ (v2.1):[/]\n"
        "  • ⏱️  30% Toplam Hız (🧠 Düşünme + ✍️ Yazma)\n"
        "  • 🏛️  30% Mimari & Temiz Kod (McCabe + PEP8 + Güvenlik)\n"
        "  • ❌ 25% Hata/Deneme Oranı (her hata -10% ceza)\n"
        "  • 💎 15% Kütüphane Verimliliği\n\n"
        f"[bold bright_blue]📁 RAPORLAR:[/] [dim]{LOGS_DIR}/[/]\n"
        "  • JSON: report_YYYYMMDD_HHMMSS.json\n"
        "  • HTML: report_YYYYMMDD_HHMMSS.html (tarayıcıda açılabilir)\n\n"
        "[dim italic]💡 İpucu: Düşünme süresi komut dağıtıldığı andan signal dosyasına kadar,\n"
        "   yazma süresi signal dosyasından kod dosyasına kadar ölçülür.[/]",
        title=f"[bold]⚡ {APP_NAME} v{VERSION} — Total Performance Rehberi[/]",
        border_style="bright_green",
        padding=(1, 2),
    ))
    console.print()


    # ── 0.5 PRE-CHECK ──────────────────────────────────────────
    console.print(Panel(
        "🔍 Hedef klasör izinleri denetleniyor...",
        title="[bold]0 · Ön Kontrol[/]",
        border_style="bright_blue",
    ))

    check_result = run_pre_checks()
    for tool_name, info in check_result["results"].items():
        if info["ok"]:
            console.print(f"  ✅ [bright_green]{tool_name}[/] — yazma izni OK")
        else:
            console.print(f"  ❌ [bright_red]{tool_name}[/] — {info['error']}")

    if not check_result["all_ok"]:
        console.print("\n[bright_red]⛔ Klasör izin hatası! Lütfen izinleri kontrol edin.[/]")
        sys.exit(1)
    console.print()

    # ── 1. DAĞITIM ──────────────────────────────────────────────
    console.print(Panel(
        f"📝 Prompt: [bright_white]{prompt_text[:120]}{'...' if len(prompt_text) > 120 else ''}[/]",
        title="[bold]1 · Prompt Dağıtımı[/]",
        border_style="bright_green",
    ))

    dist_results = distribute_prompt(prompt_text, clean=not no_clean)

    if not dist_results:
        console.print("[bright_red]⛔ Hedef bulunamadı![/]")
        sys.exit(1)

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

    # ── 2. SIGNAL TRIGGER + TELEMETRİ BİLGİ ────────────────────
    console.print(Panel(
        "👁️  Dosya izleme + telemetri başlatılıyor...\n\n"
        "   📋 [bold]AI Görev Protokolü (Total Performance):[/]\n"
        f"   [bright_cyan]1.[/] Klasöre [bold]{START_SIGNAL_FILE}[/] oluştur → 🧠 düşünme biter, ✍️ yazma başlar\n"
        "   [bright_cyan]2.[/] Kodu yaz ve klasöre kaydet → ✍️ yazma durur\n"
        f"   [bright_cyan]3.[/] İşlem bittikten sonra [bold]{START_SIGNAL_FILE}[/] sil\n\n"
        f"   ⏰ Timeout: {timeout}sn\n"
        "   📊 Puanlama: 🧠+✍️ = ⏱️ Toplam Hız 30% + Mimari 30% + Hata 25% + Kütüphane 15%\n"
        "   🔬 Derin Analiz: McCabe + PEP8 + Güvenlik Taraması",
        title="[bold]2 · Total Performance İzleme (Thinking + Writing)[/]",
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
        "   • McCabe karmaşıklığı & PEP8 uyumu\n"
        "   • Güvenlik taraması (eval/exec)\n"
        "   • Kütüphane verimliliği\n"
        "   • Hata/Deneme oranı analizi",
        title="[bold]3 · Derin Analiz & Skorlama[/]",
        border_style="bright_cyan",
    ))

    watcher_results = watcher.get_results()
    telemetry_data = watcher.get_telemetry_data()
    scores = calculate_scores(watcher_results, telemetry_data)

    # ── 6. RAPOR ────────────────────────────────────────────────
    report_path = save_final_report(scores, prompt_text, log_file)

    # HTML Rapor
    html_path = generate_html_report(scores, prompt_text, telemetry_data)

    winner_name, winner_data = get_winner(scores)
    if winner_name:
        logger.info("🏆 KAZANAN: %s (skor: %.1f, net süre: %s)",
                     winner_name, winner_data["total_score"],
                     f"{winner_data['execution_time']:.3f}s" if winner_data["execution_time"] else "N/A")

    # ── 7. FİNAL ───────────────────────────────────────────────
    print_final(scores, report_path, html_path)


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
                t_str = f"{net:.3f}sn" if net is not None else "—"
                files = ", ".join(data.get("detected_files", [])) or "—"

                # Telemetri verileri
                tele = data.get("telemetry", {})
                tele_str = ""
                if tele:
                    tele_str = f" | Deneme: {tele.get('retries', 0)} | Hata: {tele.get('errors', 0)}"

                console.print(f"  🔧 [bold]{tool_name}[/]: {status} | Net süre: {t_str} | Dosyalar: {files}{tele_str}")
            except Exception as e:
                logger.debug("Status dosyası okuma hatası: %s", e, exc_info=True)
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

        html_reports = sorted(
            [f for f in os.listdir(LOGS_DIR) if f.startswith("report_") and f.endswith(".html")],
            reverse=True,
        )
        if html_reports:
            console.print(f"  🌐 Son HTML: [dim]{os.path.join(LOGS_DIR, html_reports[0])}[/]")
            console.print()


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="vibebench",
        description=f"⚡ {APP_NAME} — Multi-AI Coding Benchmark Tool v{VERSION}",
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
