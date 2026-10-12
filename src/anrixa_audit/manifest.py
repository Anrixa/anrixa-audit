from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

from .checks import sha256_file
from .core import AuditReport, AuditRun

MANIFEST_SCHEMA = "anrixa.audit.manifest/v1"
DEFAULT_EXCLUDES = (".git", ".git/**", "__pycache__", "**/__pycache__/**")


@dataclass(frozen=True, slots=True, order=True)
class ManifestEntry:
    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class Manifest:
    entries: tuple[ManifestEntry, ...]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": MANIFEST_SCHEMA,
            "metadata": dict(self.metadata),
            "files": [entry.to_dict() for entry in self.entries],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False) + "\n"

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8", newline="\n")
        return target


def create_manifest(
    root: str | Path,
    *,
    exclude: Sequence[str] = (),
    include_hidden: bool = True,
    metadata: dict[str, Any] | None = None,
) -> Manifest:
    """Create a sorted SHA-256 manifest for all regular files under ``root``."""

    base = Path(root).resolve()
    if not base.is_dir():
        raise NotADirectoryError(base)

    patterns = tuple(DEFAULT_EXCLUDES) + tuple(exclude)
    entries: list[ManifestEntry] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(base).as_posix()
        if not include_hidden and any(part.startswith(".") for part in Path(relative).parts):
            continue
        if _matches_any(relative, patterns):
            continue
        entries.append(ManifestEntry(relative, path.stat().st_size, sha256_file(path)))

    manifest_metadata = dict(metadata or {})
    manifest_metadata.setdefault("root_name", base.name)
    return Manifest(tuple(entries), manifest_metadata)


def read_manifest(path: str | Path) -> Manifest:
    target = Path(path)
    with target.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict) or data.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"unsupported manifest schema in {target}")
    raw_files = data.get("files")
    if not isinstance(raw_files, list):
        raise ValueError("manifest files must be a list")

    entries: list[ManifestEntry] = []
    seen: set[str] = set()
    for item in raw_files:
        if not isinstance(item, dict):
            raise ValueError("manifest file entry must be an object")
        relative = _safe_relative_path(item.get("path"))
        if relative in seen:
            raise ValueError(f"duplicate manifest path: {relative}")
        seen.add(relative)
        size = item.get("size")
        digest = item.get("sha256")
        if not isinstance(size, int) or size < 0:
            raise ValueError(f"invalid size for {relative}")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
            raise ValueError(f"invalid sha256 for {relative}")
        entries.append(ManifestEntry(relative, size, digest.lower()))

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("manifest metadata must be an object")
    return Manifest(tuple(sorted(entries)), dict(metadata))


def verify_manifest(
    manifest: Manifest | str | Path,
    root: str | Path,
    *,
    strict: bool = False,
    exclude: Sequence[str] = (),
) -> AuditReport:
    """Verify file presence, byte size, and SHA-256 for a manifest.

    In ``strict`` mode, the verifier additionally fails when an unmanifested regular file is
    present under ``root`` after applying the same exclusion patterns.
    """

    loaded = read_manifest(manifest) if isinstance(manifest, (str, Path)) else manifest
    base = Path(root).resolve()
    if not base.is_dir():
        raise NotADirectoryError(base)

    run = AuditRun("manifest-verify", metadata={"root": str(base), "strict": strict})
    run.record("manifest_files", len(loaded.entries))

    expected_paths = {entry.path for entry in loaded.entries}
    for entry in loaded.entries:
        target = base / Path(entry.path)
        gate = f"FILE:{entry.path}"
        if not target.is_file() or target.is_symlink():
            run.fail(gate, "file missing or not a regular file", actual=None, expected=entry.sha256)
            continue
        actual_size = target.stat().st_size
        if actual_size != entry.size:
            run.fail(gate, "file size mismatch", actual=actual_size, expected=entry.size)
            continue
        actual_hash = sha256_file(target)
        run.check(gate, actual_hash == entry.sha256, actual=actual_hash, expected=entry.sha256)

    if strict:
        patterns = tuple(DEFAULT_EXCLUDES) + tuple(exclude)
        actual_paths = {
            path.relative_to(base).as_posix()
            for path in base.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and not _matches_any(path.relative_to(base).as_posix(), patterns)
        }
        unexpected = sorted(actual_paths - expected_paths)
        run.check(
            "UNEXPECTED_FILES",
            not unexpected,
            actual=unexpected,
            expected=[],
            message=None if not unexpected else "unmanifested files are present",
        )

    return run.finalize()


def _matches_any(relative: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("manifest path must be a non-empty string")
    if "\\" in value:
        raise ValueError(f"manifest path must use POSIX separators: {value}")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"manifest path escapes root: {value}")
    normalized = candidate.as_posix()
    if normalized in {"", "."}:
        raise ValueError("manifest path must name a file")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized
