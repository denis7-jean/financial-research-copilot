"""Invented accounting observations; no extra real send, native or SDK I/O."""

from decimal import Decimal
from fractions import Fraction
import io
from pathlib import Path

import pytest

from app.agents.orchestrator import CopilotOrchestrator
from app.services.rag_smoke_policy import SmokeStop, canonical, digest, strict_json
from tests.test_jev_rag_smoke import QUERY, SENTINEL, invented, policy
from tests import test_jev_rag_smoke_handler as handler_tests
from tests.test_jev_rag_smoke_handler import invoke


@pytest.fixture
def handler_run(tmp_path):
    return handler_tests.run.__wrapped__(tmp_path)


@pytest.mark.parametrize("retries", [1, 2, 100, None, True, SENTINEL, {}])
def test_retry_inconsistency_keeps_valid_usage_without_inventing_deliveries(
    tmp_path, retries
):
    f = invented(tmp_path)
    f.model.responses[0]["ResponseMetadata"]["RetryAttempts"] = retries
    p = policy(f)
    with pytest.raises(SmokeStop, match="ATTEMPT_COUNT_INVALID"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    entry = p.attempts["router"]
    assert entry["usage"] == {"inputTokens": 20, "outputTokens": 10}
    assert entry["charge_usd"] == "0.000077"
    assert not entry["settled"] and entry["hold_usd"] == "0.220352"
    assert entry["usage_attribution"] == "UNATTRIBUTED_RESPONSE"
    assert p.exposure["haiku"] == Decimal("0.220429")
    assert not p.accounting()["exposure_bound_established"]
    assert not p.accounting()["ceiling_established"]
    assert p.extra_requests == []  # Retry metadata never supplies exact sends.
    assert len(f.model.calls) == f.model.wire_sends == 1 and not f.s3.calls
    assert SENTINEL not in canonical(entry).decode()
    journal = strict_json(next(p.directory.glob("*-usage.json")).read_bytes())
    assert journal["usage_scope"] == "RETURNED_RESPONSE_ONLY"
    assert journal["charge_usd"] == entry["charge_usd"]


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"inputTokens": True, "outputTokens": 0},
        {"inputTokens": -1, "outputTokens": 0},
        {"inputTokens": 1, "outputTokens": 0, "totalTokens": 2},
    ],
)
def test_invalid_usage_is_never_promoted_by_retry_metadata(tmp_path, usage):
    f = invented(tmp_path)
    f.model.responses[0]["ResponseMetadata"]["RetryAttempts"] = 1
    f.model.responses[0]["usage"] = usage
    p = policy(f)
    with pytest.raises(SmokeStop, match="USAGE_INVALID"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert "charge_usd" not in p.attempts["router"]
    assert p.exposure["haiku"] == Decimal("0.220352")
    assert p.accounting()["known_charges_usd"]["haiku"] == "0"
    assert not p.accounting()["exposure_bound_established"]
    assert not f.s3.calls


def test_blocked_second_send_has_no_fabricated_delivery_or_charge(tmp_path):
    f = invented(tmp_path)
    f.model.send_events = 2
    p = policy(f)
    with pytest.raises(SmokeStop, match="EXTRA_SEND"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert f.model.wire_sends == 1 and not f.s3.calls
    assert p.attempts["router"]["send_checks"] == {
        "callbacks": 2,
        "approved_before_send": 1,
        "blocked_before_send": 1,
    }
    extra = p.extra_requests[0]
    assert extra["delivery"] == "NO" and extra["usage"] is None
    assert extra["charge_usd"] is None and not extra["approved"]
    assert p.exposure["haiku"] == Decimal("0.220352")
    assert p.accounting()["known_charges_usd"]["haiku"] == "0"


def observe_extra(
    f,
    p,
    *,
    delivery="YES",
    usage=None,
    lose_original_response=False,
    stage="router",
    count=1,
    binding=None,
):
    original = f.model.call

    def observed(operation, kwargs):
        response = original(operation, kwargs)
        # The fake transport supplies independent observations of a bypassed
        # request; we never weaken/call the real pre-send gate to let one through.
        for ordinal in range(count):
            f.model.wire_sends += 1
            p.record_extra_request(
                stage,
                delivery=delivery,
                usage=usage,
                **(
                    binding
                    or {
                        "model_id": f.config["models"][
                            "titan" if stage == "embedding" else "haiku"
                        ],
                        "region": "us-east-1",
                        "tier": "standard",
                    }
                ),
                request_evidence_sha256=digest(
                    canonical(
                        {
                            "invented_request": ordinal,
                            "stage": stage,
                            "delivery": delivery,
                            "usage": usage,
                        }
                    )
                ),
            )
        if lose_original_response:
            raise TimeoutError(SENTINEL)
        return response

    f.model.call = observed


@pytest.mark.parametrize(
    "delivery,usage",
    [
        ("YES", {"inputTokens": 10, "outputTokens": 2}),
        ("YES", None),
        ("UNKNOWN", None),
        ("UNKNOWN", {"inputTokens": 10, "outputTokens": 2}),
        ("YES", {"inputTokens": True, "outputTokens": 0}),
    ],
)
def test_observed_extra_preserves_its_own_charge_or_unknown_exposure(
    tmp_path, delivery, usage
):
    f = invented(tmp_path)
    p = policy(f)
    observe_extra(f, p, delivery=delivery, usage=usage)
    with pytest.raises(SmokeStop, match="EXTRA_REQUEST_OBSERVED"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert f.model.wire_sends == 2 and not f.s3.calls
    assert p.attempts["router"]["settled"]
    assert p.attempts["router"]["charge_usd"] == "0.000077"
    extra = p.extra_requests[0]
    assert (
        extra["reservation_usd"] == "0"
        and not extra["approved"]
        and not extra["settled"]
    )
    valid = usage is not None and type(usage["inputTokens"]) is int
    assert extra["charge_usd"] == ("0.000022" if valid else None)
    assert p.exposure["haiku"] == Decimal("0.000099" if valid else "0.000077")
    assert p.accounting()["exposure_bound_established"] == (delivery == "YES" and valid)
    assert not p.accounting()["ceiling_established"]
    assert SENTINEL not in canonical(p.accounting()).decode()
    with pytest.raises(SmokeStop, match="RUN_ALREADY_CLAIMED"):
        with p.activate(QUERY):
            pass


def test_contract_s41_three_unit_hold_plus_one_unit_extra(tmp_path):
    f = invented(tmp_path)
    prices = strict_json(f.evidence["haiku"])
    prices.update(
        input_token_bound=3, input_usd_per_million="1000000", output_usd_per_million="0"
    )
    f.evidence["haiku"] = canonical(prices)
    f.hashes["haiku"] = digest(f.evidence["haiku"])
    f.config["ceilings_usd"].update(haiku="3", total="3.01")
    p = policy(f)
    observe_extra(
        f, p, usage={"inputTokens": 1, "outputTokens": 0}, lose_original_response=True
    )
    with pytest.raises(SmokeStop, match="UNCERTAIN_PROVIDER_OUTCOME"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    scenario = next(
        row
        for row in strict_json(
            (
                Path(__file__).parent / "fixtures/jev_rag_smoke_acceptance.json"
            ).read_bytes()
        )["scenarios"]
        if row["id"].startswith("S41-")
    )
    units = scenario["exposure_units"]
    assert Decimal(p.attempts["router"]["hold_usd"]) == Decimal(units["retained_hold"])
    assert Decimal(p.extra_requests[0]["charge_usd"]) == Decimal(
        units["unreserved_actual"]
    )
    assert p.exposure["haiku"] == Decimal(units["recorded_total"]) == Decimal(4)
    assert p.accounting()["reservation_coverage"] == "VIOLATED"
    assert not p.accounting()["ceiling_established"]
    assert p.accounting()["known_charges_usd"]["haiku"] == "1"
    assert p.accounting()["retained_holds_usd"]["haiku"] == "3"
    assert f.model.wire_sends == 2 and not f.s3.calls


def test_distinct_extra_requests_never_share_usage_or_a_reservation(tmp_path):
    f = invented(tmp_path)
    p = policy(f)
    observe_extra(f, p, usage={"inputTokens": 10, "outputTokens": 2}, count=2)
    with pytest.raises(SmokeStop, match="EXTRA_REQUEST_OBSERVED"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert len(p.extra_requests) == 2 and f.model.wire_sends == 3
    assert len({row["request_evidence_sha256"] for row in p.extra_requests}) == 2
    assert p.exposure["haiku"] == Decimal("0.000121")
    assert p.accounting()["known_charges_usd"]["haiku"] == "0.000121"
    assert all(not row["settled"] for row in p.extra_requests)
    assert not f.s3.calls


@pytest.mark.parametrize(
    "field,value",
    [("model_id", SENTINEL), ("region", "eu-west-1"), ("tier", "unapproved-tier")],
)
def test_unknown_extra_pricing_binding_keeps_usage_without_inventing_charge(
    tmp_path, field, value
):
    f = invented(tmp_path)
    p = policy(f)
    binding = {
        "model_id": f.config["models"]["haiku"],
        "region": "us-east-1",
        "tier": "standard",
    }
    binding[field] = value
    observe_extra(f, p, usage={"inputTokens": 10, "outputTokens": 2}, binding=binding)
    with pytest.raises(SmokeStop, match="EXTRA_REQUEST_OBSERVED"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    extra = p.extra_requests[0]
    assert extra["usage_status"] == "VALID_UNPRICED"
    assert extra["usage"] == {"inputTokens": 10, "outputTokens": 2}
    assert extra["charge_usd"] is None
    assert not p.accounting()["exposure_bound_established"]
    assert not p.accounting()["ceiling_established"]
    assert SENTINEL not in canonical(extra).decode()
    assert not f.s3.calls


def test_known_zero_cost_extra_is_still_unauthorized_and_stops(tmp_path):
    f = invented(tmp_path)
    p = policy(f)
    observe_extra(f, p, usage={"inputTokens": 0, "outputTokens": 0})
    with pytest.raises(SmokeStop, match="EXTRA_REQUEST_OBSERVED"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert p.extra_requests[0]["charge_usd"] == "0.00"
    assert not p.extra_requests[0]["approved"] and not p.extra_requests[0]["settled"]
    assert not f.s3.calls and p.halted


def test_embedding_retry_usage_is_preserved_without_generation(tmp_path):
    f = invented(tmp_path)
    f.model.responses[1]["ResponseMetadata"]["RetryAttempts"] = 1
    p = policy(f)
    with pytest.raises(SmokeStop, match="ATTEMPT_COUNT_INVALID"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    entry = p.attempts["embedding"]
    assert entry["usage"] == {"inputTokens": 5, "outputTokens": 0}
    assert entry["charge_usd"] == "1E-7" and not entry["settled"]
    assert p.exposure["titan"] == Decimal("0.0000021")
    assert len(f.model.calls) == 2 and len(f.model.responses) == 1


def test_untrusted_embedding_payload_does_not_rescue_a_usage_field(tmp_path):
    f = invented(tmp_path)
    f.model.responses[1]["body"] = io.BytesIO(
        b'{"inputTextTokenCount":5,"inputTextTokenCount":7}'
    )
    f.model.responses[1]["ResponseMetadata"]["RetryAttempts"] = 1
    p = policy(f)
    with pytest.raises(SmokeStop, match="JSON_INVALID"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    assert "charge_usd" not in p.attempts["embedding"]
    assert p.accounting()["known_charges_usd"]["titan"] == "0"
    assert len(f.model.calls) == 2


def test_generation_retry_usage_survives_real_qa_failure_seam(handler_run):
    # The original invented factory shares metadata; replace this record so the
    # probe reaches generation rather than inadvertently changing routing.
    handler_run.f.model.responses[2]["ResponseMetadata"] = {"RetryAttempts": 1}
    result = invoke(handler_run)
    assert result["schema"] == "rag-smoke-handler-result-v2"
    assert result["status"] == "UNCERTAIN" and result["code"] == "ATTEMPT_COUNT_INVALID"
    entry = result["attempts"]["generation"]
    assert entry["charge_usd"] == "0.000143" and not entry["settled"]
    assert entry["hold_usd"] == entry["reservation_usd"]
    assert entry["usage_attribution"] == "UNATTRIBUTED_RESPONSE"
    assert result["accounting"]["known_charges_usd"]["haiku"] == "0.000220"
    assert handler_run.order == [
        "Converse",
        "GetObject",
        "GetObject",
        "InvokeModel",
        "Converse",
    ]
    assert result["result"] is None and not result["publication_confirmed"]


def test_mismatch_overrun_charge_is_exact_and_unclamped(tmp_path):
    f = invented(tmp_path)
    incoming = 10**90 + 7
    f.model.responses[0]["usage"] = {"inputTokens": incoming, "outputTokens": 0}
    f.model.responses[0]["ResponseMetadata"]["RetryAttempts"] = 1
    p = policy(f)
    with pytest.raises(SmokeStop, match="ATTEMPT_COUNT_INVALID"):
        CopilotOrchestrator.process_smoke(QUERY, policy=p)
    # Integer rational arithmetic establishes the expected unrounded charge.
    actual = Decimal(p.attempts["router"]["charge_usd"])
    assert actual.as_integer_ratio() == (incoming * 11, 10_000_000)
    assert Fraction(p.exposure["haiku"]) == Fraction(actual) + Fraction(
        Decimal("0.220352")
    )
    assert p.accounting()["known_charges_usd"]["haiku"] == str(actual)
    assert not p.attempts["router"]["settled"] and not f.s3.calls
    assert p.accounting()["reservation_coverage"] == "VIOLATED"


def test_reused_extra_evidence_cannot_consume_a_distinct_request(tmp_path):
    f = invented(tmp_path)
    p = policy(f)
    evidence = digest(b"invented independent request proof")
    with pytest.raises(SmokeStop, match="CHAIN_INCOMPLETE"):
        with p.activate(QUERY):
            p.record_extra_request(
                "router",
                delivery="YES",
                request_evidence_sha256=evidence,
                model_id=f.config["models"]["haiku"],
                region="us-east-1",
                tier="standard",
                usage={"inputTokens": 1, "outputTokens": 0},
            )
            with pytest.raises(SmokeStop, match="EXTRA_EVIDENCE_INVALID"):
                p.record_extra_request(
                    "router",
                    delivery="YES",
                    request_evidence_sha256=evidence,
                    model_id=f.config["models"]["haiku"],
                    region="us-east-1",
                    tier="standard",
                    usage={"inputTokens": 2, "outputTokens": 0},
                )
            assert len(p.extra_requests) == 1
            assert not p.accounting()["exposure_bound_established"]
            assert p.accounting()["known_charges_usd"]["haiku"] == "0.0000011"
            with pytest.raises(SmokeStop, match="CHAIN_ORDER_INVALID"):
                p.invoke("router", "Converse", {})
            assert not f.model.calls and not f.s3.calls


def test_handler_retains_accounting_bounds_sanitization_and_duplicate_holds(
    handler_run, monkeypatch
):
    f = handler_run.f
    factory = handler_run.factory

    def observed_factory(p):
        clients = factory(p)
        observe_extra(f, p, delivery="UNKNOWN")
        return clients

    handler_run.factory = observed_factory
    result = invoke(handler_run)
    assert (
        result["status"] == "UNCERTAIN" and result["code"] == "EXTRA_REQUEST_OBSERVED"
    )
    assert not result["accounting"]["exposure_bound_established"]
    assert result["accounting"]["extra_requests"][0]["delivery"] == "UNKNOWN"
    assert all(
        result[key] is False
        for key in (
            "publication_confirmed",
            "parent_claim_verified",
            "release_authorized",
            "qualification",
        )
    )
    assert handler_run.order == ["Converse"]
    directory = handler_run.root / f.config["run_id"]
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    again = invoke(handler_run)
    assert again["code"] == "RUN_ALREADY_CLAIMED"
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    assert handler_run.order == ["Converse"]
    assert SENTINEL not in canonical(result).decode()


def test_handler_overflow_keeps_known_extra_and_full_local_bindings(
    handler_run, monkeypatch
):
    from app import rag_smoke_handler as handler

    factory = handler_run.factory

    def observed_factory(p):
        clients = factory(p)
        observe_extra(handler_run.f, p, usage={"inputTokens": 10, "outputTokens": 2})
        return clients

    handler_run.factory = observed_factory
    monkeypatch.setattr(handler, "MAX_RESULT_BYTES", 3500)
    result = invoke(handler_run)
    assert result["code"] == "RESULT_TOO_LARGE" and result["status"] == "UNCERTAIN"
    assert len(canonical(result)) <= 3500
    assert result["accounting"]["known_charges_usd"]["haiku"] == "0.000099"
    assert result["accounting"]["extra_request_count"] == 1
    assert "extra_requests" not in result["accounting"]
    rows = [
        strict_json(p.read_bytes())
        for p in (handler_run.root / handler_run.f.config["run_id"]).glob(
            "*-extra-request.json"
        )
    ]
    assert rows[0]["charge_usd"] == "0.000022" and not rows[0]["settled"]
    assert not result["publication_confirmed"]
