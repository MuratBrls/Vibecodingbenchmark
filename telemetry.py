# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Telemetry Engine v2.1 (Total Performance)
AI araçlarının her save/edit işlemini izler.
Düşünme süresi (thinking_time) ve yazma süresi (writing_time) takibi.
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
        save_count:    Toplam dosya kaydetme/oluşturma sayısı
        retry_count:   start_signal.json tekrar oluşturulma sayısı (ilkinden sonra)
        error_count:   Tespit edilen hata sayısı (dosya silinip yeniden yazılması vb.)
        thinking_time: Global start → signal arası süre (saniye)
        writing_time:  Signal → kod tamamlanma arası süre (saniye)
        events_log:    Kronolojik olay kayıtları
    """

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.save_count = 0
        self.retry_count = 0
        self.error_count = 0
        self.thinking_time = None
        self.writing_time = None
        self.events_log = []
        self._signal_seen = False
        self._signal_time = None
        self._known_files = {}  # path → son modify zamanı
        self._lock = threading.Lock()

    def record_signal(self, global_start: float):
        """
        start_signal.json olayını kaydet.
        thinking_time = signal_time - global_start
        """
        with self._lock:
            now = time.time()
            if self._signal_seen:
                self.retry_count += 1
                self._log_event("retry", "start_signal.json tekrar oluşturuldu")
                logger.info("%s: 🔄 Retry algılandı (toplam: %d)", self.tool_name, self.retry_count)
            else:
                self._signal_seen = True
                self._signal_time = now
                self.thinking_time = round(now - global_start, 3)
                self._log_event("signal", f"start_signal.json ilk kez alındı (düşünme: {self.thinking_time:.3f}s)")
                logger.info("%s: 🧠 Düşünme süresi: %.3fs", self.tool_name, self.thinking_time)

    def record_completion(self, signal_time: float):
        """
        Kod dosyası tamamlandığında çağrılır.
        writing_time = end_time - signal_time
        """
        with self._lock:
            now = time.time()
            self.writing_time = round(now - signal_time, 3)
            self._log_event("completion", f"Kod tamamlandı (yazma: {self.writing_time:.3f}s)")
            logger.info("%s: ✍️ Yazma süresi: %.3fs", self.tool_name, self.writing_time)

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
                "thinking_time": self.thinking_time,
                "writing_time": self.writing_time,
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
