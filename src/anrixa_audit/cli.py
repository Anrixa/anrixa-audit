from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .checks import check_hash, sha256_file
from .core import AuditRun
from .manifest import create_manifest, verify_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anrixa-audit",
        description="Deterministic audit gates, SHA-256 evidence, and file manifests.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    hash_parser = sub.add_parser("hash", help="print SHA-256 hashes for files")
    hash_parser.add_argument("files", nargs="+", type=Path)
    hash_parser.set_defaults(handler=_cmd_hash)

    check_parser = sub.add_parser("check-hash", help="verify one file against an expected SHA-256")
    check_parser.add_argument("file", type=Path)
    check_parser.add_argument("expected_sha256")
    check_parser.add_argument("--json", action="store_true", dest="as_json")
    check_parser.set_defaults(handler=_cmd_check_hash)

    manifest_parser = sub.add_parser("manifest", help="create or verify file manifests")
    manifest_sub = manifest_parser.add_subparsers(dest="manifest_command", required=True)

    create_parser = manifest_sub.add_parser("create", help="create a SHA-256 manifest for a directory")
    create_parser.add_argument("root", type=Path)
    create_parser.add_argument("-o", "--output", type=Path, required=True)
    create_parser.add_argument("--exclude", action="append", default=[], help="glob to exclude; repeatable")
    create_parser.add_argument("--no-hidden", action="store_true", help="exclude files below dot-prefixed paths")
    create_parser.set_defaults(handler=_cmd_manifest_create)

    verify_parser = manifest_sub.add_parser("verify", help="verify a manifest against a directory")
    verify_parser.add_argument("manifest", type=Path)
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("--strict", action="store_true")
    verify_parser.add_argument("--exclude", action="append", default=[], help="glob to exclude in strict mode")
    verify_parser.add_argument("--json", action="store_true", dest="as_json")
    verify_parser.set_defaults(handler=_cmd_manifest_verify)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _cmd_hash(args: argparse.Namespace) -> int:
    for path in args.files:
        print(f"{sha256_file(path)}  {path}")
    return 0


def _cmd_check_hash(args: argparse.Namespace) -> int:
    run = AuditRun("sha256-check")
    run.record("file", str(args.file))
    run.check("SHA256", check_hash(args.file, args.expected_sha256))
    report = run.finalize()
    sys.stdout.write(report.to_json() if args.as_json else report.render_text())
    return report.exit_code


def _cmd_manifest_create(args: argparse.Namespace) -> int:
    manifest = create_manifest(
        args.root,
        exclude=args.exclude,
        include_hidden=not args.no_hidden,
    )
    manifest.write(args.output)
    print(f"MANIFEST_CREATE_GATE=PASS files={len(manifest.entries)} output={args.output}")
    return 0


def _cmd_manifest_verify(args: argparse.Namespace) -> int:
    report = verify_manifest(
        args.manifest,
        args.root,
        strict=args.strict,
        exclude=args.exclude,
    )
    sys.stdout.write(report.to_json() if args.as_json else report.render_text())
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
