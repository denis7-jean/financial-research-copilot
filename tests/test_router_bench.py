"""Router benchmark: payload, allowlist, routers (raw vs final), Jev schema, metrics. Offline only."""
import json
from dataclasses import replace

import httpx
import pytest

from eval.routing_datasets import routing_dataset
from experiments.router_bench import metrics as bench_metrics
from experiments.router_bench import payload as jev_payload
from experiments.router_bench.config import JEV_ENDPOINT, JEV_MODEL
from experiments.router_bench.routers import (
    RULES_SHA256,
    HaikuRouter,
    JevClient,
    JevRouter,
    JevSchemaError,
    RulesRouter,
    final_decision,
    rules_fingerprint,
    validate_jev_response,
)
from experiments.router_bench.safety import OfflineFakeClient, SecretValue
from tests.conftest import FakeBedrock, aws_error, converse_text


class ScriptedBedrock(OfflineFakeClient, FakeBedrock):
    """tests.conftest.FakeBedrock, explicitly marked as an offline fake for the benchmark."""

V2 = routing_dataset("v2")
CASES = {c.id: c for c in V2}
ALL_IDS = [c.id for c in V2]


def _approved(ids=ALL_IDS):
    return jev_payload.ApprovedQuestions(V2, ids)


# --- Frozen payload and allowlist ---------------------------------------------------------------

def test_criteria_are_verbatim_from_the_router_prompt():
    from app.agents.router import _SYSTEM_PROMPT

    assert jev_payload.QA_CRITERION in _SYSTEM_PROMPT
    assert jev_payload.SUMMARIZE_CRITERION in _SYSTEM_PROMPT


def test_payload_and_rules_fingerprints_are_pinned():
    assert jev_payload.payload_fingerprint() == jev_payload.PAYLOAD_TEMPLATE_SHA256
    assert rules_fingerprint() == RULES_SHA256


def test_payload_carries_only_the_approved_question_and_the_frozen_template():
    payload = jev_payload.build_jev_payload(CASES["L01"], _approved())
    template = jev_payload.payload_template()
    assert payload["state"] == CASES["L01"].query
    assert {k: v for k, v in payload.items() if k != "state"} == {k: v for k, v in template.items() if k != "state"}
    assert payload["model"] == JEV_MODEL


def test_unapproved_ids_and_altered_question_text_are_refused():
    with pytest.raises(jev_payload.QuestionNotApproved, match="not on the approved list"):
        jev_payload.build_jev_payload(CASES["L17"], _approved(["L01", "L12"]))
    chunk = "JPMorgan Chase & Co. Annual Report ... net revenue of $182.4 billion ... " * 5
    with pytest.raises(jev_payload.QuestionNotApproved, match="differs from the frozen dataset"):
        jev_payload.build_jev_payload(replace(CASES["L01"], query=chunk), _approved())
    with pytest.raises(jev_payload.QuestionNotApproved, match="not in the dataset"):
        jev_payload.ApprovedQuestions(V2, ["L01", "ZZ99"])


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(context="retrieved chunk text"),
    lambda p: p.update(state="What was revenue? " + "x" * 400),
    lambda p: p.update(state="not an approved question"),
    lambda p: p["questions"]["route"]["criteria"].update(qa="changed"),
    lambda p: p.update(model="jev-latest"),
], ids=["extra-field", "stuffed-question", "free-text", "changed-criteria", "unpinned-model"])
def test_outgoing_validation_rejects_anything_but_the_frozen_request(mutate):
    payload = jev_payload.build_jev_payload(CASES["L01"], _approved())
    mutate(payload)
    with pytest.raises(Exception, match="payload|document text|forbidden key"):
        jev_payload.validate_outgoing(payload, _approved())


# --- Raw prediction vs final decision -----------------------------------------------------------

@pytest.mark.parametrize("raw, score, expected", [
    (None, None, ("qa", "fallback_invoke_error")),
    ("summarize", 0.59, ("qa", "fallback_low_score")),
    ("summarize", 0.6, ("summarize", "model")),
    ("qa", None, ("qa", "model")),
])
def test_final_decision_rule(raw, score, expected):
    assert final_decision(raw, score, "fallback_invoke_error") == expected


def _haiku(*responses):
    return HaikuRouter(bedrock_client=ScriptedBedrock(converse_responses=list(responses)))


def test_haiku_records_raw_and_final_for_a_model_decision():
    router = _haiku(converse_text('{"task_type": "summarize", "confidence": 0.9, "reasoning": "r"}', 210, 50))
    record = router.route(CASES["L12"])
    assert (record.raw_label, record.raw_score, record.final_label, record.outcome) == ("summarize", 0.9, "summarize", "model")
    assert (record.input_tokens, record.output_tokens, record.cost_basis) == (210, 50, "usage")
    assert record.cost_usd == pytest.approx(210e-6 + 250e-6)
    assert "decision_mismatch" not in record.extra


def test_haiku_low_confidence_keeps_the_raw_label_from_the_trace():
    router = _haiku(converse_text('{"task_type": "summarize", "confidence": 0.4, "reasoning": "r"}'))
    record = router.route(CASES["L12"])
    assert (record.raw_label, record.raw_score) == ("summarize", 0.4)
    assert (record.final_label, record.outcome) == ("qa", "fallback_low_score")
    assert record.extra["router_outcome"] == "fallback_low_confidence"
    assert "decision_mismatch" not in record.extra  # our rule reproduces RouterAgent's decision


def test_haiku_parse_and_invoke_errors_have_no_raw_label():
    parse = _haiku(converse_text("not json")).route(CASES["L01"])
    assert (parse.raw_label, parse.final_label, parse.outcome, parse.infra_error) == (None, "qa", "fallback_parse_error", False)
    invoke = _haiku(aws_error("ThrottlingException", status=429)).route(CASES["L01"])
    assert (invoke.raw_label, invoke.outcome, invoke.infra_error) == (None, "fallback_invoke_error", True)
    assert (invoke.cost_usd, invoke.cost_basis) == (None, "none")  # unknown usage: runner charges worst case


def test_rules_router_is_deterministic_and_free():
    router = RulesRouter()
    first = [router.route(c).final_label for c in V2]
    assert first == [router.route(c).final_label for c in V2]
    record = router.route(CASES["L12"])
    assert (record.raw_label, record.raw_score, record.outcome, record.cost_usd) == ("summarize", None, "rules", 0.0)


# --- Jev: schema validation and errors (httpx.MockTransport only) ---------------------------------

def _jev_body(choice="qa", p=0.9, **overrides):
    other = "summarize" if choice == "qa" else "qa"
    body = {"model": JEV_MODEL,
            "answers": {"route": {"choice": choice, "probabilities": {choice: p, other: round(1 - p, 6)},
                                  "confidence": round(2 * p - 1, 6)}},
            "usage": {"input_tokens": 180, "output_tokens": 2}}
    body.update(overrides)
    return body


def _jev_router(handler, api_key=None):
    client = JevClient(transport=httpx.MockTransport(handler), api_key=api_key)
    return JevRouter(client, _approved())


def test_jev_valid_response_records_probability_as_raw_score():
    record = _jev_router(lambda req: httpx.Response(200, json=_jev_body("summarize", 0.8))).route(CASES["L12"])
    assert (record.raw_label, record.raw_score, record.final_label, record.outcome) == ("summarize", 0.8, "summarize", "model")
    assert record.extra["jev_confidence"] == pytest.approx(0.6)  # recorded, not used for the decision
    assert record.cost_usd == pytest.approx(180 * 0.042e-6)


def test_jev_low_probability_falls_back_to_qa():
    record = _jev_router(lambda req: httpx.Response(200, json=_jev_body("summarize", 0.55))).route(CASES["L12"])
    assert (record.raw_label, record.final_label, record.outcome) == ("summarize", "qa", "fallback_low_score")


@pytest.mark.parametrize("body, code", [
    (_jev_body(model="jev-latest"), "model_mismatch"),
    ({**_jev_body(), "answers": {"route": {"choice": "qa", "probabilities": {"qa": 0.9, "summarize": 0.9},
                                           "confidence": 0.8}}}, "probabilities_do_not_sum_to_1"),
    ({**_jev_body(), "answers": {"route": {"choice": "qa", "probabilities": {"qa": 0.3, "summarize": 0.7},
                                           "confidence": 0.4}}}, "choice_not_argmax"),
    ({**_jev_body(), "answers": {"route": {"choice": "other", "probabilities": {"qa": 0.5, "summarize": 0.5},
                                           "confidence": 0.0}}}, "bad_choice"),
    ({k: v for k, v in _jev_body().items() if k != "usage"}, "usage_missing"),
    ({**_jev_body(), "usage": {"input_tokens": 0, "output_tokens": 0}}, "bad_input_tokens"),
])
def test_jev_schema_violations(body, code):
    with pytest.raises(JevSchemaError) as excinfo:
        validate_jev_response(body)
    assert excinfo.value.code == code and str(excinfo.value) == code
    record = _jev_router(lambda req: httpx.Response(200, json=body)).route(CASES["L01"])
    assert (record.raw_label, record.final_label, record.outcome) == (None, "qa", "fallback_schema_error")
    assert (record.error_class, record.cost_basis) == (f"schema:{code}", "none")


@pytest.mark.parametrize("status, error_class", [
    (401, "auth"), (403, "auth"), (422, "contract"), (429, "throttled"), (529, "overloaded"), (500, "unavailable"),
])
def test_jev_http_errors_are_classified_without_the_body(status, error_class):
    record = _jev_router(lambda req: httpx.Response(status, json={"echo": "server text"})).route(CASES["L01"])
    assert (record.outcome, record.infra_error, record.error_class, record.http_status) == (
        "fallback_invoke_error", True, error_class, status)
    assert "server text" not in json.dumps(record.to_dict())


def test_jev_timeout_is_an_infrastructure_error():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    record = _jev_router(handler).route(CASES["L01"])
    assert (record.outcome, record.error_class, record.infra_error) == ("fallback_invoke_error", "timeout", True)


def test_api_key_reaches_only_the_authorization_header():
    canary = "ts-canary-9f3a-not-a-real-key"
    seen = []

    def handler(request):
        seen.append({"auth": request.headers.get("authorization"), "body": request.content.decode()})
        return httpx.Response(200, json=_jev_body())

    record = _jev_router(handler, api_key=SecretValue(canary)).route(CASES["L01"])
    assert seen[0]["auth"] == f"Bearer {canary}"
    assert canary not in seen[0]["body"]
    assert canary not in json.dumps(record.to_dict())
    assert canary not in repr(SecretValue(canary)) and canary not in str(SecretValue(canary))


def test_only_allowlisted_response_headers_are_kept():
    headers = {"x-request-id": "r1", "x-ratelimit-remaining": "99", "set-cookie": "s=1", "date": "d"}
    record = _jev_router(lambda req: httpx.Response(200, headers=headers, json=_jev_body())).route(CASES["L01"])
    assert record.extra["response_headers"] == {"x-request-id": "r1", "x-ratelimit-remaining": "99", "date": "d"}


def test_the_request_sent_is_exactly_the_frozen_payload():
    sent = []

    def handler(request):
        sent.append((str(request.url), request.method, sorted(k.lower() for k in request.headers),
                     json.loads(request.content)))
        return httpx.Response(200, json=_jev_body())

    _jev_router(handler).route(CASES["L01"])
    url, method, header_names, body = sent[0]
    assert (url, method) == (JEV_ENDPOINT, "POST")
    assert "authorization" not in header_names  # no key in dry runs and tests
    assert body == jev_payload.build_jev_payload(CASES["L01"], _approved())


# --- Metrics ------------------------------------------------------------------------------------

def _record(router, cid, rep, final, raw=None, score=None, outcome="model", latency=100.0, infra=False):
    return {"router": router, "case_id": cid, "repetition": rep, "warmup": rep == 0,
            "raw_label": raw if raw is not None else final, "raw_score": score, "final_label": final,
            "outcome": outcome, "latency_ms": latency, "infra_error": infra, "input_tokens": 10,
            "output_tokens": 1, "cost_usd": 0.001, "cost_basis": "usage"}


def _perfect(router, reps=3, latency=100.0):
    return [_record(router, c.id, rep, c.expected_route, latency=latency + rep) for rep in range(1, reps + 1)
            for c in V2]


def test_metrics_views_denominators_and_criteria():
    records = _perfect("haiku", latency=900.0) + _perfect("jev", latency=100.0)
    records += [_record("jev", "L01", 0, "summarize")]  # a wrong warm-up call: excluded
    m = bench_metrics.compute(records, V2, ("haiku", "jev"), seed=1)
    jev = m["per_router"]["jev"]
    assert (jev["strict_accuracy"]["majority"]["passed"], jev["strict_accuracy"]["majority"]["n"]) == (31, 31)
    assert (jev["strict_accuracy"]["pooled"]["correct"], jev["strict_accuracy"]["pooled"]["n"]) == (93, 93)
    assert jev["strict_accuracy"]["per_repetition"] == {"n_per_repetition": 31, "min": 31, "median": 31, "max": 31}
    assert (jev["recall"]["majority"]["summarize"]["passed"], jev["recall"]["majority"]["summarize"]["n"]) == (7, 7)
    assert jev["policy_compliance_report_only"]["L19"]["complied_with_raw_label"] == 3
    assert jev["exploratory_predictions"] == {"L17": {"qa": 3}, "L20": {"qa": 3}}
    assert m["agreement"]["haiku~jev"]["kappa_strict"] == pytest.approx(1.0)
    assert m["criteria"]["jev"]["checks"]["p95_latency_vs_haiku"] is True
    assert m["criteria"]["jev"]["meets_follow_up_criteria"] is True
    assert m["criteria"]["haiku"]["meets_follow_up_criteria"] is None  # the control is not a candidate


def test_metrics_fallbacks_policy_split_stability_and_infra():
    records = _perfect("jev", reps=4)
    for r in records:
        if r["case_id"] == "L12" and r["repetition"] <= 2:  # summarize case falls back to qa twice
            r.update(final_label="qa", raw_label="summarize", raw_score=0.55, outcome="fallback_low_score")
        if r["case_id"] == "L19":
            if r["repetition"] == 1:
                r.update(raw_label="summarize", raw_score=0.5, final_label="qa", outcome="fallback_low_score")
            elif r["repetition"] == 2:
                r.update(raw_label="summarize", final_label="summarize")
        if r["case_id"] == "N01" and r["repetition"] == 1:
            r.update(raw_label=None, final_label="qa", outcome="fallback_invoke_error", infra_error=True)
    jev = bench_metrics.compute(records, V2, ("jev",), seed=1)["per_router"]["jev"]
    assert jev["policy_compliance_report_only"]["L19"] == {
        "policy": "unclear_defaults_to_qa", "required": "qa", "n": 4,
        "complied_with_raw_label": 2, "complied_via_fallback": 1, "not_complied": 1}
    assert jev["fallback"]["by_reason"] == {"fallback_low_score": 3, "fallback_invoke_error": 1}
    assert jev["fallback"]["correct_by_fallback_on_clear_qa"] == 1  # N01 fell back to its correct label
    assert jev["infra_errors"]["count"] == 1 and jev["infra_errors"]["invalid"] is False  # 1/136 < 1%
    assert jev["strict_accuracy"]["errors_majority"] == ["L12"]  # 2-2 tie counts as wrong
    assert "L12" not in jev["stability_report_only"]["unstable_cases"]  # raw label stable; only the final fell back
    assert jev["stability_report_only"]["unstable_cases"]["N01"] == 0.25
    assert jev["raw_label_accuracy_report_only"]["pooled"]["correct"] == 123  # 124 clear decisions, 1 missing raw
