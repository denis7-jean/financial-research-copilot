"""Offline-only CLI: no live, freeze, rank or select command exists."""

import argparse
import json
from pathlib import Path


def main(argv=None):
    # The repository's guard is installed before local operational imports.
    from tests.offline_guard import install

    install()
    from experiments.reviewer_protocol_v2.common import ProtocolError

    parser = argparse.ArgumentParser(description="Reviewer v2 offline unselected audit")
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    audit.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            from experiments.reviewer_protocol_v2.audit import run_audit

            result = run_audit(args.root, args.output)
        else:
            from experiments.reviewer_protocol_v2.integrity import (
                verify_output_manifest,
            )

            result = {"manifest_sha256": verify_output_manifest(args.directory)}
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (
        ProtocolError,
        OSError,
        UnicodeError,
        KeyError,
        TypeError,
        StopIteration,
        ValueError,
    ):
        # Never expose real records, source text, IDs or exception reprs.
        print(
            json.dumps(
                {
                    "status": "OFFLINE_OPERATION_FAILED",
                    "detail": "see private inputs and integrity checks",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
