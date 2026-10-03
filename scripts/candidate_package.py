"""Offline source-only archive diagnostics; no install, write or deployment.

Not a Lambda deployment ZIP. Linux dependencies/layers and actual configuration
require later independently reviewed evidence.
"""

import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import zipfile

DEFAULT_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


class CandidateError(ValueError):
    """Static sanitized rejection codes."""


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_config(config):
    required = {
        "router_provider": "haiku",
        "shadow_enabled": False,
        "live_eval_enabled": False,
        "bedrock_model_id": DEFAULT_MODEL,
        "region": "us-east-1",
        "target_python": "3.11",
        "handler": "app.lambda_handler.handler",
    }
    if type(config) is not dict or set(config) != set(required):
        raise CandidateError("configuration_schema")
    if any(
        type(config[key]) is not type(value) or config[key] != value
        for key, value in required.items()
    ):
        raise CandidateError("configuration_not_safe_default")
    return dict(required)


def safe_read(root, relative):
    target = root / relative
    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise CandidateError("source_symlink")
    if not target.resolve().is_relative_to(root) or not target.is_file():
        raise CandidateError("source_binding")
    return target.read_bytes()


def build_candidate(root, config):
    root = Path(root).resolve(strict=True)
    config = validate_config(config)
    names = []
    # No application imports eval; keep evaluation inputs and archives out.
    for directory in ("app",):
        base = root / directory
        if base.is_symlink() or not base.is_dir():
            raise CandidateError("source_binding")
        for path in base.rglob("*"):
            relative = path.relative_to(root)
            if "results" in relative.parts or "__pycache__" in relative.parts:
                continue
            if path.is_symlink():
                raise CandidateError("source_symlink")
            if (
                path.is_file()
                and path.suffix == ".py"
                and not path.name.startswith("test_")
            ):
                names.append(relative.as_posix())
    required = {
        "app/lambda_handler.py",
        "app/main.py",
        "app/agents/router.py",
        "app/agents/router_configuration.py",
    }
    if not required.issubset(names):
        raise CandidateError("source_incomplete")
    sources = {}
    for name in sorted(names):
        raw = safe_read(root, name)
        try:
            ast.parse(raw, feature_version=(3, 11))
        except (SyntaxError, ValueError, UnicodeError):
            raise CandidateError("python311_syntax") from None
        sources[name] = raw
    lock = safe_read(root, "requirements.txt")
    manifest = {
        "schema": "jev-source-candidate-v1",
        "status": "NOT_DEPLOYABLE_DEPENDENCIES_NOT_INCLUDED",
        "configuration": config,
        "configuration_evidence": "OFFLINE_ASSERTION_NOT_ENVIRONMENT_OBSERVATION",
        "source_sha256": {p: digest(b) for p, b in sources.items()},
        "requirements_sha256": digest(lock),
        "limitations": [
            "not_a_runtime_or_dependency_lock",
            "python311_syntax_only_not_execution",
            "no_actual_lambda_configuration_verified",
            "jev_live_and_shadow_disabled",
        ],
    }
    sources["requirements.txt"] = lock
    sources["candidate-manifest.json"] = canonical(manifest)
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(sources):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, sources[name])
    raw = memory.getvalue()
    return raw, canonical(
        {
            "schema": "jev-source-candidate-receipt-v1",
            "archive_sha256": digest(raw),
            "manifest_sha256": digest(sources["candidate-manifest.json"]),
            "manifest": manifest,
        }
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Explicit nonsecret offline configuration JSON",
    )
    args = parser.parse_args()
    try:
        raw, receipt = build_candidate(args.root, json.loads(args.config.read_bytes()))
    except (CandidateError, OSError, ValueError) as error:
        parser.exit(
            2,
            "candidate_check_failed:"
            + (
                str(error)
                if isinstance(error, CandidateError)
                else "input_read_or_schema"
            )
            + "\n",
        )
    print(receipt.decode("utf-8"), end="")
    assert digest(raw) == json.loads(receipt)["archive_sha256"]


if __name__ == "__main__":
    main()
