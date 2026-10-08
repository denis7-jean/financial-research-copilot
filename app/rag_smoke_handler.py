"""Isolated opt-in smoke entry. No clients, dotenv or native imports at import time.

The trusted isolated function configuration binds the canonical event, not owner
approval. Persistent parent claims and actual execution permission are external.
"""

import os
from pathlib import Path
import re

from app.services.rag_smoke_policy import (
    SmokePolicy,
    SmokeStop,
    canonical,
    digest,
    strict_json,
)

SCHEMA = "rag-smoke-invocation-v1"
RESULT_SCHEMA = "rag-smoke-handler-result-v1"
PAYLOAD_BINDING_VARIABLE = "COPILOT_RAG_SMOKE_PAYLOAD_SHA256"
MAX_EVENT_BYTES = 131_072
MAX_RESULT_BYTES = 131_072
MAX_ANSWER_BYTES = 16_384
HASH = re.compile(r"[0-9a-f]{64}\Z")
STOP_CODES = frozenset(
    {
        "RUN_ALREADY_CLAIMED",
        "CLAIM_PATH_INVALID",
        "CLAIM_UNAVAILABLE",
        "EVIDENCE_PUBLICATION_FAILED",
        "LOCAL_OR_UNCERTAIN_FAILURE",
        "UNCERTAIN_PROVIDER_OUTCOME",
        "CLIENT_BINDING_INVALID",
        "CLIENT_CONFIG_INVALID",
        "CHAIN_ORDER_INVALID",
        "CHAIN_INCOMPLETE",
        "CLIENTS_MISSING",
        "UNEXPECTED_REQUEST",
        "UNEXPECTED_SEND",
        "EXTRA_ATTEMPT",
        "EXTRA_SEND",
        "ENDPOINT_INVALID",
        "ATTEMPT_COUNT_INVALID",
        "RESERVATION_EXHAUSTED",
        "USAGE_INVALID",
        "USAGE_OVERRUN",
        "MODEL_OUTPUT_INVALID",
        "BODY_MISSING",
        "BODY_INVALID",
        "BODY_TOO_LARGE",
        "OBJECT_BINDING_MISMATCH",
        "METADATA_INVALID",
        "METADATA_SOURCE_MISMATCH",
        "JSON_INVALID",
        "INDEX_STRUCTURE_INVALID",
        "EMBEDDING_INVALID",
        "SEARCH_RESULT_INVALID",
        "EXPECTED_SOURCE_MISSING",
        "ROUTER_MISROUTE",
        "ROUTER_FALLBACK",
        "ROUTER_OUTPUT_INVALID",
        "RAG_RESULT_INVALID",
        "INPUT_BINDING_MISMATCH",
        "RESULT_INVALID",
        "RESULT_TOO_LARGE",
        "LOCAL_EVIDENCE_UNAVAILABLE",
    }
)


class EnvelopeError(ValueError):
    """Expected failures contain fixed codes only."""


def require(condition, code):
    if not condition:
        raise EnvelopeError(code) from None


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys), "ENVELOPE_INVALID")


def encoded(value):
    try:
        return canonical(value)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise EnvelopeError("ENVELOPE_INVALID") from None


def validate(event, expected_payload_sha256, root, native):
    """No client construction, imports of execution modules or claim publication."""
    require(
        type(expected_payload_sha256) is str
        and HASH.fullmatch(expected_payload_sha256) is not None,
        "TRUSTED_PAYLOAD_BINDING_REQUIRED",
    )
    raw = encoded(event)
    require(len(raw) <= MAX_EVENT_BYTES, "ENVELOPE_TOO_LARGE")
    require(digest(raw) == expected_payload_sha256, "PAYLOAD_BINDING_MISMATCH")
    exact(event, {"schema", "query", "policy_utf8", "evidence_utf8", "bindings"})
    require(event["schema"] == SCHEMA, "ENVELOPE_INVALID")
    query = event["query"]
    try:
        valid_query = (
            type(query) is str and 0 < len(query) <= 300 and len(query.encode()) <= 1200
        )
    except UnicodeError:
        valid_query = False
    require(valid_query, "QUERY_INVALID")
    exact(event["evidence_utf8"], {"haiku", "titan"})
    exact(event["bindings"], {"policy_sha256", "price_evidence_sha256"})
    exact(event["bindings"]["price_evidence_sha256"], {"haiku", "titan"})
    require(
        type(event["bindings"]["policy_sha256"]) is str
        and HASH.fullmatch(event["bindings"]["policy_sha256"]) is not None,
        "ENVELOPE_INVALID",
    )
    texts = {"policy": event["policy_utf8"], **event["evidence_utf8"]}
    records = {}
    for key, value in texts.items():
        require(type(value) is str, "ENVELOPE_INVALID")
        try:
            record = value.encode("utf-8")
        except UnicodeError:
            raise EnvelopeError("ENVELOPE_INVALID") from None
        require(
            0 < len(record) <= (65_536 if key == "policy" else 16_384),
            "ENVELOPE_TOO_LARGE",
        )
        records[key] = record
    require(
        digest(records["policy"]) == event["bindings"]["policy_sha256"],
        "POLICY_BINDING_MISMATCH",
    )
    try:
        config = strict_json(records["policy"])
        require(encoded(config) == records["policy"], "POLICY_NOT_CANONICAL")
        policy = SmokePolicy(
            config,
            evidence={k: records[k] for k in ("haiku", "titan")},
            trusted_evidence_hashes=event["bindings"]["price_evidence_sha256"],
            claim_directory=Path(root) / config["run_id"],
            native=native,
        )
        policy.validate_query(query)
        expected = policy.config["expected_source"]
        require(
            expected["minimum_hits"]
            <= policy.config["metadata"]["source_counts"][expected["source"]],
            "EXPECTED_SOURCE_IMPOSSIBLE",
        )
    except (
        SmokeStop,
        KeyError,
        TypeError,
        ValueError,
        UnicodeError,
        RecursionError,
        OverflowError,
    ) as error:
        if isinstance(error, EnvelopeError):
            raise
        raise EnvelopeError("POLICY_OR_EVIDENCE_INVALID") from None
    parent = Path(root)
    try:
        require(
            parent.is_absolute()
            and parent.is_dir()
            and parent.resolve(strict=True) == parent,
            "LOCAL_ROOT_INVALID",
        )
        for path in (parent, *parent.parents):
            metadata = path.lstat()
            require(
                not path.is_symlink()
                and not getattr(metadata, "st_file_attributes", 0) & 0x400
                and not (path / ".git").exists(),
                "LOCAL_ROOT_INVALID",
            )
    except (OSError, ValueError, RuntimeError):
        raise EnvelopeError("LOCAL_ROOT_INVALID") from None
    return policy


def dedicated_clients(policy):
    """Future isolated-function SDK construction, never used by offline tests.

    Explicit endpoints exclude endpoint overrides. SDK credential-provider
    activity is outside the service-attempt hooks and an operational prerequisite.
    """
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    cfg = Config(
        region_name=policy.config["region"],
        connect_timeout=policy.config["timeouts"]["connect_seconds"],
        read_timeout=policy.config["timeouts"]["read_seconds"],
        retries={"total_max_attempts": 1, "mode": "standard"},
    )
    clients = {}
    try:
        session = boto3.session.Session(region_name=policy.config["region"])
        for name in ("bedrock-runtime", "s3"):
            clients[name] = session.client(
                name,
                region_name="us-east-1",
                endpoint_url=f"https://{name}.us-east-1.amazonaws.com",
                config=cfg,
            )
        return clients
    except (BotoCoreError, ClientError, OSError):
        for client in clients.values():
            client.close()
        raise EnvelopeError("CLIENT_INITIALIZATION_FAILED") from None


def evidence_snapshot(policy):
    """Hash exact local metadata journals; no claim of parent publication."""
    if not policy.used:
        return []
    try:
        events = []
        for ordinal in range(1, policy.sequence + 1):
            matches = list(policy.directory.glob(f"{ordinal:02d}-*.json"))
            require(
                len(matches) == 1 and not matches[0].is_symlink(),
                "LOCAL_EVIDENCE_UNAVAILABLE",
            )
            raw = matches[0].read_bytes()
            require(len(raw) <= 16_384, "LOCAL_EVIDENCE_UNAVAILABLE")
            record = strict_json(raw)
            require(
                type(record) is dict
                and record.get("sequence") == ordinal
                and record.get("schema") == "rag-smoke-event-v1",
                "LOCAL_EVIDENCE_UNAVAILABLE",
            )
            events.append(
                {"filename": matches[0].name, "sha256": digest(raw), "record": record}
            )
        require(len(events) <= 32, "LOCAL_EVIDENCE_UNAVAILABLE")
        return events
    except (OSError, SmokeStop, ValueError, TypeError, UnicodeError, RecursionError):
        raise EnvelopeError("LOCAL_EVIDENCE_UNAVAILABLE") from None


def bounded_result(result):
    require(type(result) is dict and result.get("task_type") == "qa", "RESULT_INVALID")
    inner = result.get("result")
    require(type(inner) is dict and type(inner.get("answer")) is str, "RESULT_INVALID")
    try:
        require(
            0 < len(inner["answer"].encode()) <= MAX_ANSWER_BYTES, "RESULT_TOO_LARGE"
        )
    except UnicodeError:
        raise EnvelopeError("RESULT_INVALID") from None
    # Private answer returned; retrieved text is deliberately not duplicated.
    return {
        "answer": inner["answer"],
        "citations": sorted(inner["citations"]),
        "retrieval": [
            {"source": row["source"], "score": row["score"]}
            for row in inner["retrieved_context"]
        ],
        "router_confidence": result["router_confidence"],
    }


def response(status, code, *, policy=None, result=None, events=None):
    return {
        "schema": RESULT_SCHEMA,
        "scope": "STRUCTURAL_SMOKE_NOT_QUALIFICATION",
        "status": status,
        "code": code,
        "run_id": policy.config["run_id"] if policy else None,
        "policy_sha256": digest(canonical(policy.config)) if policy else None,
        "attempts": policy.attempts if policy else {},
        "exposure_usd": {k: str(v) for k, v in policy.exposure.items()}
        if policy
        else {},
        "local_events": events or [],
        "result": result,
        "parent_claim_verified": False,
        "publication_confirmed": False,
        "qualification": False,
        "release_authorized": False,
    }


def handler(
    event,
    context,
    *,
    client_factory=None,
    native=None,
    claim_root=None,
    expected_payload_sha256=None,
):
    """Lambda entry; keyword seams are for offline tests, never caller event fields."""
    policy = None
    clients = {}
    root = Path("/tmp") if claim_root is None else claim_root
    anchor = (
        os.environ.get(PAYLOAD_BINDING_VARIABLE)
        if expected_payload_sha256 is None
        else expected_payload_sha256
    )
    try:
        policy = validate(event, anchor, root, native)
    except EnvelopeError as error:
        return response("STOPPED", str(error))
    status, code, result = "STOPPED", "CLIENT_INITIALIZATION_FAILED", None
    try:
        clients = (client_factory or dedicated_clients)(policy)
        require(
            type(clients) is dict and set(clients) == {"bedrock-runtime", "s3"},
            "CLIENT_FACTORY_INVALID",
        )
        require(
            all(
                callable(getattr(client, "close", None)) for client in clients.values()
            ),
            "CLIENT_FACTORY_INVALID",
        )
        policy.bind_clients(bedrock=clients["bedrock-runtime"], s3=clients["s3"])
        from app.agents.orchestrator import CopilotOrchestrator

        result = bounded_result(
            CopilotOrchestrator.process_smoke(event["query"], policy=policy)
        )
        status, code = "STRUCTURAL_SUCCESS", None
    except SmokeStop as error:
        code = str(error) if str(error) in STOP_CODES else "SMOKE_STOPPED"
        uncertain = code in {
            "UNCERTAIN_PROVIDER_OUTCOME",
            "LOCAL_OR_UNCERTAIN_FAILURE",
            "EVIDENCE_PUBLICATION_FAILED",
        } or any(
            not value["settled"] and value["reservation_usd"] != "0"
            for value in policy.attempts.values()
        )
        status = "UNCERTAIN" if uncertain else "STOPPED"
        result = None
    except EnvelopeError as error:
        code, result = str(error), None
    except (OSError, ImportError):
        code, result = "LOCAL_EXECUTION_UNAVAILABLE", None
        status = "UNCERTAIN" if policy.attempts else "STOPPED"
    finally:
        for client in clients.values() if type(clients) is dict else ():
            try:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
            except (OSError, ValueError):
                status, code, result = "UNCERTAIN", "CLIENT_CLOSE_FAILED", None
    try:
        events = evidence_snapshot(policy)
    except EnvelopeError:
        events = []
        status, code, result = "UNCERTAIN", "LOCAL_EVIDENCE_UNAVAILABLE", None
    output = response(status, code, policy=policy, result=result, events=events)
    try:
        require(len(canonical(output)) <= MAX_RESULT_BYTES, "RESULT_TOO_LARGE")
    except (
        EnvelopeError,
        ValueError,
        TypeError,
        UnicodeError,
        RecursionError,
        OverflowError,
    ):
        # Holds/attempts survive a bounded-output rejection; full local journals remain.
        output = response("UNCERTAIN", "RESULT_TOO_LARGE", policy=policy)
    return output
