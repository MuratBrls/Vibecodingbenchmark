# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Telemetry Engine v2.2 (Lokal On-Premise)
AI araçlarının her save/edit işlemini izler.
Düşünme süresi (thinking_time) ve yazma süresi (writing_time) takibi.
Deneme sayısı, hata sayısı ve olay loglarını tutar.
psutil ile CPU ve RAM kaynak tüketimini ölçer.
"""

import os
import time
import threading
import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from config import (
    TARGETS, START_SIGNAL_FILE, WATCHED_EXTENSIONS,
    TASK_INPUT_FILE, STATUS_FILE, RESOURCE_SAMPLE_INTERVAL,
)

logger = logging.getLogger("vibebench.telemetry")

IGNORED_FILES = {TASK_INPUT_FILE, STATUS_FILE, START_SIGNAL_FILE}


class ResourceSampler:
    """
    Daemon thread ile arka planda CPU ve RAM kullanımını örnekler.
    psutil.Process() ile mevcut sürecin kaynak tüketimini izler.

    Attributes:
        cpu_samples: CPU yüzde örnekleri listesi
        ram_samples: RAM (MB) örnekleri listesi
    """

    def __init__(self, interval: float = RESOURCE_SAMPLE_INTERVAL):
        self.interval = interval
        self.cpu_samples = []
        self.ram_samples = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._process = None

        if PSUTIL_AVAILABLE:
            try:
                self._process = psutil.Process(os.getpid())
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning("psutil Process oluşturulamadı: %s", e)

    def start(self):
        """Örnekleme daemon thread'ini başlatır."""
        if not PSUTIL_AVAILABLE or self._process is None:
            logger.warning("psutil kullanılamıyor — kaynak takibi devre dışı")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._sample_loop,
            daemon=True,
            name="ResourceSampler",
        )
        self._thread.start()
        logger.info("ResourceSampler başlatıldı (aralık: %.1fs)", self.interval)

    def stop(self):
        """Örnekleme thread'ini durdurur."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("ResourceSampler durduruldu (toplam örnek: %d)", len(self.cpu_samples))

    def _sample_loop(self):
        """Periyodik olarak CPU ve RAM örnekler."""
        while not self._stop_event.is_set():
            try:
                cpu = self._process.cpu_percent(interval=0.1)
                mem_info = self._process.memory_info()
                ram_mb = round(mem_info.rss / (1024 * 1024), 1)

                with self._lock:
                    self.cpu_samples.append(cpu)
                    self.ram_samples.append(ram_mb)

            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                logger.debug("ResourceSampler örnekleme hatası: %s", e)

            self._stop_event.wait(self.interval)

    def get_stats(self) -> dict:
        """CPU ve RAM istatistiklerini döndürür."""
        with self._lock:
            if not self.cpu_samples:
                return {
                    "avg_cpu": 0.0,
                    "peak_cpu": 0.0,
                    "avg_ram_mb": 0.0,
                    "peak_ram_mb": 0.0,
                    "sample_count": 0,
                }

            return {
                "avg_cpu": round(sum(self.cpu_samples) / len(self.cpu_samples), 1),
                "peak_cpu": round(max(self.cpu_samples), 1),
                "avg_ram_mb": round(sum(self.ram_samples) / len(self.ram_samples), 1),
                "peak_ram_mb": round(max(self.ram_samples), 1),
                "sample_count": len(self.cpu_samples),
            }


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
        resource_sampler: CPU/RAM kaynak örnekleyicisi
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

        # Kaynak takibi
        self.resource_sampler = ResourceSampler()

    def start_resource_tracking(self):
        """CPU/RAM kaynak takibini başlatır."""
        self.resource_sampler.start()

    def stop_resource_tracking(self):
        """CPU/RAM kaynak takibini durdurur."""
        self.resource_sampler.stop()

    def record_signal(self, global_start: float):
        """
        start_signal.json olayını kaydet.
        thinking_time = signal_time - global_start
        """
        with self._lock:
            now = time.perf_counter()
            if self._signal_seen:
                self.retry_count += 1
                self._log_event("retry", "start_signal.json tekrar oluşturuldu")
                logger.info("%s: 🔄 Retry algılandı (toplam: %d)", self.tool_name, self.retry_count)
            else:
                self._signal_seen = True
                self._signal_time = now
                self.thinking_time = round(now - global_start, 6)
                self._log_event("signal", f"start_signal.json ilk kez alındı (düşünme: {self.thinking_time:.3f}s)")
                logger.info("%s: 🧠 Düşünme süresi: %.3fs", self.tool_name, self.thinking_time)

    def record_completion(self, signal_time: float):
        """
        Kod dosyası tamamlandığında çağrılır.
        writing_time = end_time - signal_time
        """
        with self._lock:
            now = time.perf_counter()
            self.writing_time = round(now - signal_time, 6)
            self._log_event("completion", f"Kod tamamlandı (yazma: {self.writing_time:.3f}s)")
            logger.info("%s: ✍️ Yazma süresi: %.3fs", self.tool_name, self.writing_time)

    def record_save(self, filepath: str):
        """Dosya kaydetme/oluşturma olayını kaydet."""
        basename = os.path.basename(filepath)
        with self._lock:
            prev_time = self._known_files.get(filepath)
            now = time.perf_counter()

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
            "perf_time": time.perf_counter(),
            "type": event_type,
            "detail": detail,
        })

    def get_summary(self) -> dict:
        """Telemetri özet raporu (kaynak istatistikleri dahil)."""
        with self._lock:
            resource_stats = self.resource_sampler.get_stats()
            return {
                "saves": self.save_count,
                "retries": self.retry_count,
                "errors": self.error_count,
                "thinking_time": self.thinking_time,
                "writing_time": self.writing_time,
                "total_events": len(self.events_log),
                "events_log": list(self.events_log),
                # Kaynak kullanımı (psutil)
                "avg_cpu": resource_stats.get("avg_cpu", 0.0),
                "peak_cpu": resource_stats.get("peak_cpu", 0.0),
                "avg_ram_mb": resource_stats.get("avg_ram_mb", 0.0),
                "peak_ram_mb": resource_stats.get("peak_ram_mb", 0.0),
                "resource_samples": resource_stats.get("sample_count", 0),
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
