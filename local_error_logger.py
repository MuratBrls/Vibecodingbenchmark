# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Local Error Logger v2.2
Windows'a özgü disk I/O hatalarını (path uzunluğu, izin, dosya kilidi)
yakalar ve yapılandırılmış JSON formatında loglar.
Thread-safe, context manager destekli.
"""

import json
import os
import time
import errno
import threading
import logging

from config import BASE_DIR, LOGS_DIR

logger = logging.getLogger("vibebench.local_error")

# Windows MAX_PATH sabiti
MAX_PATH_LENGTH = 260

# Bilinen Windows errno kodları
WINDOWS_ERRNO_MAP = {
    errno.EACCES: "İzin hatası (Permission Denied)",
    errno.ENOENT: "Dosya/dizin bulunamadı",
    errno.EEXIST: "Dosya zaten mevcut",
    errno.ENOSPC: "Disk alanı yetersiz",
    errno.ENAMETOOLONG: "Dosya adı çok uzun",
}

# Windows'a özgü ek hata kodları
WIN_ERROR_SHARING_VIOLATION = 32
WIN_ERROR_LOCK_VIOLATION = 33
WIN_ERROR_PATH_NOT_FOUND = 3
WIN_ERROR_ACCESS_DENIED = 5
WIN_ERROR_FILENAME_EXCED_RANGE = 206

WINDOWS_WINERROR_MAP = {
    WIN_ERROR_SHARING_VIOLATION: "Paylaşım ihlali — dosya başka işlem tarafından kilitli",
    WIN_ERROR_LOCK_VIOLATION: "Kilit ihlali — dosya bölgesi kilitli",
    WIN_ERROR_PATH_NOT_FOUND: "Yol bulunamadı (path not found)",
    WIN_ERROR_ACCESS_DENIED: "Erişim engellendi (access denied)",
    WIN_ERROR_FILENAME_EXCED_RANGE: "Dosya adı/yol uzunluğu sınırı aşıldı (>260 karakter)",
}


class LocalErrorLogger:
    """
    Windows lokal disk I/O hatalarını yakalar ve JSON formatında loglar.

    Kullanım:
        with LocalErrorLogger() as err_logger:
            err_logger.safe_write("dosya.txt", "içerik")
            # veya
            err_logger.capture(exception, filepath)

    Attributes:
        errors: Yakalanan hataların listesi
        error_count: Toplam hata sayısı
    """

    def __init__(self, log_file: str = None):
        self._log_file = log_file or os.path.join(LOGS_DIR, "local_errors.json")
        self._errors = []
        self._lock = threading.Lock()
        self._active = False

        # Log dizinini oluştur
        os.makedirs(os.path.dirname(self._log_file), exist_ok=True)
        logger.info("LocalErrorLogger başlatıldı — %s", self._log_file)

    def __enter__(self):
        self._active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._active = False
        self._flush()
        return False  # exception'ları yeniden fırlat

    @property
    def error_count(self) -> int:
        with self._lock:
            return len(self._errors)

    @property
    def errors(self) -> list:
        with self._lock:
            return list(self._errors)

    def capture(self, exc: Exception, filepath: str = "", context: str = ""):
        """
        Bir exception'ı yakalar ve loglar.

        Args:
            exc: Yakalanan exception
            filepath: İlgili dosya yolu (varsa)
            context: Ek bağlam bilgisi
        """
        with self._lock:
            error_entry = {
                "timestamp": time.time(),
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                "type": type(exc).__name__,
                "message": str(exc),
                "filepath": filepath,
                "context": context,
                "diagnosis": self._diagnose(exc, filepath),
            }

            # Windows errno bilgisi
            if hasattr(exc, "errno") and exc.errno is not None:
                error_entry["errno"] = exc.errno
                error_entry["errno_desc"] = WINDOWS_ERRNO_MAP.get(exc.errno, "Bilinmeyen errno")

            # Windows winerror bilgisi
            if hasattr(exc, "winerror") and exc.winerror is not None:
                error_entry["winerror"] = exc.winerror
                error_entry["winerror_desc"] = WINDOWS_WINERROR_MAP.get(
                    exc.winerror, f"Windows hata kodu: {exc.winerror}"
                )

            self._errors.append(error_entry)
            logger.error("🔴 Lokal I/O Hatası: [%s] %s — %s",
                         error_entry["type"], error_entry["message"],
                         error_entry["diagnosis"])

    def _diagnose(self, exc: Exception, filepath: str) -> str:
        """Hatayı teşhis edip çözüm önerisi döndürür."""
        # Path uzunluğu kontrolü
        if filepath:
            abs_path = os.path.abspath(filepath)
            if len(abs_path) >= MAX_PATH_LENGTH:
                return (f"⚠️ Dosya yolu {len(abs_path)} karakter — Windows MAX_PATH ({MAX_PATH_LENGTH}) "
                        f"sınırını aşıyor. Daha kısa bir dizin yapısı kullanın.")

        if isinstance(exc, PermissionError):
            return "🔒 Dosya/dizin üzerinde yazma izni yok. Yönetici olarak çalıştırın veya izinleri kontrol edin."

        if isinstance(exc, FileNotFoundError):
            return "📁 Hedef dizin mevcut değil veya yol geçersiz. Dizin yapısını kontrol edin."

        if isinstance(exc, OSError):
            winerror = getattr(exc, "winerror", None)
            if winerror == WIN_ERROR_SHARING_VIOLATION:
                return "🔐 Dosya başka bir işlem tarafından kilitli. Diğer uygulamaları kapatıp tekrar deneyin."
            if winerror == WIN_ERROR_FILENAME_EXCED_RANGE:
                return f"📏 Windows MAX_PATH ({MAX_PATH_LENGTH}) sınırı aşıldı. Dosya yollarını kısaltın."
            if winerror == WIN_ERROR_ACCESS_DENIED:
                return "🛑 Windows erişim engeli. Antivirus veya güvenlik yazılımını kontrol edin."

        return "ℹ️ Genel I/O hatası. Disk durumunu ve izinleri kontrol edin."

    def safe_write(self, filepath: str, data: str, encoding: str = "utf-8") -> bool:
        """
        Güvenli dosya yazma wrapper'ı. Hataları otomatik yakalar.

        Args:
            filepath: Yazılacak dosya yolu
            data: Yazılacak veri
            encoding: Dosya kodlaması

        Returns:
            True başarılı, False hatalı
        """
        abs_path = os.path.abspath(filepath)

        # Ön kontrol: path uzunluğu
        if len(abs_path) >= MAX_PATH_LENGTH:
            self.capture(
                OSError(f"Path uzunluğu ({len(abs_path)}) MAX_PATH ({MAX_PATH_LENGTH}) sınırını aşıyor"),
                filepath=abs_path,
                context="safe_write ön kontrol"
            )
            return False

        try:
            # Dizini oluştur
            dir_path = os.path.dirname(abs_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(abs_path, "w", encoding=encoding) as f:
                f.write(data)
            return True

        except (PermissionError, FileNotFoundError, OSError) as exc:
            self.capture(exc, filepath=abs_path, context="safe_write")
            return False

    def _flush(self):
        """Biriken hataları JSON dosyasına yazar."""
        with self._lock:
            if not self._errors:
                return
            try:
                # Mevcut logları oku (varsa)
                existing = []
                if os.path.isfile(self._log_file):
                    try:
                        with open(self._log_file, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        existing = []

                existing.extend(self._errors)

                with open(self._log_file, "w", encoding="utf-8") as f:
                    json.dump(existing, f, indent=2, ensure_ascii=False)

                logger.info("LocalErrorLogger: %d hata kaydı yazıldı — %s",
                            len(self._errors), self._log_file)
            except Exception as e:
                logger.error("LocalErrorLogger flush hatası: %s", e)

    def get_summary(self) -> dict:
        """Hata özet raporu döndürür."""
        with self._lock:
            if not self._errors:
                return {"total_errors": 0, "error_types": {}, "errors": []}

            type_counts = {}
            for err in self._errors:
                t = err["type"]
                type_counts[t] = type_counts.get(t, 0) + 1

            return {
                "total_errors": len(self._errors),
                "error_types": type_counts,
                "errors": list(self._errors),
            }
