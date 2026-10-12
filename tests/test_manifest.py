from __future__ import annotations

import json

import pytest

from anrixa_audit import create_manifest, read_manifest, verify_manifest
from anrixa_audit.manifest import MANIFEST_SCHEMA


def test_manifest_creation_is_sorted_and_hashed(tmp_path) -> None:
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    manifest = create_manifest(tmp_path)
    assert [entry.path for entry in manifest.entries] == ["a.txt", "b.txt"]
    assert all(len(entry.sha256) == 64 for entry in manifest.entries)
    assert manifest.metadata["root_name"] == tmp_path.name


def test_manifest_ignores_git_by_default(tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret-ish", encoding="utf-8")
    (tmp_path / "file.txt").write_text("ok", encoding="utf-8")
    manifest = create_manifest(tmp_path)
    assert [entry.path for entry in manifest.entries] == ["file.txt"]


def test_manifest_exclude_and_hidden_controls(tmp_path) -> None:
    (tmp_path / "keep.txt").write_text("k", encoding="utf-8")
    (tmp_path / "skip.log").write_text("s", encoding="utf-8")
    (tmp_path / ".hidden").write_text("h", encoding="utf-8")
    manifest = create_manifest(tmp_path, exclude=["*.log"], include_hidden=False)
    assert [entry.path for entry in manifest.entries] == ["keep.txt"]


def test_manifest_write_and_read(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "x").write_text("x", encoding="utf-8")
    manifest = create_manifest(root, metadata={"dataset": "demo"})
    path = manifest.write(tmp_path / "manifest.json")
    loaded = read_manifest(path)
    assert loaded == manifest
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == MANIFEST_SCHEMA


def test_verify_manifest_passes(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "x.txt").write_text("hello", encoding="utf-8")
    manifest = create_manifest(root)
    report = verify_manifest(manifest, root)
    assert report.passed
    assert report.values["manifest_files"] == 1


def test_verify_manifest_detects_hash_change(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "x.txt"
    target.write_text("one", encoding="utf-8")
    manifest = create_manifest(root)
    target.write_text("two", encoding="utf-8")
    report = verify_manifest(manifest, root)
    assert report.failed
    assert report.gates[0].name == "FILE:x.txt"


def test_verify_manifest_detects_size_change_before_hash(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "x.txt"
    target.write_text("a", encoding="utf-8")
    manifest = create_manifest(root)
    target.write_text("longer", encoding="utf-8")
    gate = verify_manifest(manifest, root).gates[0]
    assert gate.message == "file size mismatch"


def test_verify_manifest_detects_missing_file(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "x.txt"
    target.write_text("x", encoding="utf-8")
    manifest = create_manifest(root)
    target.unlink()
    report = verify_manifest(manifest, root)
    assert report.failed
    assert "missing" in (report.gates[0].message or "")


def test_strict_manifest_detects_unexpected_file(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "x.txt").write_text("x", encoding="utf-8")
    manifest = create_manifest(root)
    (root / "y.txt").write_text("y", encoding="utf-8")
    report = verify_manifest(manifest, root, strict=True)
    assert report.failed
    unexpected = [gate for gate in report.gates if gate.name == "UNEXPECTED_FILES"][0]
    assert unexpected.actual == ["y.txt"]


def test_strict_manifest_can_exclude_unexpected_file(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "x.txt").write_text("x", encoding="utf-8")
    manifest = create_manifest(root)
    (root / "runtime.log").write_text("log", encoding="utf-8")
    report = verify_manifest(manifest, root, strict=True, exclude=["*.log"])
    assert report.passed


def test_read_manifest_rejects_escape_path(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": MANIFEST_SCHEMA,
                "metadata": {},
                "files": [{"path": "../escape", "size": 0, "sha256": "0" * 64}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="escapes root"):
        read_manifest(manifest_path)


def test_read_manifest_rejects_duplicates(tmp_path) -> None:
    item = {"path": "x", "size": 0, "sha256": "0" * 64}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema": MANIFEST_SCHEMA, "metadata": {}, "files": [item, item]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        read_manifest(path)


def test_create_manifest_requires_directory(tmp_path) -> None:
    file_path = tmp_path / "x"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        create_manifest(file_path)
