from __future__ import annotations

import hashlib
import json

from anrixa_audit.cli import main


def test_cli_hash(tmp_path, capsys) -> None:
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    code = main(["hash", str(path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith(hashlib.sha256(b"abc").hexdigest())


def test_cli_check_hash_exit_codes(tmp_path, capsys) -> None:
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    good = hashlib.sha256(b"abc").hexdigest()
    assert main(["check-hash", str(path), good]) == 0
    assert "FINAL_GATE=PASS" in capsys.readouterr().out
    assert main(["check-hash", str(path), "0" * 64]) == 1
    assert "FINAL_GATE=FAIL" in capsys.readouterr().out


def test_cli_check_hash_json(tmp_path, capsys) -> None:
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    good = hashlib.sha256(b"abc").hexdigest()
    assert main(["check-hash", str(path), good, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "PASS"


def test_cli_manifest_round_trip(tmp_path, capsys) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "x.txt").write_text("hello", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    assert main(["manifest", "create", str(root), "-o", str(manifest)]) == 0
    assert "MANIFEST_CREATE_GATE=PASS" in capsys.readouterr().out
    assert main(["manifest", "verify", str(manifest), "--root", str(root)]) == 0
    assert "FINAL_GATE=PASS" in capsys.readouterr().out


def test_cli_reports_input_error(tmp_path, capsys) -> None:
    code = main(["hash", str(tmp_path / "missing")])
    err = capsys.readouterr().err
    assert code == 2
    assert err.startswith("ERROR:")
