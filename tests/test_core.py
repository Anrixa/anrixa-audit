from __future__ import annotations

import json

import pytest

from anrixa_audit import AuditGateError, AuditRun, CheckResult, GateStatus


def test_empty_run_passes() -> None:
    report = AuditRun("empty").finalize()
    assert report.passed
    assert report.exit_code == 0
    assert report.final_status is GateStatus.PASS


def test_record_and_check_render_text() -> None:
    run = AuditRun("dataset-build")
    run.record("source", "gold100k")
    run.check("MANIFEST", True)
    report = run.finalize()
    assert report.render_text() == (
        "AUDIT_RUN=dataset-build\n"
        "SOURCE=gold100k\n"
        "MANIFEST_GATE=PASS\n"
        "FINAL_GATE=PASS\n"
    )


def test_failed_gate_fails_report() -> None:
    run = AuditRun("x")
    run.check("row-count", False, actual=99, expected=100)
    report = run.finalize()
    assert report.failed
    assert report.exit_code == 1
    assert "ROW_COUNT_GATE=FAIL actual=99 expected=100" in report.render_text()


def test_check_result_is_preserved() -> None:
    result = CheckResult(False, actual="abc", expected="def", message="mismatch", metadata={"kind": "hash"})
    run = AuditRun("x")
    gate = run.check("sha", result)
    assert gate.actual == "abc"
    assert gate.expected == "def"
    assert gate.message == "mismatch"
    assert gate.metadata == {"kind": "hash"}


def test_require_default_equality() -> None:
    run = AuditRun("x")
    run.require("COUNT", actual=5, expected=5)
    assert run.finalize().passed


def test_require_custom_comparator() -> None:
    run = AuditRun("x")
    run.require("MIN", actual=5, expected=3, comparator=lambda actual, minimum: actual >= minimum)
    assert run.finalize().passed


def test_require_comparator_exception_is_error_gate() -> None:
    run = AuditRun("x")
    gate = run.require("BAD", actual=1, expected=2, comparator=lambda *_: 1 / 0)
    assert gate.status is GateStatus.ERROR
    assert "ZeroDivisionError" in (gate.message or "")
    assert run.finalize().failed


def test_skip_does_not_fail_report() -> None:
    run = AuditRun("x")
    run.skip("OPTIONAL", "not requested")
    report = run.finalize()
    assert report.passed
    assert "OPTIONAL_GATE=SKIP message=not requested" in report.render_text()


def test_error_fails_report() -> None:
    run = AuditRun("x")
    run.error("IO", "disk error")
    assert run.finalize().failed


def test_fail_fast_raises() -> None:
    run = AuditRun("x", fail_fast=True)
    with pytest.raises(AuditGateError) as caught:
        run.check("NO", False)
    assert caught.value.gate.name == "NO"


def test_duplicate_record_is_rejected() -> None:
    run = AuditRun("x")
    run.record("a", 1)
    with pytest.raises(ValueError, match="already exists"):
        run.record("a", 2)


def test_mutation_after_finalize_is_rejected() -> None:
    run = AuditRun("x")
    run.finalize()
    with pytest.raises(RuntimeError, match="already finalized"):
        run.record("a", 1)


def test_finalize_is_idempotent() -> None:
    run = AuditRun("x")
    first = run.finalize()
    second = run.finalize()
    assert first is second


def test_context_manager_records_unhandled_exception() -> None:
    run = AuditRun("x")
    with pytest.raises(RuntimeError, match="boom"):
        with run:
            raise RuntimeError("boom")
    report = run.finalize()
    assert report.failed
    assert report.gates[-1].name == "UNHANDLED_EXCEPTION"
    assert report.gates[-1].status is GateStatus.ERROR


def test_json_schema_and_unicode() -> None:
    run = AuditRun("审计", metadata={"owner": "Anrixa"})
    run.record("语言", "中文")
    run.check("完整性", True)
    data = json.loads(run.finalize().to_json())
    assert data["schema"] == "anrixa.audit.report/v1"
    assert data["name"] == "审计"
    assert data["values"]["语言"] == "中文"


def test_write_outputs(tmp_path) -> None:
    report = AuditRun("x").finalize()
    json_path = report.write_json(tmp_path / "evidence" / "report.json")
    text_path = report.write_text(tmp_path / "evidence" / "report.txt")
    assert json_path.read_text(encoding="utf-8").endswith("\n")
    assert text_path.read_text(encoding="utf-8") == "AUDIT_RUN=x\nFINAL_GATE=PASS\n"


def test_invalid_names_are_rejected() -> None:
    with pytest.raises(ValueError):
        AuditRun("   ")
    run = AuditRun("x")
    with pytest.raises(ValueError):
        run.check("   ", True)
