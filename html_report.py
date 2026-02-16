# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — HTML Report Generator v2.0
Benchmark bitiminde logs/ altına detaylı, grafikli HTML raporu üretir.
Pure HTML + inline CSS + inline SVG charts — dış bağımlılık yok.
"""

import os
import time
import html
import logging

from config import LOGS_DIR, VERSION, APP_NAME

logger = logging.getLogger("vibebench.html_report")


def _score_color(score: float) -> str:
    if score >= 80:
        return "#00e676"
    elif score >= 60:
        return "#ffea00"
    elif score >= 40:
        return "#ff9100"
    return "#ff1744"


def _bar_svg(scores: dict, key: str, label: str, max_val: float = 100.0) -> str:
    """Yatay bar chart SVG üretir."""
    items = sorted(scores.items(), key=lambda x: x[1].get(key, 0), reverse=True)
    bar_height = 32
    gap = 8
    total_height = len(items) * (bar_height + gap) + 40
    width = 600

    svg = f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">\n'
    svg += f'  <text x="{width//2}" y="22" text-anchor="middle" fill="#e0e0e0" font-size="14" font-weight="bold">{html.escape(label)}</text>\n'

    y = 40
    for tool_name, data in items:
        val = data.get(key, 0) or 0
        bar_w = max(2, (val / max_val) * (width - 160))
        color = _score_color(val)

        svg += f'  <rect x="120" y="{y}" width="{bar_w}" height="{bar_height}" rx="4" fill="{color}" opacity="0.85"/>\n'
        svg += f'  <text x="110" y="{y + 21}" text-anchor="end" fill="#b0b0b0" font-size="12">{html.escape(tool_name)}</text>\n'
        svg += f'  <text x="{120 + bar_w + 8}" y="{y + 21}" fill="#ffffff" font-size="13" font-weight="bold">{val:.1f}</text>\n'
        y += bar_height + gap

    svg += '</svg>'
    return svg


def _tool_card(tool_name: str, data: dict, telemetry: dict) -> str:
    """Araç detay kartı HTML'i üretir."""
    rank = data.get("rank", 0)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    medal = medals.get(rank, f"#{rank}")

    total = data.get("total_score", 0)
    et = data.get("execution_time")
    et_str = f"{et:.3f}s" if et is not None else "N/A"

    design = data.get("design", {})
    arch = design.get("architecture", "N/A")
    libs = design.get("all_imports", [])
    funcs = design.get("total_functions", 0)
    classes = design.get("total_classes", 0)

    pro = data.get("pro_analysis", {})
    mccabe = pro.get("mccabe_avg", 0)
    pep8 = pro.get("pep8_compliance", 0)
    sec_count = pro.get("security_count", 0)

    tele = telemetry.get(tool_name, {})
    saves = tele.get("saves", 0)
    retries = tele.get("retries", 0)
    errors = tele.get("errors", 0)

    border_color = "#ffd700" if rank == 1 else "#444"
    bg = "rgba(255,215,0,0.05)" if rank == 1 else "rgba(255,255,255,0.02)"

    return f"""
    <div class="card" style="border-color:{border_color}; background:{bg};">
        <div class="card-header">
            <span class="medal">{medal}</span>
            <span class="tool-name">{html.escape(tool_name)}</span>
            <span class="total-score" style="color:{_score_color(total)}">{total:.1f}</span>
        </div>
        <div class="card-grid">
            <div class="metric">
                <div class="metric-label">⏱️ Net Süre</div>
                <div class="metric-value">{et_str}</div>
            </div>
            <div class="metric">
                <div class="metric-label">🏛️ Mimari</div>
                <div class="metric-value">{html.escape(arch)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">⚡ Hız Skoru</div>
                <div class="metric-value" style="color:{_score_color(data.get('speed_score', 0))}">{data.get('speed_score', 0):.1f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">🏛️ Mimari Skoru</div>
                <div class="metric-value" style="color:{_score_color(data.get('arch_score', 0))}">{data.get('arch_score', 0):.1f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">❌ Hata/Deneme</div>
                <div class="metric-value" style="color:{_score_color(data.get('error_ratio_score', 0))}">{data.get('error_ratio_score', 0):.1f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">💎 Kütüphane</div>
                <div class="metric-value" style="color:{_score_color(data.get('library_score', 0))}">{data.get('library_score', 0):.1f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">📦 Import Sayısı</div>
                <div class="metric-value">{len(libs)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">🔧 Fonksiyon/Sınıf</div>
                <div class="metric-value">{funcs} / {classes}</div>
            </div>
            <div class="metric">
                <div class="metric-label">🔄 Deneme</div>
                <div class="metric-value">{retries}</div>
            </div>
            <div class="metric">
                <div class="metric-label">💾 Save Sayısı</div>
                <div class="metric-value">{saves}</div>
            </div>
            <div class="metric">
                <div class="metric-label">⚠️ Hata</div>
                <div class="metric-value" style="color:{'#ff1744' if errors > 0 else '#00e676'}">{errors}</div>
            </div>
            <div class="metric">
                <div class="metric-label">🔒 Güvenlik</div>
                <div class="metric-value" style="color:{'#ff1744' if sec_count > 0 else '#00e676'}">{sec_count} sorun</div>
            </div>
        </div>
        <div class="libs-section">
            <span class="libs-label">📦 Kütüphaneler:</span>
            <span class="libs-list">{', '.join(html.escape(l) for l in libs) if libs else 'Yok'}</span>
        </div>
    </div>
    """


def generate_html_report(scores: dict, prompt_text: str, telemetry_data: dict) -> str:
    """
    Detaylı HTML raporu üretir ve logs/ altına kaydeder.

    Args:
        scores: Skorlama sonuçları
        prompt_text: Kullanılan prompt
        telemetry_data: {tool_name: telemetry_summary}

    Returns:
        HTML dosya yolu
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(LOGS_DIR, f"report_{timestamp}.html")

    # Kazanan
    winner = None
    if scores:
        winner = min(scores, key=lambda k: scores[k].get("rank", 999))

    # Tool kartları
    cards_html = ""
    for tool_name, data in sorted(scores.items(), key=lambda x: x[1].get("rank", 999)):
        cards_html += _tool_card(tool_name, data, telemetry_data)

    # SVG Charts
    chart_total = _bar_svg(scores, "total_score", "⭐ TOPLAM SKOR")
    chart_speed = _bar_svg(scores, "speed_score", "⚡ HIZ SKORU")
    chart_arch = _bar_svg(scores, "arch_score", "🏛️ MİMARİ SKORU")
    chart_error = _bar_svg(scores, "error_ratio_score", "❌ HATA/DENEME SKORU")

    winner_html = ""
    if winner:
        wd = scores[winner]
        et = wd.get("execution_time")
        et_str = f"{et:.3f}s" if et is not None else "N/A"
        winner_html = f"""
        <div class="winner-banner">
            <div class="winner-icon">🏆</div>
            <div class="winner-text">KAZANAN: {html.escape(winner)}</div>
            <div class="winner-detail">Net Süre: {et_str} • Skor: {wd.get('total_score', 0):.1f}</div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{APP_NAME} — Rapor {timestamp}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0a0a0f;
            color: #e0e0e0;
            font-family: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            min-height: 100vh;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 30px 20px; }}

        /* Header */
        .header {{
            text-align: center;
            padding: 40px 0 30px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.2rem;
            background: linear-gradient(135deg, #00e5ff, #7c4dff, #ff1744);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
            letter-spacing: 2px;
        }}
        .header .version {{
            color: #7c4dff;
            font-size: 0.9rem;
            letter-spacing: 3px;
            text-transform: uppercase;
        }}
        .header .timestamp {{
            color: #666;
            font-size: 0.85rem;
            margin-top: 10px;
        }}

        /* Prompt */
        .prompt-box {{
            background: rgba(124, 77, 255, 0.08);
            border: 1px solid rgba(124, 77, 255, 0.2);
            border-radius: 10px;
            padding: 18px 24px;
            margin-bottom: 30px;
        }}
        .prompt-label {{
            color: #7c4dff;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 6px;
        }}
        .prompt-text {{
            color: #e0e0e0;
            font-size: 1.05rem;
        }}

        /* Winner */
        .winner-banner {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, rgba(255,215,0,0.1), rgba(255,152,0,0.05));
            border: 2px solid rgba(255,215,0,0.3);
            border-radius: 14px;
            margin-bottom: 30px;
        }}
        .winner-icon {{ font-size: 3rem; margin-bottom: 8px; }}
        .winner-text {{
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffd700;
            letter-spacing: 2px;
        }}
        .winner-detail {{
            color: #ffab00;
            margin-top: 6px;
            font-size: 1rem;
        }}

        /* Scoring Weights */
        .weights {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .weight-chip {{
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
            padding: 8px 18px;
            font-size: 0.85rem;
            color: #b0b0b0;
        }}

        /* Charts */
        .charts {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-box {{
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}

        /* Cards */
        .card {{
            border: 1px solid #444;
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 20px;
            transition: transform 0.2s;
        }}
        .card:hover {{ transform: translateY(-2px); }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 18px;
            padding-bottom: 14px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        .medal {{ font-size: 2rem; }}
        .tool-name {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #00e5ff;
            flex: 1;
        }}
        .total-score {{
            font-size: 2rem;
            font-weight: 800;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 14px;
        }}
        .metric {{
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            padding: 10px 12px;
            text-align: center;
        }}
        .metric-label {{
            font-size: 0.72rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #e0e0e0;
        }}
        .libs-section {{
            font-size: 0.85rem;
            color: #888;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.04);
        }}
        .libs-label {{ color: #7c4dff; }}
        .libs-list {{ color: #b0b0b0; }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 30px 0;
            color: #444;
            font-size: 0.8rem;
            border-top: 1px solid rgba(255,255,255,0.04);
            margin-top: 30px;
        }}

        @media (max-width: 768px) {{
            .card-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .charts {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ {APP_NAME}</h1>
            <div class="version">v{VERSION} — Multi-AI Coding Benchmark</div>
            <div class="timestamp">📅 {time.strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>

        <div class="prompt-box">
            <div class="prompt-label">📝 Prompt</div>
            <div class="prompt-text">{html.escape(prompt_text[:500])}</div>
        </div>

        {winner_html}

        <div class="weights">
            <span class="weight-chip">⏱️ Hız %30</span>
            <span class="weight-chip">🏛️ Mimari %30</span>
            <span class="weight-chip">❌ Hata/Deneme %25</span>
            <span class="weight-chip">💎 Kütüphane %15</span>
        </div>

        <div class="charts">
            <div class="chart-box">{chart_total}</div>
            <div class="chart-box">{chart_speed}</div>
            <div class="chart-box">{chart_arch}</div>
            <div class="chart-box">{chart_error}</div>
        </div>

        <h2 style="color:#00e5ff; margin-bottom:20px; font-size:1.3rem;">📊 Detaylı Sonuçlar</h2>
        {cards_html}

        <div class="footer">
            {APP_NAME} v{VERSION} — Powered by Black Box Deep Analytics Engine<br>
            Generated at {time.strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

    try:
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("HTML rapor oluşturuldu: %s", report_file)
        return report_file
    except Exception as e:
        logger.error("HTML rapor oluşturma hatası: %s", e)
        return ""
