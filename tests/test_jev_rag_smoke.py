"""Invented SDK streams/events and native adapters; never run native code."""

from decimal import Decimal
import io
import json
import math
from types import SimpleNamespace
from urllib.parse import quote

import pytest

from app.agents.orchestrator import CopilotOrchestrator
from app.services import retriever
from app.services.rag_smoke_policy import (
    HAIKU,
    TITAN,
    SmokePolicy,
    SmokeStop,
    canonical,
    charge,
    digest,
    current_policy,
)
from tests import offline_guard
from tests.conftest import converse_text

QUERY = "What is the invented company's revenue?"
SENTINEL = "invented-sensitive-payload-DO-NOT-LOG"


class Events:
    def __init__(self):
        self.handlers = {}

    def register(self, event, callback):
        self.handlers[event] = callback

    def emit(self, event, **kwargs):
        callback = self.handlers.get(event)
        if callback:
            callback(**kwargs)


class FakeSDK:
    def __init__(self, service, responses):
        self.service = service
        self.responses = list(responses)
        self.calls = []
        self.wire_sends = 0
        self.send_events = 1
        self.skip_hooks = False
        self.meta = SimpleNamespace(
            config=SimpleNamespace(
                region_name="us-east-1",
                connect_timeout=2,
                read_timeout=10,
                retries={"total_max_attempts": 1, "mode": "standard"},
            ),
            endpoint_url=f"https://{service}.us-east-1.amazonaws.com",
            events=Events(),
        )

    def call(self, operation, kwargs):
        self.calls.append((operation, kwargs))
        if not self.skip_hooks:
            self.meta.events.emit(
                "before-parameter-build.*.*",
                model=SimpleNamespace(name=operation),
                params=kwargs,
            )
            if operation == "GetObject":
                url = f"https://{kwargs['Bucket']}.s3.us-east-1.amazonaws.com/{kwargs['Key']}"
            else:
                url = f"https://bedrock-runtime.us-east-1.amazonaws.com/model/{quote(kwargs['modelId'], safe='')}/{'converse' if operation == 'Converse' else 'invoke'}"
            for _ in range(self.send_events):
                self.meta.events.emit(
                    "before-send.*.*",
                    request=SimpleNamespace(
                        url=url, method="GET" if operation == "GetObject" else "POST"
                    ),
                )
                self.wire_sends += 1
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def converse(self, **kwargs):
        return self.call("Converse", kwargs)

    def invoke_model(self, **kwargs):
        return self.call("InvokeModel", kwargs)

    def get_object(self, **kwargs):
        return self.call("GetObject", kwargs)


class Native:
    def __init__(self):
        self.loads = []
        self.index = SimpleNamespace(
            d=1024,
            ntotal=5,
            search=lambda embedding, k: (
                [[1.0, 0.9, 0.8, 0.7, 0.6]],
                [[0, 1, 2, 3, 4]],
            ),
        )

    def deserialize(self, raw):
        self.loads.append(raw)
        return self.index

    def is_flat_ip(self, index):
        return True

    def embedding_array(self, values):
        return [values]

    def valid_index(self, value):
        return type(value) is int

    def finite_score(self, value):
        return type(value) in (int, float) and math.isfinite(value)


def invented(tmp_path):
    native = Native()
    index_raw = b"INVENTED INDEX BYTES - NOT FAISS"
    source = "s3://invented-bucket/docs/public-invented.pdf"
    metadata_raw = canonical(
        [{"chunk_id": i, "source": source, "text": SENTINEL} for i in range(5)]
    )
    objects = {
        role: {
            "bucket": "invented-bucket",
            "key": "index/" + role,
            "owner": "123456789012",
            "etag": '"abc"',
            "version_id": None,
            "size_bytes": len(raw),
            "sha256": digest(raw),
        }
        for role, raw in (("index", index_raw), ("metadata", metadata_raw))
    }
    config = {
        "schema": "rag-smoke-policy-v2",
        "run_id": "invented-run",
        "scenario": "invented-factual-qa",
        "query_sha256": digest(QUERY.encode()),
        "region": "us-east-1",
        "models": {"haiku": HAIKU, "titan": TITAN},
        "max_attempts": {
            "router": 1,
            "embedding": 1,
            "generation": 1,
            "object_reads": 2,
        },
        "output_tokens": {"router": 64, "generation": 100},
        "ceilings_usd": {"haiku": "1", "titan": "0.01", "total": "1.01"},
        "timeouts": {"connect_seconds": 2, "read_seconds": 10},
        "objects": objects,
        "metadata": {"rows": 5, "source_counts": {source: 5}, "max_text_bytes": 100},
        "expected_source": {"source": source, "minimum_hits": 1},
        "embedding_response_bytes": 65536,
    }
    evidence = {
        provider: canonical(
            {
                "schema": "rag-smoke-price-bound-v1",
                "model_id": model,
                "region": "us-east-1",
                "tier": "standard",
                "input_token_bound": bound,
                "max_supported_output_tokens": output,
                "input_usd_per_million": price,
                "output_usd_per_million": outprice,
                "source_urls": ["https://docs.aws.amazon.com/invented-fixture"],
                "verified_utc": "2026-10-07T00:00:00Z",
            }
        )
        for provider, model, bound, output, price, outprice in (
            ("haiku", HAIKU, 200000, 1000, "1.10", "5.50"),
            ("titan", TITAN, 100, 0, "0.02", "0"),
        )
    }
    hashes = {key: digest(raw) for key, raw in evidence.items()}
    route = converse_text(
        json.dumps({"task_type": "qa", "confidence": 0.9, "reasoning": "invented"}),
        20,
        10,
    )
    generation = converse_text("An invented answer.", 30, 20)
    route["ResponseMetadata"] = generation["ResponseMetadata"] = {"RetryAttempts": 0}
    embedding = {
        "body": io.BytesIO(
            canonical({"embedding": [1.0] + [0.0] * 1023, "inputTextTokenCount": 5})
        ),
        "ResponseMetadata": {"RetryAttempts": 0},
    }
    model = FakeSDK("bedrock-runtime", [route, embedding, generation])
    s3 = FakeSDK(
        "s3",
        [
            {
                "Body": io.BytesIO(raw),
                "ETag": '"abc"',
                "ContentLength": len(raw),
                "ResponseMetadata": {"RetryAttempts": 0},
            }
            for raw in (index_raw, metadata_raw)
        ],
    )
    return SimpleNamespace(
        config=config,
        evidence=evidence,
        hashes=hashes,
        native=native,
        model=model,
        s3=s3,
        tmp=tmp_path,
    )


def policy(f):
    result = SmokePolicy(
        f.config,
        evidence=f.evidence,
        trusted_evidence_hashes=f.hashes,
        claim_directory=f.tmp / f.config["run_id"],
        native=f.native,
    )
    result.bind_clients(bedrock=f.model, s3=f.s3)
    return result


def run(f):
    p = policy(f)
    return p, CopilotOrchestrator.process_smoke(QUERY, policy=p)


def test_actual_application_chain_and_durable_metadata_only_evidence(
    tmp_path, capsys, monkeypatch
):
    f = invented(tmp_path)
    # Ordinary cached data must never bypass this run's input verification.
    monkeypatch.setattr(retriever, "_index", object())
    monkeypatch.setattr(retriever, "_metadata", [{"text": "wrong"}])
    p, result = run(f)
    assert result["scope"] == "STRUCTURAL_SMOKE_NOT_QUALIFICATION"
    assert len(result["result"]["retrieved_context"]) == 5
    assert [op for op, _ in f.model.calls] == ["Converse", "InvokeModel", "Converse"]
    assert f.model.wire_sends == 3 and f.s3.wire_sends == 2
    assert len(f.native.loads) == 1 and current_policy() is None
    for _, request in f.s3.calls:
        assert (
            request["ExpectedBucketOwner"] == "123456789012"
            and request["IfMatch"] == '"abc"'
        )
    assert f.model.calls[0][1]["inferenceConfig"] == {"maxTokens": 64}
    assert f.model.calls[2][1]["inferenceConfig"] == {"maxTokens": 100}
    evidence_text = "".join(path.read_text() for path in p.directory.iterdir())
    assert (
        SENTINEL not in evidence_text
        and QUERY not in evidence_text
        and "An invented answer" not in evidence_text
    )
    assert SENTINEL not in capsys.readouterr().out
    assert p.exposure == {"haiku": Decimal("0.00022"), "titan": Decimal("0.0000001")}
    assert f.model.responses == [] and f.s3.responses == []
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


@pytest.mark.parametrize(
    "field,value",
    [
        ("region", "eu-west-1"),
        ("output_tokens", {}),
        ("ceilings_usd", {}),
        ("embedding_response_bytes", 0),
        ("query_sha256", "x"),
        ("models", {"haiku": "another", "titan": TITAN}),
        ("max_attempts", {"router": True}),
    ],
)
def test_incomplete_or_unapproved_config_blocks_all_side_effects(
    tmp_path, field, value
):
    f = invented(tmp_path)
    f.config[field] = value
    with pytest.raises(SmokeStop):
        policy(f)
    assert (
        not f.model.calls
        and not f.s3.calls
        and not (tmp_path / "invented-run").exists()
    )


def test_separately_supplied_hash_is_not_self_declared(tmp_path):
    f = invented(tmp_path)
    f.hashes["haiku"] = "0" * 64
    with pytest.raises(SmokeStop, match="EVIDENCE_HASH_MISMATCH"):
        policy(f)
    assert not f.model.calls


@pytest.mark.parametrize(
    "change,code",
    [
        ("hash", "OBJECT_BINDING_MISMATCH"),
        ("etag", "OBJECT_BINDING_MISMATCH"),
        ("size", "OBJECT_BINDING_MISMATCH"),
        ("metadata", "METADATA_INVALID"),
        ("sources", "METADATA_SOURCE_MISMATCH"),
        ("duplicate", "JSON_INVALID"),
    ],
)
def test_integrity_and_metadata_failure_before_native_load(tmp_path, change, code):
    f = invented(tmp_path)
    if change == "hash":
        f.config["objects"]["index"]["sha256"] = "0" * 64
    elif change == "etag":
        f.s3.responses[0]["ETag"] = '"def"'
    elif change == "size":
        f.s3.responses[0]["ContentLength"] += 1
    elif change == "sources":
        f.config["metadata"]["source_counts"] = {
            "s3://invented-bucket/docs/other.pdf": 5
        }
        f.config["expected_source"]["source"] = "s3://invented-bucket/docs/other.pdf"
        code = "METADATA_INVALID"
    else:
        raw = b"[{}]" if change == "metadata" else b'[{"chunk_id":0,"chunk_id":1}]'
        f.config["objects"]["metadata"].update(size_bytes=len(raw), sha256=digest(raw))
        f.s3.responses[1].update(Body=io.BytesIO(raw), ContentLength=len(raw))
    with pytest.raises(SmokeStop, match=code):
        run(f)
    assert not f.native.loads and len(f.model.calls) == 1


@pytest.mark.parametrize(
    "change,code",
    [
        ("summarize", "ROUTER_MISROUTE"),
        ("low", "ROUTER_FALLBACK"),
        ("output", "ROUTER_OUTPUT_INVALID"),
        ("exception", "UNCERTAIN_PROVIDER_OUTCOME"),
        ("usage", "USAGE_INVALID"),
        ("retry", "ATTEMPT_COUNT_INVALID"),
        ("hooks", "ATTEMPT_COUNT_INVALID"),
        ("extra", "EXTRA_SEND"),
    ],
)
def test_router_failure_never_reaches_rag(tmp_path, change, code, capsys):
    f = invented(tmp_path)
    response = f.model.responses[0]
    if change in ("summarize", "low"):
        response["output"]["message"]["content"][0]["text"] = json.dumps(
            {
                "task_type": "summarize" if change == "summarize" else "qa",
                "confidence": 0.5 if change == "low" else 0.9,
                "reasoning": SENTINEL,
            }
        )
    elif change == "output":
        response["output"]["message"]["content"][0]["text"] = SENTINEL
    elif change == "exception":
        f.model.responses[0] = TimeoutError(SENTINEL)
    elif change == "usage":
        response["usage"] = {}
    elif change == "retry":
        response["ResponseMetadata"] = {"RetryAttempts": 1}
    elif change == "hooks":
        f.model.skip_hooks = True
    else:
        f.model.send_events = 2
    p = policy(f)
    with pytest.raises(SmokeStop, match=code):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert not f.s3.calls and len(f.model.calls) == 1 and f.model.wire_sends <= 1
    if change in ("exception", "usage", "extra"):
        assert p.exposure["haiku"] == Decimal("0.220352")
    if change in ("retry", "hooks"):
        assert p.exposure["haiku"] == Decimal("0.220429")
        assert p.attempts["router"]["charge_usd"] == "0.000077"
        assert not p.accounting()["exposure_bound_established"]
    assert SENTINEL not in capsys.readouterr().out


@pytest.mark.parametrize(
    "value",
    [
        [],
        [0.0] * 1024,
        [True] * 1024,
        [float("nan")] * 1024,
        [1e308] * 1024,
        [1] * 1023,
    ],
)
def test_embedding_failure_stops_generation_and_closes_body(tmp_path, value):
    f = invented(tmp_path)
    raw = json.dumps({"embedding": value, "inputTextTokenCount": 5}).encode()
    body = io.BytesIO(raw)
    f.model.responses[1]["body"] = body
    with pytest.raises(SmokeStop):
        run(f)
    assert len(f.model.calls) == 2 and body.closed


@pytest.mark.parametrize("field,value", [("d", 512), ("ntotal", 4)])
def test_index_structure_failure_prevents_embedding(tmp_path, field, value):
    f = invented(tmp_path)
    setattr(f.native.index, field, value)
    with pytest.raises(SmokeStop, match="INDEX_STRUCTURE_INVALID"):
        run(f)
    assert len(f.model.calls) == 1


@pytest.mark.parametrize(
    "indices,scores",
    [
        ([0, 1, 2, 3, -1], [1.0] * 5),
        ([0, 1, 2, 3, 5], [1.0] * 5),
        ([0, 1, 2, 3, True], [1.0] * 5),
        ([0, 1, 2, 3, 4], [float("inf")] * 5),
        ([0], [1.0]),
        ([0, 0, 0, 1, 2], [1.0, 0.9, 0.8, 0.7, 0.6]),
        ([0, 1, 2, 3, 4], [0.1, 0.2, 0.3, 0.4, 0.9]),
    ],
)
def test_search_validation_prevents_generation(tmp_path, indices, scores):
    f = invented(tmp_path)
    f.native.index.search = lambda embedding, k: ([scores], [indices])
    with pytest.raises(SmokeStop, match="SEARCH_RESULT_INVALID"):
        run(f)
    assert len(f.model.calls) == 2
    assert [op for op, _ in f.model.calls] == ["Converse", "InvokeModel"]
    assert f.model.wire_sends == 2 and len(f.model.responses) == 1


def replace_invented_metadata(f, sources):
    raw = canonical(
        [
            {"chunk_id": i, "source": source, "text": SENTINEL}
            for i, source in enumerate(sources)
        ]
    )
    f.config["metadata"].update(
        rows=len(sources),
        source_counts={source: sources.count(source) for source in sources},
    )
    f.config["objects"]["metadata"].update(size_bytes=len(raw), sha256=digest(raw))
    f.s3.responses[1].update(Body=io.BytesIO(raw), ContentLength=len(raw))
    f.native.index.ntotal = len(sources)


@pytest.mark.parametrize(
    "hits,minimum",
    [(0, 1), (2, 3)],
)
def test_expected_source_gate_prevents_generation(tmp_path, hits, minimum):
    f = invented(tmp_path)
    expected = f.config["expected_source"]["source"]
    other = "s3://invented-bucket/docs/other-invented.pdf"
    replace_invented_metadata(f, [expected] * hits + [other] * (5 - hits) + [expected])
    f.config["expected_source"]["minimum_hits"] = minimum
    p = policy(f)
    with pytest.raises(SmokeStop, match="^EXPECTED_SOURCE_MISSING$"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert [op for op, _ in f.model.calls] == ["Converse", "InvokeModel"]
    assert f.model.wire_sends == 2 and len(f.model.responses) == 1
    assert f.s3.wire_sends == 2 and len(f.native.loads) == 1
    assert p.halted and current_policy() is None
    assert not list(p.directory.glob("*-complete.json"))


@pytest.mark.parametrize("mixed_sources", [False, True])
def test_tied_scores_and_sufficient_expected_source_hits_allow_generation(
    tmp_path, mixed_sources
):
    f = invented(tmp_path)
    expected = f.config["expected_source"]["source"]
    if mixed_sources:
        other = "s3://invented-bucket/docs/other-invented.pdf"
        replace_invented_metadata(f, [expected, other, expected, other, other])
        f.config["expected_source"]["minimum_hits"] = 2
    else:
        f.config["expected_source"]["minimum_hits"] = 5
    f.native.index.search = lambda embedding, k: (
        [[1.0, 1.0, 0.9, 0.9, 0.8]],
        [[0, 1, 2, 3, 4]],
    )
    p, result = run(f)
    assert f.model.wire_sends == 3
    assert [op for op, _ in f.model.calls] == ["Converse", "InvokeModel", "Converse"]
    hits = sum(
        row["source"] == expected for row in result["result"]["retrieved_context"]
    )
    assert hits >= f.config["expected_source"]["minimum_hits"]
    assert list(p.directory.glob("*-complete.json"))


@pytest.mark.parametrize(
    "condition",
    [
        None,
        {},
        {"source": "s3://invented-bucket/docs/not-allowlisted.pdf", "minimum_hits": 1},
        {"source": None, "minimum_hits": 1},
        {"minimum_hits": 1},
        {"source": "s3://invented-bucket/docs/public-invented.pdf"},
        {"source": "s3://invented-bucket/docs/public-invented.pdf", "minimum_hits": 0},
        {"source": "s3://invented-bucket/docs/public-invented.pdf", "minimum_hits": -1},
        {"source": "s3://invented-bucket/docs/public-invented.pdf", "minimum_hits": 6},
        {
            "source": "s3://invented-bucket/docs/public-invented.pdf",
            "minimum_hits": True,
        },
        {
            "source": "s3://invented-bucket/docs/public-invented.pdf",
            "minimum_hits": 1.0,
        },
        {
            "source": "s3://invented-bucket/docs/public-invented.pdf",
            "minimum_hits": "1",
        },
        {
            "source": "s3://invented-bucket/docs/public-invented.pdf",
            "minimum_hits": 1,
            "opt_out": True,
        },
    ],
)
def test_expected_source_condition_is_mandatory_and_strict(tmp_path, condition):
    f = invented(tmp_path)
    f.config["expected_source"] = condition
    with pytest.raises(SmokeStop, match="^POLICY_INVALID$"):
        policy(f)
    assert not f.model.calls and not f.s3.calls and not f.native.loads
    assert not (tmp_path / "invented-run").exists()


@pytest.mark.parametrize("mode", ["missing", "legacy_missing", "legacy_present"])
def test_missing_condition_and_legacy_policies_cannot_bypass_gate(tmp_path, mode):
    f = invented(tmp_path)
    if mode.startswith("legacy"):
        f.config["schema"] = "rag-smoke-policy-v1"
    if mode != "legacy_present":
        del f.config["expected_source"]
    with pytest.raises(SmokeStop, match="^POLICY_INVALID$"):
        policy(f)
    assert f.model.wire_sends == f.s3.wire_sends == 0
    assert not (tmp_path / "invented-run").exists()


@pytest.mark.parametrize(
    "field,value",
    [("minimum_hits", 2), ("source", "s3://invented-bucket/docs/other-invented.pdf")],
)
def test_expected_source_condition_is_bound_in_claim_policy_hash(
    tmp_path, field, value
):
    f = invented(tmp_path)
    expected = f.config["expected_source"]["source"]
    other = "s3://invented-bucket/docs/other-invented.pdf"
    replace_invented_metadata(f, [expected, expected, other, other, other])
    original_hash = digest(canonical(f.config))
    f.config["expected_source"][field] = value
    changed_hash = digest(canonical(f.config))
    assert changed_hash != original_hash
    p, _ = run(f)
    claim = json.loads((p.directory / "01-claim.json").read_bytes())
    assert claim["policy_sha256"] == changed_hash
    assert f.model.wire_sends == 3


@pytest.mark.parametrize("provider", ["haiku", "total"])
def test_budget_rejected_before_dispatch(tmp_path, provider):
    f = invented(tmp_path)
    f.config["ceilings_usd"][provider] = "0.000001"
    with pytest.raises(SmokeStop, match="RESERVATION_EXHAUSTED"):
        run(f)
    assert not f.model.calls and not f.s3.calls


def test_usage_overrun_reports_actual_not_clamped(tmp_path):
    f = invented(tmp_path)
    f.model.responses[0]["usage"] = {
        "inputTokens": 300000,
        "outputTokens": 100,
        "totalTokens": 300100,
    }
    p = policy(f)
    with pytest.raises(SmokeStop, match="USAGE_OVERRUN"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert p.exposure["haiku"] == Decimal("0.33055") and not f.s3.calls
    usage = [
        json.loads(path.read_bytes()) for path in p.directory.glob("*-usage.json")
    ][0]
    assert usage["overrun"] is True and usage["charge_usd"] == "0.33055"


def test_claim_survives_uncertain_outcome_and_new_policy_cannot_resend(tmp_path):
    f = invented(tmp_path)
    f.model.responses[0] = TimeoutError(SENTINEL)
    with pytest.raises(SmokeStop, match="UNCERTAIN_PROVIDER_OUTCOME"):
        run(f)
    second = invented(tmp_path)
    with pytest.raises(SmokeStop, match="RUN_ALREADY_CLAIMED"):
        run(second)
    assert not second.model.calls and not second.s3.calls


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("retries", {"max_attempts": 0}),
        ("read_timeout", 60),
        ("region_name", "eu-west-1"),
    ],
)
def test_actual_client_configuration_not_environment_is_required(
    tmp_path, attribute, value
):
    f = invented(tmp_path)
    setattr(f.model.meta.config, attribute, value)
    with pytest.raises(SmokeStop, match="CLIENT_CONFIG_INVALID"):
        policy(f)
    assert not f.model.calls and not (tmp_path / "invented-run").exists()


def test_wrong_input_and_missing_policy_do_not_claim_or_dispatch(tmp_path):
    f = invented(tmp_path)
    p = policy(f)
    with pytest.raises(SmokeStop, match="INPUT_BINDING_MISMATCH"):
        CopilotOrchestrator.process_smoke("different", policy=p)
    with pytest.raises(SmokeStop, match="POLICY_REQUIRED"):
        CopilotOrchestrator.process_smoke(QUERY, policy=None)
    assert not f.model.calls and not p.directory.exists()


def test_exact_decimal_reservations_have_no_float_rounding(tmp_path):
    f = invented(tmp_path)
    record = json.loads(f.evidence["haiku"])
    assert charge(200000, 256, record) == Decimal("0.221408")
    assert charge(200000, 64, record) == Decimal("0.220352")


def test_explicit_activation_is_required_for_guarded_requests(tmp_path):
    f = invented(tmp_path)
    p = policy(f)
    with pytest.raises(SmokeStop, match="CHAIN_ORDER_INVALID"):
        p.invoke("router", "Converse", {})
    assert not f.model.calls


def test_metadata_only_body_read_bound_and_failure_closure(tmp_path):
    f = invented(tmp_path)
    body = io.BytesIO(b"too-long")
    f.s3.responses[0]["Body"] = body
    f.config["objects"]["index"]["size_bytes"] = 2
    with pytest.raises(SmokeStop, match="BODY_TOO_LARGE"):
        run(f)
    assert body.closed and not f.native.loads


@pytest.mark.parametrize("stage", ["embedding", "generation"])
def test_missing_usage_retains_stage_reservation_and_stops(tmp_path, stage):
    f = invented(tmp_path)
    if stage == "embedding":
        f.model.responses[1]["body"] = io.BytesIO(
            canonical({"embedding": [1.0] + [0.0] * 1023})
        )
    else:
        f.model.responses[2]["usage"] = {"inputTokens": True, "outputTokens": 5}
    p = policy(f)
    with pytest.raises(SmokeStop, match="USAGE_INVALID"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert not p.attempts[stage]["settled"]
    assert len(f.model.calls) == (2 if stage == "embedding" else 3)
    assert not list(p.directory.glob("*-complete.json"))


def test_embedding_ceiling_blocks_embedding_after_valid_input_load(tmp_path):
    f = invented(tmp_path)
    f.config["ceilings_usd"]["titan"] = "0.00000001"
    with pytest.raises(SmokeStop, match="RESERVATION_EXHAUSTED"):
        run(f)
    assert len(f.model.calls) == 1 and len(f.s3.calls) == 2


def test_partial_stream_error_is_closed_and_not_replaced(tmp_path):
    class Broken(io.BytesIO):
        def read(self, count=-1):
            raise OSError(SENTINEL)

    f = invented(tmp_path)
    broken = Broken()
    f.s3.responses[0]["Body"] = broken
    with pytest.raises(SmokeStop, match="UNCERTAIN_PROVIDER_OUTCOME"):
        run(f)
    assert broken.closed and len(f.s3.calls) == 1 and not f.native.loads


def test_attempt_publication_failure_blocks_dispatch(tmp_path, monkeypatch):
    f = invented(tmp_path)
    p = policy(f)
    original = p._journal

    def fail_attempt(kind, **fields):
        if kind == "attempt":
            p.fail("EVIDENCE_PUBLICATION_FAILED")
        return original(kind, **fields)

    monkeypatch.setattr(p, "_journal", fail_attempt)
    with pytest.raises(SmokeStop, match="EVIDENCE_PUBLICATION_FAILED"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert not f.model.calls and p.directory.exists()


@pytest.mark.parametrize("timeout", [False, True])
def test_real_botocore_config_serializer_and_send_hooks_offline(
    tmp_path, monkeypatch, timeout
):
    import boto3
    import botocore.httpsession
    from botocore.awsrequest import AWSResponse
    from botocore.config import Config
    from botocore.exceptions import ReadTimeoutError

    f = invented(tmp_path)
    # Deliberate summary route stops after this one real-SDK/synthetic-transport call.
    text = json.dumps(
        {"task_type": "summarize", "confidence": 0.9, "reasoning": "invented"}
    )
    payload = canonical(converse_text(text, 20, 10))
    sends = []

    class Raw:
        def stream(self, amt=None, decode_content=False):
            yield payload

    def fake_send(self, request):
        sends.append(request.url)
        if timeout:
            raise ReadTimeoutError(
                endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com"
            )
        return AWSResponse(
            request.url, 200, {"content-type": "application/json"}, Raw()
        )

    monkeypatch.setattr(botocore.httpsession.URLLib3Session, "send", fake_send)
    cfg = Config(
        region_name="us-east-1",
        connect_timeout=2,
        read_timeout=10,
        retries={"total_max_attempts": 1, "mode": "standard"},
    )
    real = boto3.client(
        "bedrock-runtime",
        region_name="us-east-1",
        config=cfg,
        endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com",
    )
    p = SmokePolicy(
        f.config,
        evidence=f.evidence,
        trusted_evidence_hashes=f.hashes,
        claim_directory=f.tmp / f.config["run_id"],
        native=f.native,
    )
    p.bind_clients(bedrock=real, s3=f.s3)
    with pytest.raises(
        SmokeStop, match="UNCERTAIN_PROVIDER_OUTCOME" if timeout else "ROUTER_MISROUTE"
    ):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert len(sends) == 1 and not f.s3.calls
    real.close()


@pytest.mark.parametrize("value", [True, 99])
def test_full_hash_valid_but_row_alignment_invalid_stops_before_native(tmp_path, value):
    f = invented(tmp_path)
    rows = json.loads(f.s3.responses[1]["Body"].getvalue())
    rows[0]["chunk_id"] = value
    raw = canonical(rows)
    f.config["objects"]["metadata"].update(size_bytes=len(raw), sha256=digest(raw))
    f.s3.responses[1].update(Body=io.BytesIO(raw), ContentLength=len(raw))
    with pytest.raises(SmokeStop, match="METADATA_INVALID"):
        run(f)
    assert not f.native.loads and len(f.model.calls) == 1


@pytest.mark.parametrize("change", ["role", "empty", "tool", "content"])
def test_generation_response_contract_failure_retains_known_charge_no_completion(
    tmp_path, change
):
    f = invented(tmp_path)
    response = f.model.responses[2]
    if change == "role":
        response["output"]["message"]["role"] = "user"
    elif change == "empty":
        response["output"]["message"]["content"][0]["text"] = " "
    elif change == "tool":
        response["stopReason"] = "tool_use"
    else:
        response["output"]["message"]["content"].append({"text": SENTINEL})
    p = policy(f)
    with pytest.raises(SmokeStop, match="MODEL_OUTPUT_INVALID"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert p.attempts["generation"]["settled"] and len(f.model.calls) == 3
    assert not list(p.directory.glob("*-complete.json"))


def test_provider_exception_context_does_not_leak_in_formatted_diagnostic(tmp_path):
    import traceback

    f = invented(tmp_path)
    f.model.responses[0] = RuntimeError(SENTINEL)
    with pytest.raises(SmokeStop) as caught:
        run(f)
    assert SENTINEL not in "".join(traceback.format_exception(caught.value))


def test_unencodable_input_is_fixed_rejection_before_claim(tmp_path):
    f = invented(tmp_path)
    p = policy(f)
    with pytest.raises(SmokeStop, match="INPUT_BINDING_MISMATCH"):
        CopilotOrchestrator.process_smoke("\udc00", policy=p)
    assert not p.directory.exists() and not f.model.calls
