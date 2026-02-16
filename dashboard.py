# -*- coding: utf-8 -*-
"""
VibeBench Live Dashboard v1.1
Canlı izleme + genişletilmiş final skor tablosu (Mimari, Kütüphaneler).
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

from config import TARGETS

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
    table.add_column("⏱️ NET SÜRE", justify="center", min_width=12)
    table.add_column("📁 DOSYA", justify="left", min_width=22)

    for tool_name, h in handlers.items():
        # Sinyal durumu
        if h.signal_received:
            signal = Text("✅ Alındı", style="bright_green")
        else:
            signal = Text("⏳ Bekleniyor", style="dim yellow")

        # Ana durum
        if h.completed:
            status = Text("✅ BİTTİ", style="bold bright_green")
            net = Text(_fmt(h.net_execution_time), style="bold bright_green")
            files = ", ".join(os.path.basename(f) for f in h.detected_files) or "—"
        elif h.signal_received:
            status = Text("✍️ Yazıyor...", style="bright_cyan blink")
            net = Text(_fmt(time.time() - h.signal_time), style="bright_cyan")
            files = "—"
        else:
            status = Text("⏳ Bekliyor...", style="bright_yellow")
            net = Text("—", style="dim")
            files = "—"

        table.add_row(
            Text(tool_name, style="bold bright_cyan"),
            signal, status, net,
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
    table.add_column("⚡ HIZ", justify="center", min_width=10)
    table.add_column("🧪 VALID", justify="center", min_width=8)
    table.add_column("🏛️ MİMARİ", justify="center", min_width=14)
    table.add_column("📦 KÜTÜPHANE", justify="center", min_width=12)
    table.add_column("⭐ TOPLAM", justify="center", min_width=10)

    sorted_items = sorted(scores.items(), key=lambda x: x[1]["rank"])

    for tool_name, d in sorted_items:
        rank = d["rank"]
        is_winner = rank == 1

        # Hız
        et = d.get("execution_time")
        if et is not None:
            spd = Text(f"{_fmt(et)} ({d['speed_score']:.0f})", style="bold bright_green" if is_winner else "bright_white")
        else:
            spd = Text("— (0)", style="dim")

        # Validasyon
        v = d.get("validation_score", 0)
        vs = "bright_green" if v >= 80 else ("bright_yellow" if v >= 50 else "bright_red")
        val = Text(f"{v:.0f}%", style=vs)

        # Mimari
        design = d.get("design", {})
        arch = design.get("architecture", "N/A")
        arch_score = d.get("arch_score", 0)
        arch_icons = {"OOP": "🏛️", "Functional": "⚙️", "Scripting": "📜", "N/A": "—"}
        arch_text = Text(f"{arch_icons.get(arch, '?')} {arch} ({arch_score:.0f})",
                         style="bright_green" if arch == "OOP" else ("bright_cyan" if arch == "Functional" else "dim"))

        # Kütüphane
        libs = design.get("all_imports", [])
        lib_score = d.get("library_score", 0)
        lib_text = Text(f"{len(libs)} adet ({lib_score:.0f})", style="bright_cyan")

        # Toplam
        total = d.get("total_score", 0)
        total_text = Text(f"{total:.1f}", style="bold bright_yellow" if is_winner else "bright_white")

        table.add_row(
            _rank_text(rank),
            Text(tool_name, style="bold bright_cyan" if is_winner else "bright_white"),
            spd, val, arch_text, lib_text, total_text,
        )

    return table


def build_detail_panel(scores: dict) -> Panel:
    """Kütüphane ve mimari detay paneli."""
    lines = []
    for tool_name, d in sorted(scores.items(), key=lambda x: x[1]["rank"]):
        design = d.get("design", {})
        libs = design.get("all_imports", [])
        funcs = design.get("total_functions", 0)
        classes = design.get("total_classes", 0)
        depth = design.get("max_loop_depth", 0)

        lines.append(f"[bold bright_cyan]{tool_name}[/]")
        lines.append(f"  📦 Kütüphaneler: {', '.join(libs) if libs else '—'}")
        lines.append(f"  🔧 {funcs} fonksiyon, {classes} sınıf, döngü derinliği: {depth}")
        lines.append("")

    content = "\n".join(lines).rstrip()
    return Panel(content, title="[bold]📋 Detaylı Tasarım Analizi[/]", border_style="bright_blue", padding=(1, 2))


# ═══════════════════════════════════════════════════════════════════
#  BANNER & KAZANAN
# ═══════════════════════════════════════════════════════════════════

def print_banner():
    banner = Text(r"""
 ██╗   ██╗██╗██████╗ ███████╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
 ██║   ██║██║██╔══██╗██╔════╝██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
 ██║   ██║██║██████╔╝█████╗  ██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
 ╚██╗ ██╔╝██║██╔══██╗██╔══╝  ██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
  ╚████╔╝ ██║██████╔╝███████╗██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
   ╚═══╝  ╚═╝╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝
""", style="bold bright_cyan")
    console.print(banner)
    console.print(Align.center(Text("Multi-AI Coding Benchmark Tool  v1.1  (Signal Trigger)", style="bold bright_magenta")))
    console.print()


def print_winner(scores: dict):
    completed = {k: v for k, v in scores.items() if v["status"] == "completed"}
    if completed:
        winner = min(completed, key=lambda k: scores[k]["rank"])
        d = scores[winner]
        console.print(Panel(
            Align.center(Text(
                f"🏆 KAZANAN: {winner}  •  Net Süre: {_fmt(d['execution_time'])}  •  Skor: {d['total_score']:.1f}",
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


def print_final(scores: dict, report_path: str = ""):
    console.print()
    console.print(build_score_table(scores))
    console.print()
    console.print(build_detail_panel(scores))
    console.print()
    print_winner(scores)
    if report_path:
        console.print(f"  📄 Detaylı rapor: [dim]{report_path}[/]")
        console.print()
