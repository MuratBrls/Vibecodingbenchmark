from __future__ import annotations

import dataclasses
import enum
import hashlib
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence


class MediaOrganizerError(Exception):
    """Base error for media organizer."""


class PermissionCheckError(MediaOrganizerError):
    """Raised when a required permission is missing."""


class ScanError(MediaOrganizerError):
    """Raised when scanning fails."""


class PlanningError(MediaOrganizerError):
    """Raised when planning output paths fails."""


class ExecutionError(MediaOrganizerError):
    """Raised when executing a filesystem operation fails."""


class MediaType(str, enum.Enum):
    PHOTO = "photo"
    VIDEO = "video"
    OTHER = "other"


class OrganizationScheme(str, enum.Enum):
    BY_TYPE = "type"
    BY_DATE = "date"
    BY_TYPE_AND_DATE = "type+date"


class Operation(str, enum.Enum):
    COPY = "copy"
    MOVE = "move"


PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".webm", ".m4v"}


@dataclass(frozen=True)
class MediaFile:
    path: Path
    media_type: MediaType
    size_bytes: int
    mtime: float
    sha256: Optional[str] = None


@dataclass(frozen=True)
class PlannedOperation:
    op: Operation
    src: Path
    dest: Path
    reason: str


@dataclass
class OrganizerReport:
    planned: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = dataclasses.field(default_factory=list)


@dataclass(frozen=True)
class MediaOrganizerConfig:
    source_dir: Path
    destination_dir: Path
    scheme: OrganizationScheme = OrganizationScheme.BY_TYPE_AND_DATE
    operation: Operation = Operation.COPY
    dry_run: bool = False
    include_hidden: bool = False
    detect_duplicates: bool = True
    allowed_extensions: Optional[set[str]] = None  # None -> accept all


class MediaOrganizer:
    """
    Advanced OOP media organizer with:
    - Defensive try/except around IO
    - Permission checks (read/write)
    - Duplicate detection (SHA-256)
    - Collision-resistant destination naming
    """

    def __init__(self, config: MediaOrganizerConfig, logger: Optional[logging.Logger] = None) -> None:
        self.config = config
        self.log = logger or logging.getLogger(self.__class__.__name__)

    # -------------------------
    # Permission / safety checks
    # -------------------------
    def _require_dir(self, p: Path, *, purpose: str) -> None:
        try:
            if not p.exists():
                raise FileNotFoundError(str(p))
            if not p.is_dir():
                raise NotADirectoryError(str(p))
        except Exception as e:
            raise PermissionCheckError(f"{purpose} directory invalid: {p} ({e})") from e

    def _check_read_access(self, p: Path) -> None:
        try:
            if not os.access(p, os.R_OK):
                raise PermissionError(f"No read access: {p}")
        except Exception as e:
            raise PermissionCheckError(str(e)) from e

    def _check_write_access(self, p: Path) -> None:
        try:
            if p.exists():
                if not os.access(p, os.W_OK):
                    raise PermissionError(f"No write access: {p}")
            else:
                parent = p.parent
                if not os.access(parent, os.W_OK):
                    raise PermissionError(f"No write access to parent dir: {parent}")
        except Exception as e:
            raise PermissionCheckError(str(e)) from e

    # -------------------------
    # Helpers
    # -------------------------
    def _classify(self, path: Path) -> MediaType:
        ext = path.suffix.lower()
        if ext in PHOTO_EXTS:
            return MediaType.PHOTO
        if ext in VIDEO_EXTS:
            return MediaType.VIDEO
        return MediaType.OTHER

    def _should_include(self, path: Path) -> bool:
        if not self.config.include_hidden and path.name.startswith("."):
            return False
        if self.config.allowed_extensions is None:
            return True
        allowed = {e.lower() for e in self.config.allowed_extensions}
        return path.suffix.lower() in allowed

    def _date_folder(self, mtime: float) -> str:
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    def compute_sha256(self, path: Path, *, chunk_size: int = 1024 * 1024) -> str:
        self._check_read_access(path)
        h = hashlib.sha256()
        try:
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            raise ScanError(f"Failed hashing {path}: {e}") from e

    # -------------------------
    # Scan
    # -------------------------
    def scan(self) -> Iterator[MediaFile]:
        src = self.config.source_dir
        self._require_dir(src, purpose="source")
        self._check_read_access(src)

        try:
            for p in src.rglob("*"):
                if not p.is_file():
                    continue
                if not self._should_include(p):
                    continue
                try:
                    st = p.stat()
                    yield MediaFile(
                        path=p,
                        media_type=self._classify(p),
                        size_bytes=st.st_size,
                        mtime=st.st_mtime,
                        sha256=self.compute_sha256(p) if self.config.detect_duplicates else None,
                    )
                except PermissionCheckError:
                    raise
                except Exception as e:
                    self.log.warning("Skipping unreadable file %s (%s)", p, e)
        except PermissionCheckError:
            raise
        except Exception as e:
            raise ScanError(f"Scan failed for {src}: {e}") from e

    # -------------------------
    # Plan
    # -------------------------
    def _build_destination(self, mf: MediaFile) -> Path:
        root = self.config.destination_dir
        name = mf.path.name
        if self.config.scheme == OrganizationScheme.BY_TYPE:
            return root / mf.media_type.value / name
        if self.config.scheme == OrganizationScheme.BY_DATE:
            return root / self._date_folder(mf.mtime) / name
        return root / mf.media_type.value / self._date_folder(mf.mtime) / name

    def plan(self, files: Iterable[MediaFile]) -> list[PlannedOperation]:
        planned: list[PlannedOperation] = []
        seen: set[str] = set()

        for mf in files:
            try:
                if mf.sha256 and mf.sha256 in seen:
                    planned.append(
                        PlannedOperation(
                            op=self.config.operation,
                            src=mf.path,
                            dest=self._build_destination(mf),
                            reason="duplicate_detected_skip",
                        )
                    )
                    continue
                if mf.sha256:
                    seen.add(mf.sha256)

                planned.append(
                    PlannedOperation(
                        op=self.config.operation,
                        src=mf.path,
                        dest=self._build_destination(mf),
                        reason="organize",
                    )
                )
            except Exception as e:
                raise PlanningError(f"Planning failed for {mf.path}: {e}") from e

        return planned

    # -------------------------
    # Execute
    # -------------------------
    def _ensure_parent_dir(self, p: Path) -> None:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ExecutionError(f"Failed creating parent directory for {p}: {e}") from e

    def _resolve_collision(self, dest: Path) -> Path:
        if not dest.exists():
            return dest
        stem, suffix, parent = dest.stem, dest.suffix, dest.parent
        for i in range(1, 10_000):
            candidate = parent / f"{stem} ({i}){suffix}"
            if not candidate.exists():
                return candidate
        raise ExecutionError(f"Too many name collisions for {dest}")

    def execute(self, plan: Sequence[PlannedOperation]) -> OrganizerReport:
        report = OrganizerReport(planned=len(plan))

        try:
            self.config.destination_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ExecutionError(f"Cannot create destination root {self.config.destination_dir}: {e}") from e

        for item in plan:
            if item.reason == "duplicate_detected_skip":
                report.skipped += 1
                continue

            try:
                self._check_read_access(item.src)
                self._ensure_parent_dir(item.dest)
                self._check_write_access(item.dest)

                final_dest = self._resolve_collision(item.dest)
                if self.config.dry_run:
                    report.succeeded += 1
                    continue

                if item.op == Operation.COPY:
                    shutil.copy2(item.src, final_dest)
                else:
                    shutil.move(str(item.src), str(final_dest))

                report.succeeded += 1
            except PermissionCheckError as e:
                report.failed += 1
                report.errors.append(f"Permission error: {e}")
            except Exception as e:
                report.failed += 1
                report.errors.append(f"Failed {item.op.value} {item.src} -> {item.dest}: {e}")

        return report

    def organize(self) -> OrganizerReport:
        files = list(self.scan())
        plan = self.plan(files)
        return self.execute(plan)

