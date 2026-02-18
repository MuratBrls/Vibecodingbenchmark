# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Main CLI v2.2 (Lokal On-Premise)
Signal Trigger + Telemetri + Derin Analiz + psutil Kaynak Takibi + LocalErrorLogger
ile modülleri orkestre eder. Sıfır gecikme, tam lokal çalışma.
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

from config import (
    WATCH_TIMEOUT, TARGETS, STATUS_FILE, LOGS_DIR, START_SIGNAL_FILE,
    VERSION, APP_NAME, LOCAL_MODE, BASE_DIR, SIGNAL_POLL_INTERVAL_MS,
    RESOURCE_SAMPLE_INTERVAL,
)
from distributor import distribute_prompt
from watcher import BenchmarkWatcher
from scorer import calculate_scores, get_winner
from bench_logger import setup_logging, save_final_report
from pre_check import run_pre_checks
from html_report import generate_html_report
from local_error_logger import LocalErrorLogger
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
    """Benchmark: pre-check → dağıt → izle (signal trigger + telemetri + kaynak) → skorla → raporla."""

    prompt_text = args.prompt
    no_clean    = args.no_clean
    timeout     = args.timeout

    # ── 0. LOGGING ──────────────────────────────────────────────
    log_file = setup_logging()
    print_banner()
    logger.info("%s v%s başlatıldı — LOKAL MOD — prompt: %s", APP_NAME, VERSION, prompt_text[:100])

    # ── 0.1 LOKAL MOD ONAY ──────────────────────────────────────
    console.print(Panel(
        "[bold bright_red]🔥 LOKAL MOTOR ATEŞLENDİ![/]\n\n"
        f"[bold bright_cyan]⚡ {APP_NAME} v{VERSION} — On-Premise Mod Aktif[/]\n"
        f"[dim]Çalışma Dizini: {BASE_DIR}[/]\n\n"
        "[bold bright_yellow]🎯 LOKAL MOD ÖZELLİKLERİ:[/]\n"
        f"  🏠 Tüm yollar sabitlenmiş: [dim]{BASE_DIR}[/]\n"
        f"  ⏱️ Watchdog hassasiyeti: [bold]{SIGNAL_POLL_INTERVAL_MS}ms[/]\n"
        f"  🖥️ psutil kaynak takibi: CPU + RAM (her {RESOURCE_SAMPLE_INTERVAL}sn)\n"
        "  🛡️ LocalErrorLogger: Windows I/O hata koruması aktif\n"
        "  🚀 Sıfır gecikme — tüm işlemler lokalde\n\n"
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
        "[bold bright_magenta]📊 PUANLAMA SİSTEMİ (v2.2):[/]\n"
        "  • ⏱️  30% Toplam Hız (🧠 Düşünme + ✍️ Yazma)\n"
        "  • 🏛️  30% Mimari & Temiz Kod (McCabe + PEP8 + Güvenlik)\n"
        "  • ❌ 25% Hata/Deneme Oranı (her hata -10% ceza)\n"
        "  • 💎 15% Kütüphane Verimliliği\n"
        "  • 🖥️  Kaynak Takibi: CPU% + RAM (MB) — psutil ile lokal ölçüm\n\n"
        f"[bold bright_blue]📁 RAPORLAR:[/] [dim]{LOGS_DIR}/[/]\n"
        "  • JSON: report_YYYYMMDD_HHMMSS.json\n"
        "  • HTML: report_YYYYMMDD_HHMMSS.html (tarayıcıda açılabilir)\n\n"
        "[dim italic]💡 İpucu: Tüm zamanlamalar perf_counter ile ms hassasiyetinde ölçülür.\n"
        "   CPU/RAM kullanımı psutil ile gerçek zamanlı izlenir.[/]",
        title=f"[bold]⚡ {APP_NAME} v{VERSION} — LOKAL ON-PREMISE MOTOR[/]",
        border_style="bright_red",
        padding=(1, 2),
    ))
    console.print()

    # ── 0.4 PRE-FLIGHT CLEANUP ──────────────────────────────────
    # Eski local_errors.json'u temizle
    from config import LOCAL_ERROR_LOG
    if os.path.isfile(LOCAL_ERROR_LOG):
        try:
            os.remove(LOCAL_ERROR_LOG)
            logger.info("Pre-flight: eski %s silindi", LOCAL_ERROR_LOG)
        except OSError as e:
            logger.warning("Pre-flight: %s silinemedi — %s", LOCAL_ERROR_LOG, e)

    # ── 0.5 LOCAL ERROR LOGGER ─────────────────────────────────
    error_logger = LocalErrorLogger()
    error_logger.__enter__()
    logger.info("LocalErrorLogger başlatıldı")

    # ── 0.5 PRE-CHECK ──────────────────────────────────────────
    console.print(Panel(
        "🔍 Hedef klasör izinleri denetleniyor...\n"
        f"  📂 Çalışma dizini: [dim]{BASE_DIR}[/]",
        title="[bold]0 · Ön Kontrol (Lokal)[/]",
        border_style="bright_blue",
    ))

    check_result = run_pre_checks()
    for tool_name, info in check_result["results"].items():
        if info["ok"]:
            console.print(f"  ✅ [bright_green]{tool_name}[/] — yazma izni OK — [dim]{info['path']}[/]")
        else:
            console.print(f"  ❌ [bright_red]{tool_name}[/] — {info['error']}")

    if not check_result["all_ok"]:
        console.print("\n[bright_red]⛔ Klasör izin hatası! Lütfen izinleri kontrol edin.[/]")
        error_logger.__exit__(None, None, None)
        sys.exit(1)
    console.print()

    # ── 1. DAĞITIM ──────────────────────────────────────────────
    console.print(Panel(
        f"📝 Prompt: [bright_white]{prompt_text[:120]}{'...' if len(prompt_text) > 120 else ''}[/]",
        title="[bold]1 · Prompt Dağıtımı (Lokal)[/]",
        border_style="bright_green",
    ))

    dist_results = distribute_prompt(prompt_text, clean=not no_clean)

    if not dist_results:
        console.print("[bright_red]⛔ Hedef bulunamadı![/]")
        error_logger.__exit__(None, None, None)
        sys.exit(1)

    # perf_counter tabanlı başlangıç zamanı
    start_time = time.perf_counter()

    all_ok = True
    for tool, info in dist_results.items():
        if info["success"]:
            console.print(f"  ✅ [bright_green]{tool}[/] — task_input.txt dağıtıldı")
        else:
            console.print(f"  ❌ [bright_red]{tool}[/] — HATA: {info['error']}")
            all_ok = False

    if not all_ok:
        console.print("\n[bright_red]⛔ Dağıtım hatası! İşlem durduruluyor.[/]")
        error_logger.__exit__(None, None, None)
        sys.exit(1)

    console.print()

    # ── 2. SIGNAL TRIGGER + TELEMETRİ + KAYNAK BİLGİ ───────────
    console.print(Panel(
        "👁️  Dosya izleme + telemetri + kaynak takibi başlatılıyor...\n\n"
        "   📋 [bold]AI Görev Protokolü (Lokal On-Premise):[/]\n"
        f"   [bright_cyan]1.[/] Klasöre [bold]{START_SIGNAL_FILE}[/] oluştur → 🧠 düşünme biter, ✍️ yazma başlar\n"
        "   [bright_cyan]2.[/] Kodu yaz ve klasöre kaydet → ✍️ yazma durur\n"
        f"   [bright_cyan]3.[/] İşlem bittikten sonra [bold]{START_SIGNAL_FILE}[/] sil\n\n"
        f"   ⏰ Timeout: {timeout}sn\n"
        f"   ⚡ Watchdog polling: {SIGNAL_POLL_INTERVAL_MS}ms hassasiyetinde\n"
        f"   🖥️ Kaynak takibi: CPU + RAM (her {RESOURCE_SAMPLE_INTERVAL}sn)\n"
        "   📊 Puanlama: 🧠+✍️ = ⏱️ Toplam Hız 30% + Mimari 30% + Hata 25% + Kütüphane 15%\n"
        "   🔬 Derin Analiz: McCabe + PEP8 + Güvenlik Taraması",
        title="[bold]2 · Total Performance İzleme (Lokal — Sıfır Gecikme)[/]",
        border_style="bright_yellow",
    ))
    console.print()

    # ── 3. WATCHER ──────────────────────────────────────────────
    watcher = BenchmarkWatcher(start_time=start_time, error_logger=error_logger)
    watcher.start()

    # ── 4. CANLI DASHBOARD ──────────────────────────────────────
    try:
        with Live(
            build_live_table(watcher.handlers, start_time),
            refresh_per_second=2,
            console=console,
        ) as live:
            deadline = start_time + timeout
            while time.perf_counter() < deadline:
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
        "   • Hata/Deneme oranı analizi\n"
        "   • 🖥️ CPU & 🧮 RAM kaynak analizi (psutil)",
        title="[bold]3 · Derin Analiz & Skorlama (Lokal)[/]",
        border_style="bright_cyan",
    ))

    watcher_results = watcher.get_results()
    telemetry_data = watcher.get_telemetry_data()
    scores = calculate_scores(watcher_results, telemetry_data)

    # ── 6. RAPOR ────────────────────────────────────────────────
    local_err_summary = error_logger.get_summary()
    report_path = save_final_report(scores, prompt_text, log_file, local_err_summary)

    # HTML Rapor
    html_path = generate_html_report(scores, prompt_text, telemetry_data)

    winner_name, winner_data = get_winner(scores)
    if winner_name:
        logger.info("🏆 KAZANAN: %s (skor: %.1f, net süre: %s)",
                     winner_name, winner_data["total_score"],
                     f"{winner_data['execution_time']:.3f}s" if winner_data["execution_time"] else "N/A")

    # ── 7. FİNAL ───────────────────────────────────────────────
    print_final(scores, report_path, html_path)

    # Lokal hata raporu
    if local_err_summary["total_errors"] > 0:
        console.print(Panel(
            f"[bold bright_red]⚠️ {local_err_summary['total_errors']} lokal I/O hatası tespit edildi![/]\n"
            f"  📄 Detaylar: [dim]{error_logger._log_file}[/]",
            title="[bold]🛡️ Lokal Hata Raporu[/]",
            border_style="bright_red",
        ))
    else:
        console.print(Panel(
            "[bold bright_green]✅ Sıfır lokal I/O hatası — sistem sağlıklı![/]",
            title="[bold]🛡️ Lokal Hata Raporu[/]",
            border_style="bright_green",
        ))

    # LocalErrorLogger kapat
    error_logger.__exit__(None, None, None)

    console.print(Panel(
        "[bold bright_green]🔥 LOKAL MOTOR BAŞARIYLA TAMAMLADI![/]\n\n"
        f"  🏠 Mod: On-Premise (Sıfır Gecikme)\n"
        f"  📂 Dizin: {BASE_DIR}\n"
        f"  ⏱️ Hassasiyet: {SIGNAL_POLL_INTERVAL_MS}ms\n"
        f"  🖥️ Kaynak Takibi: psutil aktif\n"
        f"  🛡️ Hata Koruması: LocalErrorLogger aktif",
        title=f"[bold]🔥 {APP_NAME} v{VERSION} — LOKAL MOTOR[/]",
        border_style="bold bright_green",
    ))
    console.print()


# ═══════════════════════════════════════════════════════════════════
#  STATUS KOMUTU
# ═══════════════════════════════════════════════════════════════════

def cmd_status(args):
    print_banner()
    console.print(Panel("📊 Mevcut Durum — LOKAL MOD", border_style="bright_cyan"))
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
                    cpu = tele.get("avg_cpu", 0)
                    ram = tele.get("peak_ram_mb", 0)
                    if cpu > 0 or ram > 0:
                        tele_str += f" | CPU: {cpu:.0f}% | RAM: {ram:.0f}MB"

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
        description=f"⚡ {APP_NAME} — Multi-AI Coding Benchmark Tool v{VERSION} (Lokal On-Premise)",
    )
    sub = parser.add_subparsers(dest="command", help="Komutlar")

    p_run = sub.add_parser("run", help="Benchmark başlat (Lokal Mod)")
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
