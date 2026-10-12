# anrixa-audit

Deterministic audit gates, SHA-256 evidence, and file manifests for controlled Python workflows.

`anrixa-audit` is deliberately small and dependency-free at runtime. It provides explicit PASS/FAIL evidence for data pipelines, build systems, release gates, model/data preparation, and other workflows where a log line is not enough and silent assumptions are undesirable.

## Install

```bash
pip install anrixa-audit
```

Python 3.10+ is supported.

## Why this package exists

Many pipelines answer important questions implicitly:

- Did the expected file actually arrive?
- Does its hash match the approved artifact?
- Did the row count change?
- Is a generated manifest still valid?
- Can a failed validation be represented as durable evidence rather than only a console message?

`anrixa-audit` makes those checks explicit and serializable.

## Quick start

```python
from anrixa_audit import AuditRun, check_hash

with AuditRun("dataset-build") as audit:
    audit.record("dataset", "gold100k")
    audit.check(
        "MANIFEST",
        check_hash(
            "manifest.json",
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        ),
    )
    audit.require("ROW_COUNT", actual=99_400, expected=99_400)

report = audit.finalize()
print(report.render_text(), end="")
report.write_json("evidence/audit.json")
```

Output is intentionally simple:

```text
AUDIT_RUN=dataset-build
DATASET=gold100k
MANIFEST_GATE=PASS actual=012345... expected=012345...
ROW_COUNT_GATE=PASS actual=99400 expected=99400
FINAL_GATE=PASS
```

A failed or error gate makes the final report fail and gives `report.exit_code == 1`.

## Reusable checks

```python
from anrixa_audit import (
    check_count,
    check_exists,
    check_hash,
    check_json,
    check_maximum,
    check_minimum,
    sha256_file,
)
```

All checks return a `CheckResult`, which can be attached directly to an `AuditRun`.

```python
from anrixa_audit import AuditRun, check_minimum

run = AuditRun("qualification")
run.check("COVERAGE", check_minimum(0.992, 0.99))
report = run.finalize()
```

## File manifests

Create a deterministic manifest:

```python
from anrixa_audit import create_manifest

manifest = create_manifest(
    "dataset",
    exclude=["*.tmp", "runtime/**"],
    metadata={"dataset": "example-v1"},
)
manifest.write("dataset.manifest.json")
```

The file list is sorted and every regular file contains its byte size and SHA-256 digest.

Verify it later:

```python
from anrixa_audit import verify_manifest

report = verify_manifest(
    "dataset.manifest.json",
    "dataset",
    strict=True,
    exclude=["runtime/**"],
)

if report.failed:
    raise SystemExit(report.render_text())
```

`strict=True` additionally fails when unmanifested files are present.

## CLI

Hash files:

```bash
anrixa-audit hash data.bin model.json
```

Verify one known artifact:

```bash
anrixa-audit check-hash artifact.tar.zst <expected-sha256>
```

Create a manifest:

```bash
anrixa-audit manifest create ./dataset -o dataset.manifest.json \
  --exclude '*.tmp' \
  --exclude 'runtime/**'
```

Verify it:

```bash
anrixa-audit manifest verify dataset.manifest.json --root ./dataset --strict
```

Add `--json` to hash or manifest verification commands when machine-readable evidence is preferred.

## Evidence model

Reports use a small stable JSON envelope:

```json
{
  "schema": "anrixa.audit.report/v1",
  "name": "dataset-build",
  "status": "PASS",
  "metadata": {},
  "values": {},
  "gates": [
    {
      "name": "ROW_COUNT",
      "status": "PASS",
      "actual": 99400,
      "expected": 99400
    }
  ]
}
```

Manifests use `anrixa.audit.manifest/v1`.

The v1 schemas are intentionally straightforward so evidence can be inspected without this package.

## Design principles

- **Fail explicitly.** A failed assumption becomes a failed gate.
- **No runtime dependencies.** Integrity checks should not pull in a large dependency graph.
- **Stable evidence.** Reports can be written as plain text or JSON.
- **Streaming hashes.** Large files are hashed without loading them fully into memory.
- **Safe manifests.** Manifest paths cannot escape the declared root.
- **No hidden network activity.** The library only inspects local values and files supplied by the caller.

See [docs/DESIGN.md](docs/DESIGN.md) for the package boundaries and non-goals.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
python -m pytest
python -m build
python -m twine check dist/*
```

## Publishing

The repository includes a GitHub Actions release workflow designed for PyPI Trusted Publishing. No long-lived PyPI API token is required in GitHub secrets.

Before the first release, configure a PyPI Trusted Publisher for:

- owner: `Anrixa`
- repository: `anrixa-audit`
- workflow: `release.yml`
- environment: `pypi`

Then create a GitHub Release for a version tag such as `v0.1.0`.

## Security

Do not report vulnerabilities through a public issue. See [SECURITY.md](SECURITY.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).

---

Built by [Anrixa](https://anrixa.com/) — **Intelligence, Evolved.**
