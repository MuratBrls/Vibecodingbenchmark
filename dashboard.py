# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Live Dashboard v2.1 (Total Performance)
Canlı izleme (DÜŞÜNME + YAZMA sütunları) + genişletilmiş final skor tablosu.
"""

import os
import time

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich import box

from config import TARGETS, VERSION, APP_NAME

console = Console()


def _fmt(seconds) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.2f}s"
    m, s = divmod(seconds, 60)
    return f"{int(m)}m {s:.1f}s"


def _rank_text(rank: int) -> Text:
    medals = {1: "🥇 1.", 2: "🥈 2.", 3: "🥉 3."}
    styles = {1: "bold bright_yellow", 2: "bright_white", 3: "bright_red"}
    return Text(medals.get(rank, f"   {rank}."), style=styles.get(rank, "dim"))


# ═══════════════════════════════════════════════════════════════════
#  CANLI İZLEME
# ═══════════════════════════════════════════════════════════════════

def build_live_table(handlers: dict, start_time: float) -> Table:
    elapsed = time.time() - start_time
    table = Table(
        title=f"🔴 CANLI İZLEME  •  {_fmt(elapsed)}",
        box=box.ROUNDED, show_lines=True,
        title_style="bold blink bright_red",
        border_style="bright_magenta",
        header_style="bold bright_white on dark_blue",
        padding=(0, 1),
    )
    table.add_column("🔧 ARAÇ", style="bold", justify="center", min_width=14)
    table.add_column("🟢 SİNYAL", justify="center", min_width=12)
    table.add_column("📊 DURUM", justify="center", min_width=16)
    table.add_column("🧠 DÜŞÜNME", justify="center", min_width=12)
    table.add_column("✍️ YAZMA", justify="center", min_width=12)
    table.add_column("⏱️ TOPLAM", justify="center", min_width=12)
    table.add_column("🔄 DENEME", justify="center", min_width=10)
    table.add_column("❌ HATA", justify="center", min_width=8)
    table.add_column("📁 DOSYA", justify="left", min_width=22)

    for tool_name, h in handlers.items():
        now = time.time()

        # Sinyal durumu
        if h.signal_received:
            signal = Text("✅ Alındı", style="bright_green")
        else:
            signal = Text("⏳ Bekleniyor", style="dim yellow")

        # Düşünme süresi (canlı veya sabit)
        if h.signal_received and h.signal_time:
            thinking = Text(_fmt(h.signal_time - h.global_start), style="bold bright_magenta")
        else:
            # Henüz signal gelmedi → canlı sayaç
            thinking = Text(_fmt(now - h.global_start), style="bright_magenta blink")

        # Ana durum + yazma süresi
        if h.completed:
            status = Text("✅ BİTTİ", style="bold bright_green")
            writing = Text(_fmt(h.writing_time), style="bold bright_cyan")
            total = Text(_fmt(h.total_time), style="bold bright_green")
            files = ", ".join(os.path.basename(f) for f in h.detected_files) or "—"
        elif h.signal_received:
            status = Text("✍️ Yazıyor...", style="bright_cyan blink")
            writing = Text(_fmt(now - h.signal_time), style="bright_cyan blink")
            total_val = (h.signal_time - h.global_start) + (now - h.signal_time)
            total = Text(_fmt(total_val), style="bright_yellow")
            files = "—"
        else:
            status = Text("🧠 Düşünüyor...", style="bright_magenta blink")
            writing = Text("—", style="dim")
            total = Text(_fmt(now - h.global_start), style="dim yellow")
            files = "—"

        # Telemetri verileri
        tele = h.telemetry.get_summary()
        retries = tele.get("retries", 0)
        errors = tele.get("errors", 0)

        retry_text = Text(str(retries), style="bright_yellow" if retries > 0 else "dim green")
        error_text = Text(str(errors), style="bold bright_red" if errors > 0 else "dim green")

        table.add_row(
            Text(tool_name, style="bold bright_cyan"),
            signal, status,
            thinking, writing, total,
            retry_text, error_text,
            Text(files[:50], style="dim"),
        )
    return table


# ═══════════════════════════════════════════════════════════════════
#  FİNAL SKOR TABLOSU
# ═══════════════════════════════════════════════════════════════════

def build_score_table(scores: dict) -> Table:
    table = Table(
        title="🏆 FİNAL SKOR TABLOSU",
        box=box.HEAVY_EDGE, show_lines=True,
        title_style="bold bright_yellow",
        border_style="bright_blue",
        header_style="bold bright_white on dark_blue",
        padding=(0, 1),
    )
    table.add_column("🏅", justify="center", width=6)
    table.add_column("🔧 ARAÇ", style="bold", justify="center", min_width=14)
    table.add_column("🧠 DÜŞÜNME", justify="center", min_width=12)
    table.add_column("✍️ YAZMA", justify="center", min_width=12)
    table.add_column("⏱️ TOPLAM", justify="center", min_width=12)
    table.add_column("⚡ HIZ", justify="center", min_width=10)
    table.add_column("🏛️ MİMARİ", justify="center", min_width=14)
    table.add_column("❌ HATA/DENEME", justify="center", min_width=14)
    table.add_column("📦 KÜTÜPHANE", justify="center", min_width=12)
    table.add_column("⭐ TOPLAM", justify="center", min_width=10)

    sorted_items = sorted(scores.items(), key=lambda x: x[1]["rank"])

    for tool_name, d in sorted_items:
        rank = d["rank"]
        is_winner = rank == 1

        # Düşünme süresi
        tt = d.get("thinking_time")
        thinking_text = Text(_fmt(tt), style="bright_magenta" if tt is not None else "dim")

        # Yazma süresi
        wt = d.get("writing_time")
        writing_text = Text(_fmt(wt), style="bright_cyan" if wt is not None else "dim")

        # Toplam süre
        total_t = d.get("total_time")
        if total_t is not None:
            total_time_text = Text(_fmt(total_t), style="bold bright_green" if is_winner else "bright_white")
        else:
            total_time_text = Text("—", style="dim")

        # Hız skoru
        spd = Text(f"{d['speed_score']:.0f}", style="bold bright_green" if is_winner else "bright_white")

        # Mimari & Temiz Kod
        design = d.get("design", {})
        arch = design.get("architecture", "N/A")
        arch_score = d.get("arch_score", 0)
        arch_icons = {"OOP": "🏛️", "Functional": "⚙️", "Scripting": "📜", "N/A": "—"}
        arch_text = Text(f"{arch_icons.get(arch, '?')} {arch} ({arch_score:.0f})",
                         style="bright_green" if arch == "OOP" else ("bright_cyan" if arch == "Functional" else "dim"))

        # Hata/Deneme
        err_score = d.get("error_ratio_score", 0)
        tele = d.get("telemetry", {})
        retries = tele.get("retries", 0)
        errors = tele.get("errors", 0)
        err_style = "bright_green" if err_score >= 80 else ("bright_yellow" if err_score >= 50 else "bright_red")
        err_text = Text(f"{retries}R/{errors}E ({err_score:.0f})", style=err_style)

        # Kütüphane
        libs = design.get("all_imports", [])
        lib_score = d.get("library_score", 0)
        lib_text = Text(f"{len(libs)} adet ({lib_score:.0f})", style="bright_cyan")

        # Toplam skor
        total = d.get("total_score", 0)
        total_text = Text(f"{total:.1f}", style="bold bright_yellow" if is_winner else "bright_white")

        table.add_row(
            _rank_text(rank),
            Text(tool_name, style="bold bright_cyan" if is_winner else "bright_white"),
            thinking_text, writing_text, total_time_text,
            spd, arch_text, err_text, lib_text, total_text,
        )

    return table


def build_detail_panel(scores: dict) -> Panel:
    """Detaylı analiz paneli — mimari, kütüphaneler, temiz kod, süre detayları."""
    lines = []
    for tool_name, d in sorted(scores.items(), key=lambda x: x[1]["rank"]):
        design = d.get("design", {})
        pro = d.get("pro_analysis", {})
        tele = d.get("telemetry", {})
        libs = design.get("all_imports", [])
        funcs = design.get("total_functions", 0)
        classes = design.get("total_classes", 0)
        depth = design.get("max_loop_depth", 0)

        tt = d.get("thinking_time")
        wt = d.get("writing_time")
        tot = d.get("total_time")

        lines.append(f"[bold bright_cyan]{tool_name}[/]")
        lines.append(f"  🧠 Düşünme: {_fmt(tt)} | ✍️ Yazma: {_fmt(wt)} | ⏱️ Toplam: {_fmt(tot)}")
        lines.append(f"  📦 Kütüphaneler: {', '.join(libs) if libs else '—'}")
        lines.append(f"  🔧 {funcs} fonksiyon, {classes} sınıf, döngü derinliği: {depth}")
        lines.append(f"  🧹 Temiz Kod: {pro.get('clean_code_score', 0):.1f} | McCabe: {pro.get('mccabe_avg', 0):.1f} | PEP8: {pro.get('pep8_compliance', 0):.0f}% | Güvenlik: {pro.get('security_count', 0)} sorun")
        lines.append(f"  🔄 Deneme: {tele.get('retries', 0)} | 💾 Save: {tele.get('saves', 0)} | ❌ Hata: {tele.get('errors', 0)}")
        lines.append("")

    content = "\n".join(lines).rstrip()
    return Panel(content, title="[bold]📋 Detaylı Tasarım & Telemetri Analizi[/]", border_style="bright_blue", padding=(1, 2))


# ═══════════════════════════════════════════════════════════════════
#  BANNER & KAZANAN
# ═══════════════════════════════════════════════════════════════════

def print_banner():
    banner = Text(r"""
 ██████╗ ██╗      █████╗  ██████╗██╗  ██╗    ██████╗  ██████╗ ██╗  ██╗
 ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝    ██╔══██╗██╔═══██╗╚██╗██╔╝
 ██████╔╝██║     ███████║██║     █████╔╝     ██████╔╝██║   ██║ ╚███╔╝
 ██╔══██╗██║     ██╔══██║██║     ██╔═██╗     ██╔══██╗██║   ██║ ██╔██╗
 ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗    ██████╔╝╚██████╔╝██╔╝ ██╗
 ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝    ╚═════╝  ╚═════╝╚═╝  ╚═╝
""", style="bold bright_cyan")
    console.print(banner)
    console.print(Align.center(Text(f"⚡ {APP_NAME}  v{VERSION}  (Total Performance — Düşünme + Yazma Analizi)", style="bold bright_magenta")))
    console.print(Align.center(Text("🧠 Düşünme + ✍️ Yazma = ⏱️ Toplam  •  30% Hız · 30% Mimari · 25% Hata · 15% Kütüphane", style="dim bright_white")))
    console.print()


def print_winner(scores: dict):
    completed = {k: v for k, v in scores.items() if v["status"] == "completed"}
    if completed:
        winner = min(completed, key=lambda k: scores[k]["rank"])
        d = scores[winner]
        tt = d.get("thinking_time")
        wt = d.get("writing_time")
        tot = d.get("total_time")
        console.print(Panel(
            Align.center(Text(
                f"🏆 KAZANAN: {winner}  •  🧠 {_fmt(tt)} + ✍️ {_fmt(wt)} = ⏱️ {_fmt(tot)}  •  Skor: {d['total_score']:.1f}",
                style="bold bright_yellow"
            )),
            border_style="bright_yellow", box=box.DOUBLE,
        ))
    else:
        console.print(Panel(
            Align.center(Text("⏰ Hiçbir araç zamanında tamamlayamadı!", style="bold bright_red")),
            border_style="bright_red",
        ))
    console.print()


def print_final(scores: dict, report_path: str = "", html_report_path: str = ""):
    console.print()
    console.print(build_score_table(scores))
    console.print()
    console.print(build_detail_panel(scores))
    console.print()
    print_winner(scores)
    if report_path:
        console.print(f"  📄 JSON Rapor: [dim]{report_path}[/]")
    if html_report_path:
        console.print(f"  🌐 HTML Rapor: [dim]{html_report_path}[/]")
    if report_path or html_report_path:
        console.print()
