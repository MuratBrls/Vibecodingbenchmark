from __future__ import annotations

import dataclasses
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Optional


class LocalOptimizerError(Exception):
    """Base error for LocalOptimizer."""


class PermissionError(LocalOptimizerError):
    """Raised when required filesystem permissions are missing."""


class OptimizationError(LocalOptimizerError):
    """Raised when an optimization step fails."""


@dataclass(frozen=True)
class OptimizationResult:
    scanned_files: int
    total_bytes: int
    deleted_files: int
    elapsed_ms: float
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalOptimizerConfig:
    target_dir: Path
    dry_run: bool = False
    include_hidden: bool = False
    delete_patterns: tuple[str, ...] = (".tmp", ".bak", ".log", ".DS_Store", "Thumbs.db")
    max_delete_bytes: Optional[int] = None


class LocalOptimizer:
    """
    Advanced local filesystem optimizer (OOP + logging):
    - Scans a directory tree
    - Optionally deletes common junk files (configurable)
    - Performs explicit permission checks and defensive try/except around IO
    - Measures elapsed time via perf_counter with millisecond resolution
    """

    def __init__(self, config: LocalOptimizerConfig, logger: Optional[logging.Logger] = None) -> None:
        self.config = config
        self.log = logger or logging.getLogger(self.__class__.__name__)

    def _check_dir(self, p: Path) -> None:
        try:
            if not p.exists():
                raise FileNotFoundError(str(p))
            if not p.is_dir():
                raise NotADirectoryError(str(p))
        except Exception as e:
            raise OptimizationError(f"Invalid target directory: {p} ({e})") from e

    def _check_read(self, p: Path) -> None:
        try:
            if not os.access(p, os.R_OK):
                raise PermissionError(f"No read access: {p}")
        except LocalOptimizerError:
            raise
        except Exception as e:
            raise PermissionError(f"Read permission check failed: {p} ({e})") from e

    def _check_write_parent(self, p: Path) -> None:
        try:
            parent = p.parent
            if not os.access(parent, os.W_OK):
                raise PermissionError(f"No write access to parent directory: {parent}")
        except LocalOptimizerError:
            raise
        except Exception as e:
            raise PermissionError(f"Write permission check failed: {p} ({e})") from e

    def _is_hidden(self, p: Path) -> bool:
        return p.name.startswith(".")

    def iter_files(self) -> Iterable[Path]:
        root = self.config.target_dir
        self._check_dir(root)
        self._check_read(root)

        try:
            for fp in root.rglob("*"):
                if not fp.is_file():
                    continue
                if not self.config.include_hidden and self._is_hidden(fp):
                    continue
                yield fp
        except LocalOptimizerError:
            raise
        except Exception as e:
            raise OptimizationError(f"Failed while scanning {root}: {e}") from e

    def _matches_delete_pattern(self, fp: Path) -> bool:
        name = fp.name
        suffix = fp.suffix.lower()
        for pat in self.config.delete_patterns:
            pat_l = pat.lower()
            if pat_l.startswith("."):
                if suffix == pat_l:
                    return True
            else:
                if name.lower() == pat_l:
                    return True
        return False

    def plan_deletions(self, files: Iterable[Path]) -> list[Path]:
        plan: list[Path] = []
        total_planned_bytes = 0

        for fp in files:
            try:
                if not self._matches_delete_pattern(fp):
                    continue

                st = fp.stat()
                if self.config.max_delete_bytes is not None and (total_planned_bytes + st.st_size) > self.config.max_delete_bytes:
                    continue

                plan.append(fp)
                total_planned_bytes += st.st_size
            except Exception as e:
                self.log.warning("Skipping file during planning %s (%s)", fp, e)
                continue

        return plan

    def execute_deletions(self, plan: Iterable[Path]) -> int:
        deleted = 0
        for fp in plan:
            try:
                self._check_write_parent(fp)
                if self.config.dry_run:
                    self.log.info("[dry-run] delete %s", fp)
                    deleted += 1
                    continue
                fp.unlink()
                deleted += 1
            except LocalOptimizerError as e:
                self.log.error("Delete blocked %s (%s)", fp, e)
            except Exception as e:
                self.log.error("Delete failed %s (%s)", fp, e)
        return deleted

    def optimize(self) -> OptimizationResult:
        start = perf_counter()
        scanned_files = 0
        total_bytes = 0
        notes: list[str] = []

        try:
            files = list(self.iter_files())
            for fp in files:
                try:
                    st = fp.stat()
                    scanned_files += 1
                    total_bytes += st.st_size
                except Exception:
                    scanned_files += 1
                    continue

            deletion_plan = self.plan_deletions(files)
            if deletion_plan:
                notes.append(f"planned_deletions={len(deletion_plan)}")
            deleted_files = self.execute_deletions(deletion_plan)
        except LocalOptimizerError:
            raise
        except Exception as e:
            raise OptimizationError(f"Optimization failed: {e}") from e
        finally:
            elapsed_ms = (perf_counter() - start) * 1000.0

        self.log.info(
            "optimize done scanned=%s bytes=%s deleted=%s elapsed_ms=%.3f",
            scanned_files,
            total_bytes,
            deleted_files,
            elapsed_ms,
        )
        return OptimizationResult(
            scanned_files=scanned_files,
            total_bytes=total_bytes,
            deleted_files=deleted_files,
            elapsed_ms=elapsed_ms,
            notes=tuple(notes),
        )


def _default_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def optimize_directory(
    target_dir: str | Path,
    *,
    dry_run: bool = False,
    include_hidden: bool = False,
    logger: Optional[logging.Logger] = None,
) -> OptimizationResult:
    _default_logging()
    cfg = LocalOptimizerConfig(
        target_dir=Path(target_dir).expanduser().resolve(),
        dry_run=dry_run,
        include_hidden=include_hidden,
    )
    return LocalOptimizer(cfg, logger=logger).optimize()

