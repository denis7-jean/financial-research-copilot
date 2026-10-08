"""Offline P0 calculation and exclusive local claim; never invokes a service.

Supplied hash anchors bind bytes, not prices, approval or execution authority.
One operator must retain the same persistent root and approved run identity.
The root's persistence/permissions are external prerequisites, not proved here.
"""

import argparse
from decimal import localcontext
import os
from pathlib import Path
import re
import sys

from app.services.rag_smoke_policy import (
    SmokePolicy,
    SmokeStop,
    canonical,
    charge,
    digest,
    money,
    strict_json,
)

PLAN_SCHEMA = "jev-rag-smoke-preinvoke-plan-v1"
RESULT_SCHEMA = "jev-rag-smoke-preinvoke-result-v1"
CLAIM_SCHEMA = "jev-rag-smoke-execution-claim-v1"
MAX_INPUT_BYTES = 1_048_576
HASH = re.compile(r"[0-9a-f]{64}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")
REFERENCE_FIELDS = {
    "artifact_sha256",
    "artifact_manifest_sha256",
    "artifact_review_sha256",
    "configuration_sha256",
    "configuration_review_sha256",
    "owner_decisions_sha256",
    "infrastructure_basis_sha256",
    "event_sha256",
}
EXTERNAL_GATES = [
    "AUTHORITATIVE_CURRENT_PRICE_AND_TOKEN_BOUND_EVIDENCE",
    "OWNER_DATA_LIMITS_BUDGET_AND_EXECUTION_APPROVAL",
    "INFRASTRUCTURE_ALLOWANCE_BASIS",
    "EXACT_ARTIFACT_CONFIGURATION_AND_REVIEW_VERIFICATION",
    "PERSISTENT_ROOT_RETENTION_PERMISSIONS_AND_SINGLE_OPERATOR",
    "ACTUAL_ZERO_RETRY_PARENT_CLIENT_AND_INNER_RUNTIME_ENFORCEMENT",
    "NATIVE_ARTIFACT_VALIDATION_AND_EXPLICIT_SMOKE_HANDLER",
    "PER_DELIVERED_REQUEST_ACCOUNTING_AND_CONFIRMED_OPERATOR_EVIDENCE",
]


class PreinvokeError(ValueError):
    """Only fixed codes leave expected input/publication failure boundaries."""


def require(condition, code):
    if not condition:
        raise PreinvokeError(code) from None


def exact(value, keys, code="PLAN_INVALID"):
    require(type(value) is dict and set(value) == set(keys), code)


def hash_value(value):
    return type(value) is str and HASH.fullmatch(value) is not None


def encode(value, code):
    try:
        return canonical(value)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise PreinvokeError(code) from None


def parse(raw, code):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT_BYTES, code)
    try:
        return strict_json(raw)
    except SmokeStop:
        raise PreinvokeError(code) from None


def amount(value):
    try:
        return money(value)
    except SmokeStop:
        raise PreinvokeError("LIMITS_INVALID") from None


def validate(plan_raw, policy_raw, *, evidence, expected_hashes):
    """Pure validation/calculation. No filesystem, clocks, clients or dispatch.

    expected_hashes is a separate caller input with plan/policy/haiku/titan
    keys. Its source/trust and every referenced approval remain external.
    """
    exact(
        expected_hashes, {"plan", "policy", "haiku", "titan"}, "TRUST_BINDINGS_REQUIRED"
    )
    require(
        all(hash_value(v) for v in expected_hashes.values()), "TRUST_BINDINGS_REQUIRED"
    )
    exact(evidence, {"haiku", "titan"}, "PRICE_EVIDENCE_REQUIRED")
    for name, raw in (("plan", plan_raw), ("policy", policy_raw), *evidence.items()):
        require(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT_BYTES, "INPUT_INVALID")
        require(digest(raw) == expected_hashes[name], "INPUT_HASH_MISMATCH")
    plan = parse(plan_raw, "PLAN_INVALID")
    policy = parse(policy_raw, "POLICY_INVALID")
    require(encode(plan, "PLAN_SERIALIZATION_FAILED") == plan_raw, "PLAN_NOT_CANONICAL")
    require(
        encode(policy, "POLICY_SERIALIZATION_FAILED") == policy_raw,
        "POLICY_NOT_CANONICAL",
    )
    exact(
        plan,
        {
            "schema",
            "plan_id",
            "run_id",
            "policy_sha256",
            "price_evidence_sha256",
            "references",
            "owner_limits",
            "parent_invocation",
        },
    )
    require(plan["schema"] == PLAN_SCHEMA, "PLAN_INVALID")
    require(
        all(
            type(plan[k]) is str and IDENTITY.fullmatch(plan[k])
            for k in ("plan_id", "run_id")
        ),
        "PLAN_INVALID",
    )
    require(
        plan["policy_sha256"] == expected_hashes["policy"], "POLICY_BINDING_MISMATCH"
    )
    exact(plan["price_evidence_sha256"], {"haiku", "titan"})
    require(
        plan["price_evidence_sha256"] == {k: expected_hashes[k] for k in evidence},
        "PRICE_BINDING_MISMATCH",
    )
    exact(plan["references"], REFERENCE_FIELDS)
    require(
        all(hash_value(v) for v in plan["references"].values()), "REFERENCE_INVALID"
    )
    exact(
        plan["owner_limits"],
        {
            "ceilings_usd",
            "infrastructure_allowance_usd",
            "memory_mib",
            "timeout_seconds",
            "ephemeral_storage_mib",
        },
    )
    limits = plan["owner_limits"]
    exact(limits["ceilings_usd"], {"haiku", "titan", "total"})
    ceilings = {k: amount(v) for k, v in limits["ceilings_usd"].items()}
    require(all(v > 0 for v in ceilings.values()), "LIMITS_INVALID")
    infrastructure = amount(limits["infrastructure_allowance_usd"])
    for key in ("memory_mib", "timeout_seconds", "ephemeral_storage_mib"):
        require(
            type(limits[key]) is int and 0 < limits[key] <= 1_000_000, "LIMITS_INVALID"
        )
    parent = plan["parent_invocation"]
    exact(parent, {"max_attempts", "connect_seconds", "read_seconds"})
    require(
        type(parent["max_attempts"]) is int and parent["max_attempts"] == 1,
        "PARENT_ATTEMPTS_INVALID",
    )
    for key in ("connect_seconds", "read_seconds"):
        require(
            type(parent[key]) is int and 0 < parent[key] <= 120,
            "PARENT_TIMEOUT_INVALID",
        )
    # Reuse the accepted pure constructor, never activate it or create clients.
    try:
        checked = SmokePolicy(
            policy,
            evidence=evidence,
            trusted_evidence_hashes={k: expected_hashes[k] for k in evidence},
            claim_directory=Path("unused-not-activated"),
            native=None,
        )
    except SmokeStop:
        raise PreinvokeError("POLICY_OR_PRICE_EVIDENCE_INVALID") from None
    require(plan["run_id"] == checked.config["run_id"], "RUN_BINDING_MISMATCH")
    require(ceilings == checked.caps, "CEILING_BINDING_MISMATCH")
    expected = checked.config["expected_source"]
    require(
        expected["minimum_hits"]
        <= checked.config["metadata"]["source_counts"][expected["source"]],
        "EXPECTED_SOURCE_IMPOSSIBLE",
    )
    with localcontext() as context:
        context.prec = 80
        haiku, titan = checked.prices["haiku"], checked.prices["titan"]
        route = charge(
            haiku["input_token_bound"], checked.config["output_tokens"]["router"], haiku
        )
        embedding = charge(titan["input_token_bound"], 0, titan)
        generation = charge(
            haiku["input_token_bound"],
            checked.config["output_tokens"]["generation"],
            haiku,
        )
        haiku_total = route + generation
        model_total = haiku_total + embedding
        total = model_total + infrastructure
        require(haiku_total <= ceilings["haiku"], "HAIKU_CEILING_INSUFFICIENT")
        require(embedding <= ceilings["titan"], "TITAN_CEILING_INSUFFICIENT")
        require(total <= ceilings["total"], "TOTAL_CEILING_INSUFFICIENT")
    # Stable across revisions of the same run's plan, avoiding hash-change resend.
    execution_id = digest(
        b"jev-rag-smoke-execution-id-v1\0" + plan["run_id"].encode("ascii")
    )
    return {
        "schema": RESULT_SCHEMA,
        "status": "BUDGET_SUFFICIENT_EXTERNAL_GATES_UNRESOLVED",
        "plan_sha256": expected_hashes["plan"],
        "policy_sha256": expected_hashes["policy"],
        "price_evidence_sha256": {k: expected_hashes[k] for k in evidence},
        "execution_id": execution_id,
        "references_sha256": digest(
            encode(plan["references"], "PLAN_SERIALIZATION_FAILED")
        ),
        "initial_reservations_usd": {
            k: format(v, "f")
            for k, v in {
                "ROUTE": route,
                "EMBED": embedding,
                "GENERATE": generation,
                "haiku": haiku_total,
                "titan": embedding,
                "models": model_total,
                "infrastructure": infrastructure,
                "whole_run": total,
            }.items()
        },
        "external_gates": list(EXTERNAL_GATES),
        "owner_authorized": False,
        "artifact_ready": False,
        "invoke_authorized": False,
    }


def persistent_root(value):
    """Existing absolute root outside Git, with no symlink/reparse ancestors."""
    try:
        root = Path(value)
        require(
            root.is_absolute() and root.is_dir() and root.resolve(strict=True) == root,
            "CLAIM_ROOT_INVALID",
        )
        for path in (root, *root.parents):
            metadata = path.lstat()
            require(
                not path.is_symlink()
                and not getattr(metadata, "st_file_attributes", 0) & 0x400
                and not (path / ".git").exists(),
                "CLAIM_ROOT_INVALID",
            )
    except (OSError, ValueError, TypeError, RuntimeError):
        raise PreinvokeError("CLAIM_ROOT_INVALID") from None
    return root


def publish_claim(plan_raw, policy_raw, *, evidence, expected_hashes, root):
    """Revalidate, then claim once. No retries, release, overwrite or cleanup.

    Failure after directory creation leaves it intact and blocks later attempts,
    including empty/partial publication. Successful publication is not dispatch.
    """
    result = validate(
        plan_raw, policy_raw, evidence=evidence, expected_hashes=expected_hashes
    )
    parent = persistent_root(root)
    payload = {
        "schema": CLAIM_SCHEMA,
        "state": "FULL_RESERVATIONS_RETAINED_NO_DISPATCH",
        "preflight": result,
    }
    raw = encode(payload, "CLAIM_SERIALIZATION_FAILED")
    directory = parent / result["execution_id"]
    try:
        directory.mkdir()
    except FileExistsError:
        raise PreinvokeError("EXECUTION_ALREADY_CLAIMED") from None
    except OSError:
        raise PreinvokeError("CLAIM_CREATE_FAILED") from None
    try:
        with (directory / "claim.json").open("xb") as stream:
            if stream.write(raw) != len(raw):
                raise OSError("short write")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise PreinvokeError("CLAIM_PUBLICATION_FAILED_RETAINED") from None
    except KeyboardInterrupt:
        raise PreinvokeError("CLAIM_INTERRUPTED_RETAINED") from None
    return {
        **result,
        "status": "CLAIM_PUBLISHED_NO_DISPATCH_AUTHORIZATION",
        "claim_sha256": digest(raw),
    }


def read_input(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except (OSError, ValueError):
        raise PreinvokeError("INPUT_UNREADABLE") from None
    require(0 < len(raw) <= MAX_INPUT_BYTES, "INPUT_INVALID")
    return raw


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PreinvokeError("ARGUMENTS_INVALID") from None


def diagnostic(code):
    try:
        sys.stderr.write(code + "\n")
    except (OSError, UnicodeError, ValueError):
        pass  # Exit status still denies confirmation; nothing is retried.


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "claim"))
    for name in (
        "plan",
        "policy",
        "haiku-evidence",
        "titan-evidence",
        "expected-hashes",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--persistent-root")
    try:
        args = parser.parse_args(argv)
        require(
            (args.mode == "claim") == (args.persistent_root is not None),
            "ARGUMENTS_INVALID",
        )
        plan, policy = read_input(args.plan), read_input(args.policy)
        evidence = {
            "haiku": read_input(args.haiku_evidence),
            "titan": read_input(args.titan_evidence),
        }
        hashes = parse(read_input(args.expected_hashes), "TRUST_BINDINGS_REQUIRED")
        kwargs = {"evidence": evidence, "expected_hashes": hashes}
        result = (
            publish_claim(plan, policy, root=args.persistent_root, **kwargs)
            if args.mode == "claim"
            else validate(plan, policy, **kwargs)
        )
    except PreinvokeError as error:
        diagnostic(str(error))
        return 2
    try:
        text = encode(result, "CONSOLE_CONFIRMATION_UNAVAILABLE").decode("ascii")
        require(sys.stdout.write(text) == len(text), "CONSOLE_CONFIRMATION_UNAVAILABLE")
        sys.stdout.flush()
    except (PreinvokeError, OSError, UnicodeError, ValueError):
        diagnostic("CONSOLE_CONFIRMATION_UNAVAILABLE")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
