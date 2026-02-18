# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Configuration Engine v2.2 (Lokal On-Premise)
Tüm yollar, parametreler ve sabitler.
Lokal mod: sıfır gecikme, psutil kaynak takibi, ms hassasiyetli watchdog.
"""

import os

# ─── META ────────────────────────────────────────────────────────
VERSION  = "2.2-local"
APP_NAME = "Black Box Deep Analytics"

# ─── LOKAL MOD ───────────────────────────────────────────────────
LOCAL_MODE = True   # On-Premise modu aktif

# ─── BASE ────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))

# ─── HEDEF KLASÖRLER (mutlak yollar) ────────────────────────────
TARGETS = {
    "Antigravity": os.path.abspath(os.path.join(BASE_DIR, "test-benchantigravity")),
    "Cursor":      os.path.abspath(os.path.join(BASE_DIR, "test-benchcursor")),
    "Windsurf":    os.path.abspath(os.path.join(BASE_DIR, "test-benchwindsurf")),
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

# ─── LOKAL WATCHDOG HASSASİYETİ ─────────────────────────────────
SIGNAL_POLL_INTERVAL_MS = 100    # watchdog polling aralığı (ms) — Windows I/O uyumlu

# ─── KAYNAK TAKİBİ (psutil) ─────────────────────────────────────
RESOURCE_SAMPLE_INTERVAL = 1.0   # CPU/RAM örnekleme aralığı (sn)

# ─── WINDOWS PATH SABİTİ ────────────────────────────────────────
MAX_PATH_LENGTH = 260            # Windows MAX_PATH limiti

# ─── LOGLAMA ─────────────────────────────────────────────────────
LOGS_DIR        = os.path.abspath(os.path.join(BASE_DIR, "logs"))
LOCAL_ERROR_LOG = os.path.abspath(os.path.join(LOGS_DIR, "local_errors.json"))
