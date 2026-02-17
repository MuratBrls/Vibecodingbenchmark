"""
Media Library — Kendi Kendini Organize Eden Medya Kütüphanesi
OOP mimarisinde: tarama, EXIF analizi, tarih bazlı klasörleme,
duplikat tespiti, thumbnail üretimi ve istatistik raporlama.
"""

import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging
from PIL import Image
from PIL.ExifTags import TAGS


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  DATA MODELS
# ═══════════════════════════════════════════════════════════════

@dataclass
class MediaMetadata:
    """Bir medya dosyasının EXIF ve teknik bilgileri."""
    width: int = 0
    height: int = 0
    camera_make: str = ""
    camera_model: str = ""
    date_taken: Optional[datetime] = None
    iso: Optional[int] = None
    exposure_time: str = ""
    f_number: str = ""
    focal_length: str = ""
    orientation: int = 1
    file_hash: str = ""


@dataclass
class MediaItem:
    """Tek bir medya dosyasını temsil eder."""
    path: Path
    name: str
    extension: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    metadata: MediaMetadata = field(default_factory=MediaMetadata)
    tags: Set[str] = field(default_factory=set)

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)

    @property
    def resolution(self) -> str:
        if self.metadata.width and self.metadata.height:
            return f"{self.metadata.width}x{self.metadata.height}"
        return "N/A"

    def __repr__(self) -> str:
        return f"MediaItem({self.name}, {self.size_mb}MB, {self.resolution})"


# ═══════════════════════════════════════════════════════════════
#  EXIF READER
# ═══════════════════════════════════════════════════════════════

class ExifReader:
    """EXIF metadata okuyucu — fotoğraflardan detaylı bilgi çıkarır."""

    EXIF_DATE_FMT = "%Y:%m:%d %H:%M:%S"
    TAG_MAP = {
        "Make": "camera_make", "Model": "camera_model",
        "DateTimeOriginal": "date_taken", "ISOSpeedRatings": "iso",
        "ExposureTime": "exposure_time", "FNumber": "f_number",
        "FocalLength": "focal_length", "Orientation": "orientation",
    }

    @classmethod
    def read(cls, filepath: Path) -> MediaMetadata:
        meta = MediaMetadata()
        try:
            with Image.open(filepath) as img:
                meta.width, meta.height = img.size
                exif = img._getexif()
                if exif:
                    cls._parse(exif, meta)
        except Exception as e:
            logger.debug("EXIF hatası %s: %s", filepath.name, e)
        meta.file_hash = cls._hash(filepath)
        return meta

    @classmethod
    def _parse(cls, exif: dict, meta: MediaMetadata):
        for tid, val in exif.items():
            tag = TAGS.get(tid, "")
            if tag in cls.TAG_MAP:
                attr = cls.TAG_MAP[tag]
                if attr == "date_taken":
                    try:
                        val = datetime.strptime(str(val), cls.EXIF_DATE_FMT)
                    except (ValueError, TypeError):
                        continue
                setattr(meta, attr, val)

    @staticmethod
    def _hash(fp: Path, chunk: int = 8192) -> str:
        h = hashlib.md5()
        try:
            with open(fp, "rb") as f:
                while data := f.read(chunk):
                    h.update(data)
        except OSError:
            return ""
        return h.hexdigest()


# ═══════════════════════════════════════════════════════════════
#  THUMBNAIL GENERATOR
# ═══════════════════════════════════════════════════════════════

class ThumbnailGenerator:
    """Önizleme resimleri üretir."""

    def __init__(self, output_dir: Path, size: tuple = (256, 256)):
        self.output_dir = output_dir
        self.size = size
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, item: MediaItem) -> Optional[Path]:
        try:
            dest = self.output_dir / f"thumb_{item.name}"
            with Image.open(item.path) as img:
                img.thumbnail(self.size, Image.LANCZOS)
                img.save(dest, quality=85, optimize=True)
            return dest
        except Exception as e:
            logger.error("Thumbnail hatası %s: %s", item.name, e)
            return None

    def generate_batch(self, items: List[MediaItem]) -> Dict[str, Path]:
        results = {}
        for item in items:
            path = self.generate(item)
            if path:
                results[item.name] = path
        logger.info("%d/%d thumbnail oluşturuldu", len(results), len(items))
        return results


# ═══════════════════════════════════════════════════════════════
#  MEDIA SCANNER
# ═══════════════════════════════════════════════════════════════

class MediaScanner:
    """Desteklenen medya dosyalarını tarar."""

    SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}

    def __init__(self, root: Path, recursive: bool = True):
        self.root = root
        self.recursive = recursive

    def scan(self) -> List[MediaItem]:
        if not self.root.exists():
            raise FileNotFoundError(f"Dizin bulunamadı: {self.root}")
        items = []
        pattern = "**/*" if self.recursive else "*"
        for fp in self.root.glob(pattern):
            if fp.is_file() and fp.suffix.lower() in self.SUPPORTED:
                try:
                    items.append(self._build(fp))
                except Exception as e:
                    logger.warning("Hata %s: %s", fp.name, e)
        logger.info("%d dosya bulundu", len(items))
        return items

    @staticmethod
    def _build(fp: Path) -> MediaItem:
        stat = fp.stat()
        return MediaItem(
            path=fp, name=fp.name, extension=fp.suffix.lower(),
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            metadata=ExifReader.read(fp),
        )


# ═══════════════════════════════════════════════════════════════
#  ORGANIZER
# ═══════════════════════════════════════════════════════════════

class MediaOrganizer:
    """Medya dosyalarını tarih bazlı klasörler."""

    def __init__(self, destination: Path, pattern: str = "%Y/%Y-%m"):
        self.destination = destination
        self.pattern = pattern

    def organize(self, items: List[MediaItem]) -> List[Dict]:
        moved = []
        for item in items:
            date = item.metadata.date_taken or item.created_at
            folder = self.destination / date.strftime(self.pattern)
            folder.mkdir(parents=True, exist_ok=True)
            dest = self._safe_copy(folder, item)
            moved.append({"source": str(item.path), "dest": str(dest), "date": date.isoformat()})
        logger.info("%d dosya organize edildi", len(moved))
        return moved

    @staticmethod
    def _safe_copy(folder: Path, item: MediaItem) -> Path:
        dest = folder / item.name
        if not dest.exists():
            shutil.copy2(str(item.path), str(dest))
            return dest
        stem, ext = os.path.splitext(item.name)
        c = 1
        while dest.exists():
            dest = folder / f"{stem}_{c}{ext}"
            c += 1
        shutil.copy2(str(item.path), str(dest))
        return dest


# ═══════════════════════════════════════════════════════════════
#  DUPLICATE DETECTOR
# ═══════════════════════════════════════════════════════════════

class DuplicateDetector:
    """Hash tabanlı duplikat dosya tespiti."""

    def detect(self, items: List[MediaItem]) -> Dict[str, List[MediaItem]]:
        hmap: Dict[str, List[MediaItem]] = defaultdict(list)
        for item in items:
            if item.metadata.file_hash:
                hmap[item.metadata.file_hash].append(item)
        dupes = {h: g for h, g in hmap.items() if len(g) > 1}
        logger.info("Duplikat: %d grup", len(dupes))
        return dupes


# ═══════════════════════════════════════════════════════════════
#  STATISTICS
# ═══════════════════════════════════════════════════════════════

class MediaStatistics:
    """Koleksiyon istatistik hesaplayıcı."""

    def analyze(self, items: List[MediaItem]) -> Dict:
        if not items:
            return {"total": 0}
        total_sz = sum(i.size_bytes for i in items)
        exts = defaultdict(int)
        cams = defaultdict(int)
        monthly = defaultdict(int)
        for item in items:
            exts[item.extension] += 1
            if item.metadata.camera_make:
                cams[item.metadata.camera_make] += 1
            d = item.metadata.date_taken or item.created_at
            monthly[d.strftime("%Y-%m")] += 1
        return {
            "total": len(items),
            "total_size_mb": round(total_sz / 1048576, 2),
            "avg_size_mb": round(total_sz / len(items) / 1048576, 2),
            "by_extension": dict(exts),
            "by_camera": dict(cams),
            "by_month": dict(sorted(monthly.items())),
            "largest": max(items, key=lambda i: i.size_bytes).name,
            "smallest": min(items, key=lambda i: i.size_bytes).name,
        }


# ═══════════════════════════════════════════════════════════════
#  MEDIA LIBRARY — ANA ORKESTRATÖR
# ═══════════════════════════════════════════════════════════════

class MediaLibrary:
    """
    Ana medya kütüphanesi — tüm bileşenleri orkestre eder.

    Kullanım:
        lib = MediaLibrary("./photos", "./organized")
        lib.load()
        lib.organize()
        stats = lib.get_statistics()
        dupes = lib.find_duplicates()
    """

    def __init__(self, source: str, destination: str = None,
                 date_pattern: str = "%Y/%Y-%m", recursive: bool = True):
        self.source = Path(source)
        self.destination = Path(destination) if destination else self.source / "organized"
        self.scanner = MediaScanner(self.source, recursive)
        self.organizer = MediaOrganizer(self.destination, date_pattern)
        self.dup_detector = DuplicateDetector()
        self.stats_engine = MediaStatistics()
        self.items: List[MediaItem] = []
        self._loaded = False

    def load(self) -> int:
        logger.info("Tarama: %s", self.source)
        self.items = self.scanner.scan()
        self._loaded = True
        return len(self.items)

    def organize(self) -> List[Dict]:
        self._ensure_loaded()
        return self.organizer.organize(self.items)

    def find_duplicates(self) -> Dict[str, List[MediaItem]]:
        self._ensure_loaded()
        return self.dup_detector.detect(self.items)

    def get_statistics(self) -> Dict:
        self._ensure_loaded()
        return self.stats_engine.analyze(self.items)

    def generate_thumbnails(self, out_dir: str = None, size=(256, 256)) -> Dict[str, Path]:
        self._ensure_loaded()
        gen = ThumbnailGenerator(Path(out_dir) if out_dir else self.destination / "thumbs", size)
        return gen.generate_batch(self.items)

    def search(self, **kw) -> List[MediaItem]:
        self._ensure_loaded()
        res = self.items
        if "extension" in kw:
            e = kw["extension"] if kw["extension"].startswith(".") else f".{kw['extension']}"
            res = [i for i in res if i.extension == e.lower()]
        if "min_size_mb" in kw:
            mn = kw["min_size_mb"] * 1048576
            res = [i for i in res if i.size_bytes >= mn]
        if "camera" in kw:
            c = kw["camera"].lower()
            res = [i for i in res if c in (i.metadata.camera_make or "").lower()]
        return res

    def summary(self) -> str:
        s = self.get_statistics()
        return (f"MediaLibrary: {s['total']} dosya, {s['total_size_mb']}MB\n"
                f"Uzantılar: {s.get('by_extension', {})}\n"
                f"Kameralar: {s.get('by_camera', {})}")

    def _ensure_loaded(self):
        if not self._loaded:
            raise RuntimeError("Önce load() çağırın.")


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    lib = MediaLibrary(source=".", destination="./organized_media")
    count = lib.load()
    print(f"\n{count} medya dosyası bulundu.")
    if count > 0:
        print(lib.summary())
        lib.organize()
        print("Organizasyon tamamlandı!")
