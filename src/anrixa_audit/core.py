from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from ._types import CheckResult, GateRecord, GateStatus

Comparator = Callable[[Any, Any], bool]


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Immutable finalized representation of an audit run."""

    name: str
    gates: tuple[GateRecord, ...]
    values: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(gate.status in {GateStatus.PASS, GateStatus.SKIP} for gate in self.gates)

    @property
    def failed(self) -> bool:
        return not self.passed

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1

    @property
    def final_status(self) -> GateStatus:
        return GateStatus.PASS if self.passed else GateStatus.FAIL

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "anrixa.audit.report/v1",
            "name": self.name,
            "status": self.final_status.value,
            "metadata": dict(self.metadata),
            "values": dict(self.values),
            "gates": [gate.to_dict() for gate in self.gates],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False) + "\n"

    def render_text(self, *, include_values: bool = True) -> str:
        lines = [f"AUDIT_RUN={self.name}"]
        if include_values:
            for key, value in self.values.items():
                lines.append(f"{_label(key)}={_format_scalar(value)}")
        for gate in self.gates:
            line = f"{_label(gate.name)}_GATE={gate.status.value}"
            details: list[str] = []
            if gate.actual is not None:
                details.append(f"actual={_format_scalar(gate.actual)}")
            if gate.expected is not None:
                details.append(f"expected={_format_scalar(gate.expected)}")
            if gate.message:
                details.append(f"message={_one_line(gate.message)}")
            if details:
                line += " " + " ".join(details)
            lines.append(line)
        lines.append(f"FINAL_GATE={self.final_status.value}")
        return "\n".join(lines) + "\n"

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8", newline="\n")
        return target

    def write_text(self, path: str | Path, *, include_values: bool = True) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.render_text(include_values=include_values), encoding="utf-8", newline="\n")
        return target


class AuditRun:
    """Collect deterministic values and PASS/FAIL gates for one controlled run.

    ``AuditRun`` intentionally does not hide failures behind logging. Every check becomes an
    explicit record, and ``finalize()`` produces an immutable report that can be rendered as
    human-readable gate lines or serialized as JSON evidence.
    """

    def __init__(
        self,
        name: str,
        *,
        metadata: Mapping[str, Any] | None = None,
        fail_fast: bool = False,
    ) -> None:
        if not name or not name.strip():
            raise ValueError("audit run name must not be empty")
        self.name = name.strip()
        self.metadata = dict(metadata or {})
        self.fail_fast = fail_fast
        self._values: dict[str, Any] = {}
        self._gates: list[GateRecord] = []
        self._report: AuditReport | None = None

    def _ensure_open(self) -> None:
        if self._report is not None:
            raise RuntimeError("audit run is already finalized")

    def record(self, key: str, value: Any) -> "AuditRun":
        self._ensure_open()
        normalized = key.strip()
        if not normalized:
            raise ValueError("record key must not be empty")
        if normalized in self._values:
            raise ValueError(f"record key already exists: {normalized}")
        self._values[normalized] = value
        return self

    def check(
        self,
        name: str,
        result: bool | CheckResult,
        *,
        actual: Any = None,
        expected: Any = None,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> GateRecord:
        self._ensure_open()
        normalized = _validate_gate_name(name)

        if isinstance(result, CheckResult):
            status = GateStatus.PASS if result.passed else GateStatus.FAIL
            record = GateRecord(
                normalized,
                status,
                actual=result.actual,
                expected=result.expected,
                message=result.message,
                metadata=dict(result.metadata),
            )
        else:
            record = GateRecord(
                normalized,
                GateStatus.PASS if result else GateStatus.FAIL,
                actual=actual,
                expected=expected,
                message=message,
                metadata=dict(metadata or {}),
            )

        self._gates.append(record)
        if self.fail_fast and record.status in {GateStatus.FAIL, GateStatus.ERROR}:
            raise AuditGateError(record)
        return record

    def require(
        self,
        name: str,
        *,
        actual: Any,
        expected: Any,
        comparator: Comparator | None = None,
        message: str | None = None,
    ) -> GateRecord:
        compare = comparator or (lambda left, right: left == right)
        try:
            passed = bool(compare(actual, expected))
        except Exception as exc:  # comparator is caller-provided and can fail
            return self.error(name, f"comparator raised {type(exc).__name__}: {exc}", actual=actual, expected=expected)
        return self.check(name, passed, actual=actual, expected=expected, message=message)

    def fail(
        self,
        name: str,
        message: str,
        *,
        actual: Any = None,
        expected: Any = None,
    ) -> GateRecord:
        return self.check(name, False, actual=actual, expected=expected, message=message)

    def error(
        self,
        name: str,
        message: str,
        *,
        actual: Any = None,
        expected: Any = None,
    ) -> GateRecord:
        self._ensure_open()
        record = GateRecord(
            _validate_gate_name(name),
            GateStatus.ERROR,
            actual=actual,
            expected=expected,
            message=message,
        )
        self._gates.append(record)
        if self.fail_fast:
            raise AuditGateError(record)
        return record

    def skip(self, name: str, message: str | None = None) -> GateRecord:
        self._ensure_open()
        record = GateRecord(_validate_gate_name(name), GateStatus.SKIP, message=message)
        self._gates.append(record)
        return record

    def finalize(self) -> AuditReport:
        if self._report is None:
            self._report = AuditReport(
                self.name,
                tuple(self._gates),
                values=dict(self._values),
                metadata=dict(self.metadata),
            )
        return self._report

    def __enter__(self) -> "AuditRun":
        self._ensure_open()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        if exc is not None and not isinstance(exc, AuditGateError) and self._report is None:
            self._gates.append(
                GateRecord(
                    "UNHANDLED_EXCEPTION",
                    GateStatus.ERROR,
                    message=f"{type(exc).__name__}: {exc}",
                )
            )
        self.finalize()
        return False


class AuditGateError(RuntimeError):
    """Raised when ``fail_fast=True`` and a gate does not pass."""

    def __init__(self, gate: GateRecord) -> None:
        self.gate = gate
        super().__init__(f"audit gate {gate.name} ended with {gate.status.value}")


def _validate_gate_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError("gate name must not be empty")
    return normalized


def _label(value: str) -> str:
    chars: list[str] = []
    previous_underscore = False
    for char in value.strip().upper():
        safe = char if char.isalnum() else "_"
        if safe == "_":
            if previous_underscore:
                continue
            previous_underscore = True
        else:
            previous_underscore = False
        chars.append(safe)
    return "".join(chars).strip("_") or "VALUE"


def _one_line(value: str) -> str:
    return " ".join(value.splitlines()).strip()


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _one_line(str(value))
