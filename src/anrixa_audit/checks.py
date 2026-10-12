from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ._types import CheckResult


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the lowercase SHA-256 digest for a file without loading it into memory."""

    target = Path(path)
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    digest = hashlib.sha256()
    with target.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def check_hash(path: str | Path, expected_sha256: str) -> CheckResult:
    """Check that ``path`` exists and exactly matches a SHA-256 digest."""

    target = Path(path)
    expected = _normalize_sha256(expected_sha256)
    if not target.is_file():
        return CheckResult(False, actual=None, expected=expected, message=f"file not found: {target}")
    actual = sha256_file(target)
    return CheckResult(actual == expected, actual=actual, expected=expected)


def check_exists(path: str | Path, *, kind: str = "any") -> CheckResult:
    """Check for an existing path, file, or directory."""

    target = Path(path)
    if kind == "any":
        passed = target.exists()
    elif kind == "file":
        passed = target.is_file()
    elif kind == "dir":
        passed = target.is_dir()
    else:
        raise ValueError("kind must be one of: any, file, dir")
    return CheckResult(passed, actual=str(target), expected=f"existing {kind}")


def check_json(path: str | Path) -> CheckResult:
    """Check that a file exists and contains valid JSON."""

    target = Path(path)
    if not target.is_file():
        return CheckResult(False, actual=None, expected="valid JSON", message=f"file not found: {target}")
    try:
        with target.open("r", encoding="utf-8") as handle:
            json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return CheckResult(False, actual=type(exc).__name__, expected="valid JSON", message=str(exc))
    return CheckResult(True, actual="valid JSON", expected="valid JSON")


def check_count(actual: int, expected: int) -> CheckResult:
    return CheckResult(actual == expected, actual=actual, expected=expected)


def check_minimum(actual: int | float, minimum: int | float) -> CheckResult:
    return CheckResult(actual >= minimum, actual=actual, expected=f">={minimum}")


def check_maximum(actual: int | float, maximum: int | float) -> CheckResult:
    return CheckResult(actual <= maximum, actual=actual, expected=f"<={maximum}")


def _normalize_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError("expected_sha256 must be exactly 64 hexadecimal characters")
    return normalized
