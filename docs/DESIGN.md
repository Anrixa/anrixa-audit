# Design

## Scope

`anrixa-audit` is a local evidence and integrity library. It does not attempt to become a workflow engine, policy language, provenance database, or remote attestation service.

The package has four layers:

1. **Result types** — immutable gate/check records.
2. **Audit runs** — ordered values and gates with explicit final status.
3. **Checks** — small reusable local validators.
4. **Manifests** — deterministic inventories of regular files with size and SHA-256 evidence.

The CLI is a thin interface over these APIs.

## Status semantics

A gate has one of four states:

- `PASS` — the asserted condition is true.
- `FAIL` — the asserted condition is false.
- `ERROR` — the check itself could not be evaluated correctly.
- `SKIP` — the gate was intentionally not evaluated.

An audit report passes only when every gate is `PASS` or `SKIP`.

## Determinism

The evidence format avoids automatic timestamps and host-specific IDs. Callers may add such information through report metadata when it is useful. This keeps identical logical audits serializable to identical JSON, assuming the caller supplies identical values in the same order.

## Manifest security

Manifest paths are relative and rejected if they contain `..` or are absolute. Symbolic links are not included in generated manifests and do not satisfy manifest verification entries. These rules keep verification scoped to the declared root instead of silently following filesystem references elsewhere.

## Non-goals

The package does not:

- sign manifests cryptographically;
- contact transparency logs;
- upload evidence;
- manage secrets;
- replace SBOM formats;
- infer approval or authorization from a PASS result;
- execute arbitrary policy code from manifest files.

Higher-level Anrixa packages may build on these primitives later.
