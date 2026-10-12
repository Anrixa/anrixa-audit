from __future__ import annotations

import hashlib
import json

import pytest

from anrixa_audit import (
    check_count,
    check_exists,
    check_hash,
    check_json,
    check_maximum,
    check_minimum,
    sha256_file,
)


def test_sha256_file(tmp_path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"anrixa")
    assert sha256_file(path) == hashlib.sha256(b"anrixa").hexdigest()


def test_sha256_chunk_size_validation(tmp_path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"x")
    with pytest.raises(ValueError, match="chunk_size"):
        sha256_file(path, chunk_size=0)


def test_check_hash_pass_and_fail(tmp_path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc")
    digest = hashlib.sha256(b"abc").hexdigest()
    assert check_hash(path, digest.upper()).passed
    failed = check_hash(path, "0" * 64)
    assert not failed.passed
    assert failed.actual == digest


def test_check_hash_missing_file(tmp_path) -> None:
    result = check_hash(tmp_path / "missing", "0" * 64)
    assert not result.passed
    assert "file not found" in (result.message or "")


def test_check_hash_rejects_invalid_digest(tmp_path) -> None:
    with pytest.raises(ValueError, match="64 hexadecimal"):
        check_hash(tmp_path / "x", "xyz")


def test_check_exists_kinds(tmp_path) -> None:
    file_path = tmp_path / "f"
    file_path.write_text("x", encoding="utf-8")
    dir_path = tmp_path / "d"
    dir_path.mkdir()
    assert check_exists(file_path).passed
    assert check_exists(file_path, kind="file").passed
    assert check_exists(dir_path, kind="dir").passed
    assert not check_exists(file_path, kind="dir").passed
    with pytest.raises(ValueError):
        check_exists(file_path, kind="socket")


def test_check_json(tmp_path) -> None:
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"ok": True}), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert check_json(good).passed
    assert not check_json(bad).passed
    assert not check_json(tmp_path / "missing.json").passed


def test_numeric_checks() -> None:
    assert check_count(4, 4).passed
    assert not check_count(4, 5).passed
    assert check_minimum(4, 3).passed
    assert not check_minimum(2, 3).passed
    assert check_maximum(4, 5).passed
    assert not check_maximum(6, 5).passed
