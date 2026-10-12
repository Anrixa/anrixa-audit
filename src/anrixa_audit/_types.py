from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class GateStatus(StrEnum):
    """Normalized status for an audit gate."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIP = "SKIP"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result returned by reusable checks before it is attached to an audit run."""

    passed: bool
    actual: Any = None
    expected: Any = None
    message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GateRecord:
    """One immutable gate result in an :class:`AuditRun`."""

    name: str
    status: GateStatus
    actual: Any = None
    expected: Any = None
    message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status is GateStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "status": self.status.value,
        }
        if self.actual is not None:
            data["actual"] = self.actual
        if self.expected is not None:
            data["expected"] = self.expected
        if self.message:
            data["message"] = self.message
        if self.metadata:
            data["metadata"] = dict(self.metadata)
        return data
