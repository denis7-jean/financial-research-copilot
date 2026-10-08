"""Invented events, fake Lambda context/SDK transports, no native execution."""

import ast
import copy
from contextlib import contextmanager
import importlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from app import rag_smoke_handler as smoke
from app.services.rag_smoke_policy import canonical, current_policy, digest, strict_json
from tests import offline_guard
from tests.test_jev_rag_smoke import QUERY, SENTINEL, invented


@pytest.fixture
def run(tmp_path):
    f = invented(tmp_path)
    closed, order, factories = [], [], []
    for name, client in (("bedrock-runtime", f.model), ("s3", f.s3)):
        client.close = lambda name=name: closed.append(name)
        call = client.call

        def recorded(operation, kwargs, original=call):
            order.append(operation)
            return original(operation, kwargs)

        client.call = recorded
    event = {
        "schema": smoke.SCHEMA,
        "query": QUERY,
        "policy_utf8": canonical(f.config).decode(),
        "evidence_utf8": {k: raw.decode() for k, raw in f.evidence.items()},
        "bindings": {
            "policy_sha256": digest(canonical(f.config)),
            "price_evidence_sha256": f.hashes,
        },
    }

    def factory(policy):
        factories.append(policy)
        return {"bedrock-runtime": f.model, "s3": f.s3}

    return SimpleNamespace(
        f=f,
        event=event,
        factory=factory,
        factories=factories,
        closed=closed,
        order=order,
        root=tmp_path,
        context=SimpleNamespace(aws_request_id="invented-context"),
    )


def invoke(run, **kwargs):
    return smoke.handler(
        run.event,
        run.context,
        client_factory=run.factory,
        native=run.f.native,
        claim_root=run.root,
        expected_payload_sha256=digest(canonical(run.event)),
        **kwargs,
    )


def rebind_policy(run, config):
    raw = canonical(config)
    run.event["policy_utf8"] = raw.decode()
    run.event["bindings"]["policy_sha256"] = digest(raw)


def test_real_chain_positive_and_metadata_evidence(run, capsys):
    result = invoke(run)
    assert result["status"] == "STRUCTURAL_SUCCESS" and result["code"] is None
    assert run.order == [
        "Converse",
        "GetObject",
        "GetObject",
        "InvokeModel",
        "Converse",
    ]
    assert run.f.model.wire_sends == 3 and run.f.s3.wire_sends == 2
    assert sorted(run.closed) == ["bedrock-runtime", "s3"]
    assert result["result"]["answer"] == "An invented answer."
    assert len(result["result"]["retrieval"]) == 5
    assert all("text" not in row for row in result["result"]["retrieval"])
    assert set(result["attempts"]) == {
        "router",
        "index",
        "metadata",
        "embedding",
        "generation",
    }
    assert all(
        result["attempts"][stage]["settled"]
        for stage in ("router", "embedding", "generation")
    )
    assert all(
        result[key] is False
        for key in (
            "parent_claim_verified",
            "publication_confirmed",
            "qualification",
            "release_authorized",
        )
    )
    assert result["local_events"][-1]["record"]["kind"] == "complete"
    for event in result["local_events"]:
        raw = (run.root / run.f.config["run_id"] / event["filename"]).read_bytes()
        assert digest(raw) == event["sha256"]
        assert strict_json(raw) == event["record"]
    usage = [
        e["record"] for e in result["local_events"] if e["record"]["kind"] == "usage"
    ]
    assert [(row["input_tokens"], row["output_tokens"]) for row in usage] == [
        (20, 10),
        (5, 0),
        (30, 20),
    ]
    assert len(canonical(result)) <= smoke.MAX_RESULT_BYTES
    logs = capsys.readouterr()
    assert SENTINEL not in logs.out and QUERY not in logs.out
    assert "An invented answer." not in logs.out and logs.err == ""
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("extra_approval", "ENVELOPE_INVALID"),
        ("schema", "ENVELOPE_INVALID"),
        ("query_long", "QUERY_INVALID"),
        ("query_unicode", "QUERY_INVALID"),
        ("query_mismatch", "POLICY_OR_EVIDENCE_INVALID"),
        ("policy_hash", "POLICY_BINDING_MISMATCH"),
        ("price_hash", "POLICY_OR_EVIDENCE_INVALID"),
        ("policy_duplicate", "POLICY_OR_EVIDENCE_INVALID"),
        ("policy_noncanonical", "POLICY_NOT_CANONICAL"),
        ("missing_evidence", "ENVELOPE_INVALID"),
        ("impossible_source", "EXPECTED_SOURCE_IMPOSSIBLE"),
        ("envelope_large", "ENVELOPE_TOO_LARGE"),
    ],
)
def test_malformed_input_creates_no_client_claim_or_send(run, mutation, code):
    if mutation == "extra_approval":
        run.event["owner_approved"] = True
    elif mutation == "schema":
        run.event["schema"] = "unsupported"
    elif mutation.startswith("query_"):
        run.event["query"] = (
            "q" * 301
            if mutation == "query_long"
            else "\ud800"
            if mutation == "query_unicode"
            else "different invented query"
        )
    elif mutation == "policy_hash":
        run.event["bindings"]["policy_sha256"] = "0" * 64
    elif mutation == "price_hash":
        run.event["bindings"]["price_evidence_sha256"]["haiku"] = "0" * 64
    elif mutation == "policy_duplicate":
        run.event["policy_utf8"] = '{"run_id":"a","run_id":"b"}'
        run.event["bindings"]["policy_sha256"] = digest(
            run.event["policy_utf8"].encode()
        )
    elif mutation == "policy_noncanonical":
        run.event["policy_utf8"] = json.dumps(run.f.config, indent=2)
        run.event["bindings"]["policy_sha256"] = digest(
            run.event["policy_utf8"].encode()
        )
    elif mutation == "missing_evidence":
        del run.event["evidence_utf8"]["haiku"]
    elif mutation == "impossible_source":
        config = copy.deepcopy(run.f.config)
        source = config["expected_source"]["source"]
        config["metadata"]["source_counts"] = {
            source: 1,
            source.replace("public-invented", "other-invented"): 4,
        }
        config["expected_source"]["minimum_hits"] = 2
        rebind_policy(run, config)
    else:
        run.event["policy_utf8"] = "x" * (smoke.MAX_EVENT_BYTES + 1)
    result = invoke(run)
    assert (result["status"], result["code"]) == ("STOPPED", code)
    assert not run.factories and not run.order and not list(run.root.iterdir())


def test_trusted_configuration_required_and_event_anchor_cannot_self_approve(
    run, monkeypatch
):
    monkeypatch.delenv(smoke.PAYLOAD_BINDING_VARIABLE, raising=False)
    assert (
        smoke.handler(
            run.event, run.context, client_factory=run.factory, claim_root=run.root
        )["code"]
        == "TRUSTED_PAYLOAD_BINDING_REQUIRED"
    )
    monkeypatch.setenv(smoke.PAYLOAD_BINDING_VARIABLE, "0" * 64)
    assert (
        smoke.handler(
            run.event, run.context, client_factory=run.factory, claim_root=run.root
        )["code"]
        == "PAYLOAD_BINDING_MISMATCH"
    )
    assert not run.factories and not run.order
    monkeypatch.setenv(smoke.PAYLOAD_BINDING_VARIABLE, digest(canonical(run.event)))
    result = smoke.handler(
        run.event,
        run.context,
        client_factory=run.factory,
        native=run.f.native,
        claim_root=run.root,
    )
    assert (
        result["status"] == "STRUCTURAL_SUCCESS"
        and result["release_authorized"] is False
    )


@pytest.mark.parametrize("service", ["s3", "bedrock-runtime"])
@pytest.mark.parametrize(
    "field", ["region", "connect", "read", "retries", "endpoint", "missing_events"]
)
def test_actual_client_settings_reject_before_first_send(run, service, field):
    client = run.f.s3 if service == "s3" else run.f.model
    if field == "region":
        client.meta.config.region_name = "unapproved-region"
    elif field == "connect":
        client.meta.config.connect_timeout = 3
    elif field == "read":
        client.meta.config.read_timeout = 11
    elif field == "retries":
        client.meta.config.retries = {"total_max_attempts": 2, "mode": "standard"}
    elif field == "endpoint":
        client.meta.endpoint_url = "https://invented.invalid"
    else:
        client.meta.events = None
    result = invoke(run)
    assert result["code"] == "CLIENT_CONFIG_INVALID"
    assert not run.order and not list(run.root.iterdir())
    assert sorted(run.closed) == ["bedrock-runtime", "s3"]


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate",
        "increasing",
        "negative",
        "out_of_range",
        "nonfinite",
        "expected_source",
    ],
)
def test_retrieval_failure_prevents_generation_through_handler(run, kind):
    indices, scores = [0, 1, 2, 3, 4], [1.0, 0.9, 0.8, 0.7, 0.6]
    if kind == "duplicate":
        indices[1] = 0
    elif kind == "increasing":
        scores[1] = 1.1
    elif kind == "negative":
        indices[1] = -1
    elif kind == "out_of_range":
        indices[1] = 5
    elif kind == "nonfinite":
        scores[1] = float("nan")
    else:
        config = copy.deepcopy(run.f.config)
        source = config["expected_source"]["source"]
        other = source.replace("public-invented", "other-invented")
        config["metadata"]["rows"] = 6
        config["metadata"]["source_counts"] = {source: 1, other: 5}
        metadata = canonical(
            [
                {"chunk_id": i, "source": source if i == 5 else other, "text": SENTINEL}
                for i in range(6)
            ]
        )
        config["objects"]["metadata"].update(
            size_bytes=len(metadata), sha256=digest(metadata)
        )
        rebind_policy(run, config)
        run.f.s3.responses[1]["Body"] = io.BytesIO(metadata)
        run.f.s3.responses[1]["ContentLength"] = len(metadata)
        run.f.native.index.ntotal = 6
    run.f.native.index.search = lambda embedding, k: ([scores], [indices])
    result = invoke(run)
    assert result["code"] == (
        "EXPECTED_SOURCE_MISSING"
        if kind == "expected_source"
        else "SEARCH_RESULT_INVALID"
    )
    assert run.order == ["Converse", "GetObject", "GetObject", "InvokeModel"]
    assert "generation" not in result["attempts"] and len(run.f.model.responses) == 1


def test_tied_scores_and_expected_source_allow_success(run):
    run.f.native.index.search = lambda embedding, k: ([[1.0] * 5], [[0, 1, 2, 3, 4]])
    assert invoke(run)["status"] == "STRUCTURAL_SUCCESS"


def test_second_send_blocking_visible_uncertainty_and_no_fallback(run):
    run.f.model.send_events = 2
    result = invoke(run)
    assert (result["status"], result["code"]) == ("UNCERTAIN", "EXTRA_SEND")
    assert run.f.model.wire_sends == 1 and not run.f.s3.calls
    assert not result["attempts"]["router"]["settled"]
    assert (
        result["attempts"]["router"]["reservation_usd"]
        == result["exposure_usd"]["haiku"]
    )
    assert run.order == ["Converse"]


@pytest.mark.parametrize(
    "change,code",
    [
        ("timeout", "UNCERTAIN_PROVIDER_OUTCOME"),
        ("missing_usage", "USAGE_INVALID"),
        ("misroute", "ROUTER_MISROUTE"),
        ("low_confidence", "ROUTER_FALLBACK"),
        ("invalid_output", "ROUTER_OUTPUT_INVALID"),
    ],
)
def test_router_stops_sanitized_no_downstream(run, change, code, capsys):
    if change == "timeout":
        run.f.model.responses[0] = TimeoutError(SENTINEL)
    elif change == "missing_usage":
        del run.f.model.responses[0]["usage"]
    else:
        text = (
            "not json " + SENTINEL
            if change == "invalid_output"
            else json.dumps(
                {
                    "task_type": "summarize" if change == "misroute" else "qa",
                    "confidence": 0.1 if change == "low_confidence" else 0.9,
                    "reasoning": SENTINEL,
                }
            )
        )
        run.f.model.responses[0]["output"]["message"]["content"] = [{"text": text}]
    result = invoke(run)
    assert result["code"] == code and result["status"] != "STRUCTURAL_SUCCESS"
    assert run.order == ["Converse"] and result["result"] is None
    assert SENTINEL not in canonical(result).decode()
    assert SENTINEL not in capsys.readouterr().out


def test_known_usage_survives_output_bound_rejection(run):
    run.f.model.responses[2]["output"]["message"]["content"][0]["text"] = "x" * (
        smoke.MAX_ANSWER_BYTES + 1
    )
    result = invoke(run)
    assert result["code"] == "RESULT_TOO_LARGE" and result["result"] is None
    assert result["attempts"]["generation"]["settled"]
    assert result["local_events"][-1]["record"]["kind"] == "complete"
    assert result["publication_confirmed"] is False


def test_duplicate_does_not_touch_prior_local_holds(run):
    assert invoke(run)["status"] == "STRUCTURAL_SUCCESS"
    parent = run.root / run.f.config["run_id"]
    before = {p.name: p.read_bytes() for p in parent.iterdir()}
    order = list(run.order)
    second = invoke(run)
    assert second["code"] == "RUN_ALREADY_CLAIMED"
    assert run.order == order
    assert {p.name: p.read_bytes() for p in parent.iterdir()} == before


def test_failed_local_evidence_remains_uncertain_and_not_confirmed(run, monkeypatch):
    original = Path.open

    def fail(path, mode="r", *args, **kwargs):
        if mode == "xb" and "attempt" in path.name:
            raise OSError(SENTINEL)
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail)
    result = invoke(run)
    assert result["status"] == "UNCERTAIN"
    assert result["code"] == "LOCAL_EVIDENCE_UNAVAILABLE"
    assert not run.order and result["attempts"]["router"]["settled"] is False
    assert (run.root / run.f.config["run_id"]).exists()


def test_total_result_bound_retains_usage_and_local_journals(run, monkeypatch):
    monkeypatch.setattr(smoke, "MAX_RESULT_BYTES", 3500)
    result = invoke(run)
    assert (result["status"], result["code"]) == ("UNCERTAIN", "RESULT_TOO_LARGE")
    assert result["result"] is None and not result["local_events"]
    assert result["attempts"]["generation"]["settled"]
    assert len(canonical(result)) <= 3500
    assert any("usage" in p.name for p in (run.root / run.f.config["run_id"]).iterdir())


def test_client_close_failure_preserves_usage_denies_success(run):
    run.f.model.close = lambda: (_ for _ in ()).throw(OSError(SENTINEL))
    result = invoke(run)
    assert (result["status"], result["code"]) == ("UNCERTAIN", "CLIENT_CLOSE_FAILED")
    assert result["attempts"]["generation"]["settled"] and result["result"] is None


def test_dedicated_factory_explicit_sdk_arguments_with_fake_session(run, monkeypatch):
    import boto3

    calls = []

    class Session:
        def __init__(self, **kwargs):
            assert kwargs == {"region_name": "us-east-1"}

        def client(self, name, **kwargs):
            calls.append((name, kwargs))
            cfg = kwargs["config"]
            assert cfg.retries == {"total_max_attempts": 1, "mode": "standard"}
            assert (cfg.connect_timeout, cfg.read_timeout) == (2, 10)
            assert kwargs["endpoint_url"] == f"https://{name}.us-east-1.amazonaws.com"
            return run.f.model if name == "bedrock-runtime" else run.f.s3

    monkeypatch.setattr(boto3.session, "Session", Session)
    checked = smoke.validate(
        run.event, digest(canonical(run.event)), run.root, run.f.native
    )
    assert set(smoke.dedicated_clients(checked)) == {"bedrock-runtime", "s3"}
    assert [name for name, _ in calls] == ["bedrock-runtime", "s3"]
    assert not run.order


def test_new_handler_import_is_pure_and_p0_not_deployed(monkeypatch):
    import boto3
    import dotenv

    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden import-time activity")

    monkeypatch.setattr(boto3, "client", forbidden)
    monkeypatch.setattr(boto3.session, "Session", forbidden)
    monkeypatch.setattr(dotenv, "load_dotenv", forbidden)
    importlib.reload(smoke)
    tree = ast.parse(Path(smoke.__file__).read_bytes())
    assert all(
        "preinvoke" not in (node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


def test_bad_root_rejects_before_clients(run):
    run.root = run.root / "absent"
    result = invoke(run)
    assert result["code"] == "LOCAL_ROOT_INVALID"
    assert not run.factories and not run.order


def test_missing_session_usage_never_fabricates_settlement(run):
    del run.f.model.responses[1]["body"]
    result = invoke(run)
    assert result["status"] == "UNCERTAIN"
    assert not result["attempts"]["embedding"]["settled"]
    assert run.order == ["Converse", "GetObject", "GetObject", "InvokeModel"]


def test_sdk_retry_mismatch_keeps_n2_limitation_visible(run):
    run.f.model.responses[0]["ResponseMetadata"]["RetryAttempts"] = 1
    result = invoke(run)
    assert result["code"] == "ATTEMPT_COUNT_INVALID"
    assert result["status"] == "UNCERTAIN" and not run.f.s3.calls
    assert not result["attempts"]["router"]["settled"]
    assert "charge_usd" not in result["attempts"]["router"]
    # Existing N2: retry inconsistency prevents accepted policy usage settlement.
    # This test records the limitation, not coverage of already-delivered extras.


def test_cold_smoke_imports_construct_no_ordinary_clients(run, monkeypatch):
    import boto3
    import dotenv

    names = [
        "app.agents.orchestrator",
        "app.agents.qa_agent",
        "app.agents.router",
        "app.services.bedrock_client",
        "app.services.retriever",
    ]
    originals = {name: sys.modules.get(name) for name in names}
    parents = {name: importlib.import_module(name.rsplit(".", 1)[0]) for name in names}
    attributes = {
        name: getattr(parents[name], name.rsplit(".", 1)[1], None) for name in names
    }
    loaders = []

    def forbidden(*args, **kwargs):
        raise AssertionError("ordinary SDK construction forbidden in smoke")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(boto3, "client", forbidden)
            patch.setattr(boto3.session, "Session", forbidden)
            # Metadata-only spy; no file is read. Guard's network hooks stay active.
            patch.setattr(
                dotenv, "load_dotenv", lambda *a, **kw: loaders.append("called")
            )
            for name in names:
                sys.modules.pop(name, None)
            result = invoke(run)
            assert result["status"] == "STRUCTURAL_SUCCESS"
            assert run.order == [
                "Converse",
                "GetObject",
                "GetObject",
                "InvokeModel",
                "Converse",
            ]
            assert sys.modules["app.services.retriever"].s3 is None
            assert sys.modules["app.services.retriever"].bedrock is None
            assert sys.modules["app.services.bedrock_client"].bedrock is None
            # The spy records invocation directly, never reading a dotenv file.
            assert loaders == []
    finally:
        for name in names:
            if originals[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = originals[name]
            parent, attribute = parents[name], name.rsplit(".", 1)[1]
            if attributes[name] is None:
                if hasattr(parent, attribute):
                    delattr(parent, attribute)
            else:
                setattr(parent, attribute, attributes[name])
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


@contextmanager
def cold_chain_loader_spy(monkeypatch):
    """Record real import sites before cold imports; never call the loader."""
    import boto3
    import dotenv

    from tests.conftest import FakeBedrock, converse_text

    names = (
        "app.agents.orchestrator",
        "app.agents.qa_agent",
        "app.agents.router",
        "app.services.bedrock_client",
        "app.services.retriever",
    )
    originals = {name: sys.modules.get(name) for name in names}
    parents = {name: importlib.import_module(name.rsplit(".", 1)[0]) for name in names}
    attributes = {
        name: getattr(parents[name], name.rsplit(".", 1)[1], None) for name in names
    }
    calls, clients = [], []

    def record(*args, **kwargs):
        calls.append(
            (sys._getframe(1).f_globals["__name__"], args, kwargs, current_policy())
        )

    def client(service, **kwargs):
        assert current_policy() is None, "ordinary construction during smoke"
        assert kwargs == {"region_name": "us-east-1"}
        fake = FakeBedrock(
            converse_responses=[
                converse_text('{"task_type":"qa","confidence":1,"reasoning":"fake"}')
            ]
        )
        clients.append((service, fake))
        return fake

    def forbidden(*args, **kwargs):
        raise AssertionError("SDK session forbidden in recording-only test")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(dotenv, "load_dotenv", record)
            patch.setattr(boto3, "client", client)
            patch.setattr(boto3.session, "Session", forbidden)
            for name in names:
                sys.modules.pop(name, None)
            yield SimpleNamespace(calls=calls, clients=clients, patch=patch)
    finally:
        for name in names:
            if originals[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = originals[name]
            parent, attr = parents[name], name.rsplit(".", 1)[1]
            if attributes[name] is None:
                parent.__dict__.pop(attr, None)
            else:
                setattr(parent, attr, attributes[name])
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


@pytest.mark.parametrize("ordinary_first", [True, False])
def test_loader_guard_preserves_ordinary_clients_and_defaults(
    run, monkeypatch, ordinary_first
):
    with cold_chain_loader_spy(monkeypatch) as spy:
        if ordinary_first:
            importlib.import_module("app.agents.qa_agent")
            assert ("app.agents.qa_agent", (), {}, None) in spy.calls
            retriever = sys.modules["app.services.retriever"]
            generation = sys.modules["app.services.bedrock_client"]
            caches = (retriever.s3, retriever.bedrock, generation.bedrock)
            ordinary_index, ordinary_metadata = object(), object()
            retriever._index, retriever._metadata = ordinary_index, ordinary_metadata
            model = generation.BEDROCK_MODEL_ID
        spy.calls.clear()
        prior_clients = len(spy.clients)
        result = invoke(run)
        assert result["status"] == "STRUCTURAL_SUCCESS"
        assert len(run.order) == 5
        assert spy.calls == [] and len(spy.clients) == prior_clients
        assert current_policy() is None
        retriever = sys.modules["app.services.retriever"]
        generation = sys.modules["app.services.bedrock_client"]
        if ordinary_first:
            assert (retriever.s3, retriever.bedrock, generation.bedrock) == caches
            assert retriever._index is ordinary_index
            assert retriever._metadata is ordinary_metadata
            assert generation.BEDROCK_MODEL_ID == model
        else:
            assert retriever.s3 is retriever.bedrock is generation.bedrock is None
            assert retriever._index is retriever._metadata is None

        # Subsequent ordinary use constructs/uses only ordinary fake clients.
        s3 = retriever._ordinary_client("s3")
        embedding = retriever._ordinary_client("bedrock-runtime")
        model_client = generation._ordinary_client()
        assert all(
            c is not run.f.model and c is not run.f.s3
            for c in (s3, embedding, model_client)
        )
        if ordinary_first:
            assert (s3, embedding, model_client) == caches
        else:
            assert spy.calls and all(call[3] is None for call in spy.calls)
        RouterAgent = sys.modules["app.agents.router"].RouterAgent
        router = RouterAgent()
        assert spy.calls[-1] == ("app.agents.router", (), {}, None)
        assert router._model_id == generation.BEDROCK_MODEL_ID
        assert router._model_id == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        assert router.route(QUERY).task_type == "qa"
        spy.patch.setattr(generation, "retrieve_chunks", lambda *a, **kw: [])
        qa = sys.modules["app.agents.qa_agent"].QAAgent()
        assert qa.run(QUERY).answer == generation.NO_EVIDENCE_ANSWER
        assert generation.bedrock is model_client
        assert not model_client.converse_calls and not embedding.invoke_calls
        assert all(call[3] is None for call in spy.calls)


def test_cold_malformed_smoke_never_invokes_loader(run, monkeypatch):
    with cold_chain_loader_spy(monkeypatch) as spy:
        run.event["query"] = ""
        result = invoke(run)
        assert result["status"] == "STOPPED"
        assert not spy.calls and not spy.clients
        assert not run.factories and not run.order
        assert "app.agents.qa_agent" not in sys.modules
        assert "app.services.bedrock_client" not in sys.modules
