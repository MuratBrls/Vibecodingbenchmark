# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Telemetry Engine v2.0
AI araçlarının her save/edit işlemini izler.
Deneme sayısı, hata sayısı ve olay loglarını tutar.
"""

import os
import time
import threading
import logging

from config import TARGETS, START_SIGNAL_FILE, WATCHED_EXTENSIONS, TASK_INPUT_FILE, STATUS_FILE

logger = logging.getLogger("vibebench.telemetry")

IGNORED_FILES = {TASK_INPUT_FILE, STATUS_FILE, START_SIGNAL_FILE}


class TelemetryTracker:
    """
    Bir hedef klasör için dosya değişiklik telemetrisini takip eder.

    Attributes:
        save_count:  Toplam dosya kaydetme/oluşturma sayısı
        retry_count: start_signal.json tekrar oluşturulma sayısı (ilkinden sonra)
        error_count: Tespit edilen hata sayısı (dosya silinip yeniden yazılması vb.)
        events_log:  Kronolojik olay kayıtları
    """

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.save_count = 0
        self.retry_count = 0
        self.error_count = 0
        self.events_log = []
        self._signal_seen = False
        self._known_files = {}  # path → son modify zamanı
        self._lock = threading.Lock()

    def record_signal(self):
        """start_signal.json olayını kaydet."""
        with self._lock:
            if self._signal_seen:
                self.retry_count += 1
                self._log_event("retry", "start_signal.json tekrar oluşturuldu")
                logger.info("%s: 🔄 Retry algılandı (toplam: %d)", self.tool_name, self.retry_count)
            else:
                self._signal_seen = True
                self._log_event("signal", "start_signal.json ilk kez alındı")

    def record_save(self, filepath: str):
        """Dosya kaydetme/oluşturma olayını kaydet."""
        basename = os.path.basename(filepath)
        with self._lock:
            prev_time = self._known_files.get(filepath)
            now = time.time()

            if prev_time is not None:
                # Aynı dosya tekrar kaydedildi → düzenleme/deneme olabilir
                delta = now - prev_time
                if delta < 2.0:
                    # Çok hızlı ardışık save → muhtemelen hata+düzeltme
                    self.error_count += 1
                    self._log_event("rapid_save", f"{basename} hızlı ardışık kayıt ({delta:.1f}s)")

            self._known_files[filepath] = now
            self.save_count += 1
            self._log_event("save", f"{basename} kaydedildi")

    def record_delete(self, filepath: str):
        """Dosya silme olayını kaydet (hata tespiti)."""
        basename = os.path.basename(filepath)
        with self._lock:
            if filepath in self._known_files:
                self.error_count += 1
                self._log_event("delete", f"{basename} silindi (hata olabilir)")
                del self._known_files[filepath]

    def _log_event(self, event_type: str, detail: str):
        """Olayı kronolojik log'a ekle."""
        self.events_log.append({
            "time": time.time(),
            "type": event_type,
            "detail": detail,
        })

    def get_summary(self) -> dict:
        """Telemetri özet raporu."""
        with self._lock:
            return {
                "saves": self.save_count,
                "retries": self.retry_count,
                "errors": self.error_count,
                "total_events": len(self.events_log),
                "events_log": list(self.events_log),
            }


def create_trackers() -> dict:
    """
    Tüm hedefler için TelemetryTracker oluşturur.

    Returns:
        {tool_name: TelemetryTracker}
    """
    trackers = {}
    for tool_name in TARGETS:
        trackers[tool_name] = TelemetryTracker(tool_name)
        logger.info("%s: telemetry tracker oluşturuldu", tool_name)
    return trackers
