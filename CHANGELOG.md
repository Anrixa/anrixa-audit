# Changelog

All notable changes to this project will be documented in this file.

The project follows Semantic Versioning.

## [Unreleased]

## [0.1.0] - 2026-10-13

### Added

- `AuditRun`, immutable `AuditReport`, and explicit PASS/FAIL/ERROR/SKIP gate records.
- JSON and plain-text evidence output.
- SHA-256, existence, JSON, count, minimum, and maximum checks.
- Deterministic file-manifest creation and verification.
- Strict manifest mode for unexpected-file detection.
- Command-line interface for hashes and manifests.
- Dependency-free runtime package.
- Test suite, package build checks, CI, and PyPI Trusted Publishing workflow.
