# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Configuration Engine v2.0
Tüm yollar, parametreler ve sabitler.
"""

import os

# ─── META ────────────────────────────────────────────────────────
VERSION  = "2.0"
APP_NAME = "Black Box Deep Analytics"

# ─── BASE ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── HEDEF KLASÖRLER ─────────────────────────────────────────────
TARGETS = {
    "Antigravity": os.path.join(BASE_DIR, "test-benchantigravity"),
    "Cursor":      os.path.join(BASE_DIR, "test-benchcursor"),
    "Windsurf":    os.path.join(BASE_DIR, "test-benchwindsurf"),
}

# ─── DOSYA ADLARI ────────────────────────────────────────────────
TASK_INPUT_FILE    = "task_input.txt"
STATUS_FILE        = "status.json"
START_SIGNAL_FILE  = "start_signal.json"

# ─── İZLENEN UZANTILAR ───────────────────────────────────────────
WATCHED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".html", ".css", ".java", ".cpp", ".c",
    ".go", ".rs", ".rb", ".php", ".swift",
}

# ─── ZAMANLAMALAR ────────────────────────────────────────────────
WATCH_TIMEOUT      = 600   # 10 dakika
SUBPROCESS_TIMEOUT = 30    # script çalıştırma limiti

# ─── LOGLAMA ─────────────────────────────────────────────────────
LOGS_DIR = os.path.join(BASE_DIR, "logs")
