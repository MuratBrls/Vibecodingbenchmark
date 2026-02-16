# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Live Watcher v2.0 (Signal Trigger + Telemetry)
start_signal.json oluştuğu an kronometre başlar,
kaynak kod dosyası oluştuğu an kronometre durur.
Telemetri: save sayısı, retry sayısı, hata sayısı.
"""

import json
import os
import time
import threading
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import (
    TARGETS, STATUS_FILE, TASK_INPUT_FILE, START_SIGNAL_FILE,
    WATCHED_EXTENSIONS, WATCH_TIMEOUT,
)
from telemetry import TelemetryTracker, create_trackers

logger = logging.getLogger("vibebench.watcher")

IGNORED_FILES = {TASK_INPUT_FILE, STATUS_FILE, START_SIGNAL_FILE}


class BenchmarkEventHandler(FileSystemEventHandler):
    """
    İki aşamalı izleme + telemetri:
      Aşama 1: start_signal.json bekle → signal_time kaydedilir
      Aşama 2: kaynak kod dosyası bekle → end_time kaydedilir
    Telemetri: her dosya olayı kaydedilir.
    Net süre = end_time - signal_time
    """

    def __init__(self, tool_name: str, target_dir: str, global_start: float,
                 on_complete, telemetry_tracker: TelemetryTracker):
        super().__init__()
        self.tool_name = tool_name
        self.target_dir = target_dir
        self.global_start = global_start

        # Signal trigger
        self.signal_received = False
        self.signal_time = None

        # Completion
        self.completed = False
        self.end_time = None
        self.detected_files = []

        # Telemetry
        self.telemetry = telemetry_tracker

        self._on_complete = on_complete
        self._lock = threading.Lock()

    def _is_watched(self, path: str) -> bool:
        _, ext = os.path.splitext(path)
        return ext.lower() in WATCHED_EXTENSIONS

    def _is_signal(self, path: str) -> bool:
        return os.path.basename(path) == START_SIGNAL_FILE

    def _handle_event(self, event):
        if event.is_directory:
            return

        src = event.src_path
        basename = os.path.basename(src)

        # ── AŞAMA 1: Signal Trigger ────────────────────────────
        if self._is_signal(src):
            with self._lock:
                self.telemetry.record_signal()
                if not self.signal_received:
                    self.signal_time = time.time()
                    self.signal_received = True
                    logger.info("%s: 🟢 start_signal.json alındı — kronometre başladı", self.tool_name)
            return

        # ── AŞAMA 2: Kod Dosyası ───────────────────────────────
        if basename in IGNORED_FILES:
            return
        if not self._is_watched(src):
            return

        # Telemetri: her save olayını kaydet
        self.telemetry.record_save(src)

        with self._lock:
            if src not in self.detected_files:
                self.detected_files.append(src)

            if self.completed:
                return

            self.end_time = time.time()

            # Signal yoksa global_start kullan (geriye uyumluluk)
            if not self.signal_received:
                self.signal_time = self.global_start
                self.signal_received = True
                logger.warning("%s: signal olmadan kod alındı, global_start kullanılıyor", self.tool_name)

            self.completed = True

        self._update_status()
        net_time = self.end_time - self.signal_time
        logger.info("%s: ✅ tamamlandı — %s (net: %.3fs)", self.tool_name, basename, net_time)

        try:
            if self._on_complete:
                self._on_complete(self.tool_name)
        except Exception as e:
            logger.error("%s: callback hatası — %s", self.tool_name, e)

    def _update_status(self):
        try:
            net_time = round(self.end_time - self.signal_time, 3)
            gross_time = round(self.end_time - self.global_start, 3)
            tele = self.telemetry.get_summary()
            data = {
                "status": "completed",
                "signal_time": self.signal_time,
                "end_time": self.end_time,
                "net_execution_time": net_time,
                "gross_time": gross_time,
                "tool": self.tool_name,
                "detected_files": [os.path.basename(f) for f in self.detected_files],
                "telemetry": {
                    "saves": tele["saves"],
                    "retries": tele["retries"],
                    "errors": tele["errors"],
                },
            }
            with open(os.path.join(self.target_dir, STATUS_FILE), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("%s: status.json güncelleme hatası — %s", self.tool_name, e)

    @property
    def net_execution_time(self):
        """Net süre (signal → kod)."""
        if self.completed and self.signal_time and self.end_time:
            return round(self.end_time - self.signal_time, 3)
        return None

    @property
    def elapsed(self):
        """Global başlangıçtan itibaren geçen süre."""
        if self.completed:
            return round(self.end_time - self.global_start, 3)
        return round(time.time() - self.global_start, 3)

    def on_created(self, event):
        self._handle_event(event)

    def on_modified(self, event):
        self._handle_event(event)


class BenchmarkWatcher:
    """Tüm hedef klasörleri paralel olarak izler + telemetri."""

    def __init__(self, start_time: float):
        self.start_time = start_time
        self.observers = []
        self.handlers = {}
        self.telemetry_trackers = create_trackers()
        self._completed_count = 0
        self._total = len(TARGETS)
        self._lock = threading.Lock()
        self._all_done = threading.Event()

    def _on_tool_complete(self, tool_name: str):
        with self._lock:
            self._completed_count += 1
            if self._completed_count >= self._total:
                self._all_done.set()

    def start(self):
        for tool_name, target_dir in TARGETS.items():
            try:
                tracker = self.telemetry_trackers.get(tool_name)
                handler = BenchmarkEventHandler(
                    tool_name=tool_name,
                    target_dir=target_dir,
                    global_start=self.start_time,
                    on_complete=self._on_tool_complete,
                    telemetry_tracker=tracker,
                )
                observer = Observer()
                observer.schedule(handler, target_dir, recursive=True)
                observer.start()
                self.observers.append(observer)
                self.handlers[tool_name] = handler
                logger.info("%s: gözlemci başlatıldı — %s", tool_name, target_dir)
            except Exception as e:
                logger.error("%s: gözlemci başlatma hatası — %s", tool_name, e)

    def wait(self, timeout: float = None) -> bool:
        return self._all_done.wait(timeout=timeout or WATCH_TIMEOUT)

    def stop(self):
        for obs in self.observers:
            try:
                obs.stop()
            except Exception:
                pass
        for obs in self.observers:
            try:
                obs.join(timeout=5)
            except Exception:
                pass

    def get_results(self) -> dict:
        results = {}
        for tool_name, handler in self.handlers.items():
            tele_summary = handler.telemetry.get_summary()
            if handler.completed:
                results[tool_name] = {
                    "status": "completed",
                    "execution_time": handler.net_execution_time,
                    "gross_time": handler.elapsed,
                    "signal_received": handler.signal_received,
                    "detected_files": [os.path.basename(f) for f in handler.detected_files],
                    "telemetry": tele_summary,
                }
            else:
                results[tool_name] = {
                    "status": "timeout",
                    "execution_time": None,
                    "gross_time": None,
                    "signal_received": handler.signal_received,
                    "detected_files": [],
                    "telemetry": tele_summary,
                }
        return results

    def get_telemetry_data(self) -> dict:
        """Tüm telemetri verilerini döndürür."""
        data = {}
        for tool_name, handler in self.handlers.items():
            data[tool_name] = handler.telemetry.get_summary()
        return data
