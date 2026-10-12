"""Anrixa Audit: deterministic gates, file integrity checks, and evidence manifests."""

from ._types import CheckResult, GateRecord, GateStatus
from .checks import (
    check_count,
    check_exists,
    check_hash,
    check_json,
    check_maximum,
    check_minimum,
    sha256_file,
)
from .core import AuditGateError, AuditReport, AuditRun
from .manifest import Manifest, ManifestEntry, create_manifest, read_manifest, verify_manifest

__version__ = "0.1.0"

__all__ = [
    "AuditGateError",
    "AuditReport",
    "AuditRun",
    "CheckResult",
    "GateRecord",
    "GateStatus",
    "Manifest",
    "ManifestEntry",
    "check_count",
    "check_exists",
    "check_hash",
    "check_json",
    "check_maximum",
    "check_minimum",
    "create_manifest",
    "read_manifest",
    "sha256_file",
    "verify_manifest",
]
