# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Live Watcher v2.2 (Lokal On-Premise)
start_signal.json oluştuğu an kronometre başlar,
kaynak kod dosyası oluştuğu an kronometre durur.
Thinking time: global_start → signal (perf_counter ile ms hassasiyetinde)
Writing time:  signal → kod (perf_counter ile ms hassasiyetinde)
Telemetri: save sayısı, retry sayısı, hata sayısı, CPU/RAM takibi.
LocalErrorLogger ile Windows I/O hataları yakalanır.
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
    WATCHED_EXTENSIONS, WATCH_TIMEOUT, SIGNAL_POLL_INTERVAL_MS,
)
from telemetry import TelemetryTracker, create_trackers
from local_error_logger import LocalErrorLogger

logger = logging.getLogger("vibebench.watcher")

IGNORED_FILES = {TASK_INPUT_FILE, STATUS_FILE, START_SIGNAL_FILE}


class BenchmarkEventHandler(FileSystemEventHandler):
    """
    İki aşamalı izleme + telemetri + lokal hata yakalama:
      Aşama 1: start_signal.json bekle → signal_time kaydedilir, thinking_time hesaplanır
      Aşama 2: kaynak kod dosyası bekle → end_time kaydedilir, writing_time hesaplanır
    Tüm zamanlamalar time.perf_counter() ile milisaniye hassasiyetinde ölçülür.
    """

    def __init__(self, tool_name: str, target_dir: str, global_start: float,
                 on_complete, telemetry_tracker: TelemetryTracker,
                 error_logger: LocalErrorLogger = None):
        super().__init__()
        self.tool_name = tool_name
        self.target_dir = target_dir
        self.global_start = global_start  # perf_counter tabanlı

        # Signal trigger
        self.signal_received = False
        self.signal_time = None

        # Completion
        self.completed = False
        self.end_time = None
        self.detected_files = []

        # Telemetry
        self.telemetry = telemetry_tracker

        # Lokal hata yakalayıcı
        self._error_logger = error_logger

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
                self.telemetry.record_signal(self.global_start)
                if not self.signal_received:
                    self.signal_time = time.perf_counter()
                    self.signal_received = True
                    thinking_ms = (self.signal_time - self.global_start) * 1000
                    logger.info("%s: 🟢 start_signal.json alındı — kronometre başladı (düşünme: %.3fms)",
                                self.tool_name, thinking_ms)
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

            self.end_time = time.perf_counter()

            # Signal yoksa global_start kullan (geriye uyumluluk)
            if not self.signal_received:
                self.signal_time = self.global_start
                self.signal_received = True
                logger.warning("%s: signal olmadan kod alındı, global_start kullanılıyor", self.tool_name)

            self.completed = True

        # Telemetri: yazma süresi kaydı
        self.telemetry.record_completion(self.signal_time)

        self._update_status()
        net_ms = (self.end_time - self.signal_time) * 1000
        thinking_ms = (self.signal_time - self.global_start) * 1000
        total_ms = thinking_ms + net_ms
        logger.info("%s: ✅ tamamlandı — %s (düşünme: %.3fms, yazma: %.3fms, toplam: %.3fms)",
                    self.tool_name, basename, thinking_ms, net_ms, total_ms)

        try:
            if self._on_complete:
                self._on_complete(self.tool_name)
        except Exception as e:
            logger.error("%s: callback hatası — %s", self.tool_name, e)

    def _update_status(self):
        try:
            writing_time = round(self.end_time - self.signal_time, 6)
            thinking_time = round(self.signal_time - self.global_start, 6)
            total_time = round(thinking_time + writing_time, 6)
            tele = self.telemetry.get_summary()
            data = {
                "status": "completed",
                "local_mode": True,
                "signal_time": self.signal_time,
                "end_time": self.end_time,
                "thinking_time": thinking_time,
                "writing_time": writing_time,
                "total_time": total_time,
                "net_execution_time": writing_time,  # geriye uyumluluk
                "gross_time": total_time,
                "tool": self.tool_name,
                "detected_files": [os.path.basename(f) for f in self.detected_files],
                "telemetry": {
                    "saves": tele["saves"],
                    "retries": tele["retries"],
                    "errors": tele["errors"],
                    "thinking_time": tele["thinking_time"],
                    "writing_time": tele["writing_time"],
                    "avg_cpu": tele.get("avg_cpu", 0.0),
                    "peak_cpu": tele.get("peak_cpu", 0.0),
                    "avg_ram_mb": tele.get("avg_ram_mb", 0.0),
                    "peak_ram_mb": tele.get("peak_ram_mb", 0.0),
                },
            }
            status_path = os.path.join(self.target_dir, STATUS_FILE)

            # LocalErrorLogger ile güvenli yazma
            if self._error_logger:
                self._error_logger.safe_write(
                    status_path,
                    json.dumps(data, indent=2, ensure_ascii=False),
                )
            else:
                with open(status_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("%s: status.json güncelleme hatası — %s", self.tool_name, e)
            if self._error_logger:
                self._error_logger.capture(e, filepath=os.path.join(self.target_dir, STATUS_FILE),
                                           context="status.json yazma")

    @property
    def thinking_time(self):
        """Düşünme süresi (global_start → signal) — perf_counter tabanlı."""
        if self.signal_received and self.signal_time:
            return round(self.signal_time - self.global_start, 6)
        return None

    @property
    def writing_time(self):
        """Yazma süresi (signal → kod) — perf_counter tabanlı."""
        if self.completed and self.signal_time and self.end_time:
            return round(self.end_time - self.signal_time, 6)
        return None

    @property
    def total_time(self):
        """Toplam süre (thinking + writing)."""
        t = self.thinking_time
        w = self.writing_time
        if t is not None and w is not None:
            return round(t + w, 6)
        return None

    @property
    def net_execution_time(self):
        """Net süre (signal → kod) — geriye uyumluluk."""
        return self.writing_time

    @property
    def elapsed(self):
        """Global başlangıçtan itibaren geçen süre."""
        if self.completed:
            return round(self.end_time - self.global_start, 6)
        return round(time.perf_counter() - self.global_start, 6)

    def on_created(self, event):
        self._handle_event(event)

    def on_modified(self, event):
        self._handle_event(event)


class BenchmarkWatcher:
    """Tüm hedef klasörleri paralel olarak izler + telemetri + lokal hata yakalama."""

    def __init__(self, start_time: float, error_logger: LocalErrorLogger = None):
        self.start_time = start_time  # perf_counter tabanlı
        self.observers = []
        self.handlers = {}
        self.telemetry_trackers = create_trackers()
        self._error_logger = error_logger
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
        # Kaynak takibini başlat
        for tracker in self.telemetry_trackers.values():
            tracker.start_resource_tracking()

        for tool_name, target_dir in TARGETS.items():
            try:
                tracker = self.telemetry_trackers.get(tool_name)
                handler = BenchmarkEventHandler(
                    tool_name=tool_name,
                    target_dir=target_dir,
                    global_start=self.start_time,
                    on_complete=self._on_tool_complete,
                    telemetry_tracker=tracker,
                    error_logger=self._error_logger,
                )
                # Observer başlatma sırasında timeout tanımla (property olarak atanamaz)
                poll_seconds = SIGNAL_POLL_INTERVAL_MS / 1000.0
                observer = Observer(timeout=poll_seconds)
                observer.schedule(handler, target_dir, recursive=True)
                observer.start()
                self.observers.append(observer)
                self.handlers[tool_name] = handler
                logger.info("%s: 🟢 gözlemci başlatıldı — %s (polling: %dms)",
                            tool_name, target_dir, SIGNAL_POLL_INTERVAL_MS)
            except Exception as e:
                logger.error("%s: gözlemci başlatma hatası — %s", tool_name, e)
                if self._error_logger:
                    self._error_logger.capture(e, filepath=target_dir, context="observer başlatma")

    def emergency_cleanup(self):
        """
        Acil durum temizliği: tüm global_timer ve start_signal
        kontrollerini sıfırlar. Hata oluştuğunda çağrılır.
        """
        logger.warning("⚠️ EMERGENCY CLEANUP başlatıldı — tüm state sıfırlanıyor")
        with self._lock:
            self._completed_count = 0
            self._all_done.clear()

        for tool_name, handler in self.handlers.items():
            try:
                with handler._lock:
                    handler.signal_received = False
                    handler.signal_time = None
                    handler.completed = False
                    handler.end_time = None
                    handler.detected_files.clear()
                logger.info("%s: state sıfırlandı", tool_name)
            except Exception as e:
                logger.error("%s: cleanup hatası — %s", tool_name, e)

        for tool_name, tracker in self.telemetry_trackers.items():
            try:
                with tracker._lock:
                    tracker._signal_seen = False
                    tracker._signal_time = None
                    tracker.thinking_time = None
                    tracker.writing_time = None
                logger.info("%s: telemetry sıfırlandı", tool_name)
            except Exception as e:
                logger.error("%s: telemetry cleanup hatası — %s", tool_name, e)

        logger.info("✅ EMERGENCY CLEANUP tamamlandı")

    def wait(self, timeout: float = None) -> bool:
        return self._all_done.wait(timeout=timeout or WATCH_TIMEOUT)

    def stop(self):
        # Kaynak takibini durdur
        for tracker in self.telemetry_trackers.values():
            tracker.stop_resource_tracking()

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
                    "execution_time": handler.writing_time,
                    "thinking_time": handler.thinking_time,
                    "writing_time": handler.writing_time,
                    "total_time": handler.total_time,
                    "gross_time": handler.elapsed,
                    "signal_received": handler.signal_received,
                    "detected_files": [os.path.basename(f) for f in handler.detected_files],
                    "telemetry": tele_summary,
                }
            else:
                results[tool_name] = {
                    "status": "timeout",
                    "execution_time": None,
                    "thinking_time": handler.thinking_time,
                    "writing_time": None,
                    "total_time": None,
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
