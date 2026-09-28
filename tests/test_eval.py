"""Unit tests for the evaluation dataset, metrics and harness. No live calls:
the orchestrator, judge client and evidence retrieval are all fakes."""
import json

import pytest

from app import observability
from eval import llm_judge
from eval.eval_queries import (
    BOUNDARY_QUERIES,
    CASES_BY_ID,
    EVAL_CASES,
    EVAL_QUERIES,
    LEGACY_QUERIES_2026_06,
    RETIRED_LEGACY_IDS,
    EvalCase,
)
from eval.metrics import (
    GATES,
    company_for_source,
    company_precision,
    estimate_cost_usd,
    evaluate_gates,
    is_contaminated,
    pass_rate,
    percentile,
)
from tests.conftest import ACCESS_DENIED_MESSAGE, aws_error, converse_text


JPM_SRC = "s3://b/docs/jpmorgan-chase-10k-fy2025.pdf"
GS_SRC = "s3://b/docs/goldman-sachs-10k-fy2025.pdf"
VISA_SRC = "s3://financial-copilot-hl/docs/visa-10k-fy2025.pdf"
VISA_LEGACY_SRC = "s3://financial-copilot-hl/docs/mastercard-10k-fy2025.pdf"


# --- dataset ----------------------------------------------------------------------

def test_case_ids_are_unique():
    assert len(CASES_BY_ID) == len(EVAL_CASES)


def test_active_dataset_has_34_cases():
    assert len(EVAL_CASES) == 34


def test_legacy_queries_are_active_verbatim_or_explicitly_retired():
    legacy_ids = [f"L{i:02d}" for i in range(1, 21)]
    assert len(LEGACY_QUERIES_2026_06) == 20
    for case_id, query in zip(legacy_ids, LEGACY_QUERIES_2026_06):
        if case_id in RETIRED_LEGACY_IDS:
            assert case_id not in CASES_BY_ID
            assert CASES_BY_ID[RETIRED_LEGACY_IDS[case_id]].replaces == case_id
        else:
            assert CASES_BY_ID[case_id].query == query
            assert CASES_BY_ID[case_id].legacy is True
    assert EVAL_QUERIES == [q for i, q in zip(legacy_ids, LEGACY_QUERIES_2026_06) if i not in RETIRED_LEGACY_IDS]
    assert BOUNDARY_QUERIES == list(LEGACY_QUERIES_2026_06[16:])


def test_labels_use_allowed_values():
    for case in EVAL_CASES:
        assert case.expected_route in ("qa", "summarize")
        assert case.route_label_status in ("clear", "needs_review")
        assert case.expected_behavior in ("answer", "abstain", "either")


def test_every_gated_case_has_a_verified_reference():
    gated = [c for c in EVAL_CASES if c.gated_for_retrieval]
    assert len(gated) >= 15
    for case in gated:
        assert case.reference_answer and case.reference_source, case.id
        assert case.companies, case.id


def test_abstain_cases_have_no_reference_answer():
    for case in EVAL_CASES:
        if case.expected_behavior == "abstain":
            assert case.reference_answer is None, case.id


def test_mastercard_questions_are_out_of_corpus_abstentions():
    mastercard = [c for c in EVAL_CASES if "mastercard" in c.query.lower()]
    assert {c.id for c in mastercard} == {"L03", "L08"}
    for case in mastercard:
        assert case.category == "out_of_corpus", case.id
        assert case.expected_behavior == "abstain", case.id
        assert case.reference_answer is None and case.companies == (), case.id
        assert "mastercard" in case.tags, case.id
        # Visa is the nearest in-corpus neighbour; its figures must not leak into the answer.
        assert case.forbidden_facts, case.id


def test_visa_is_the_fifth_company_with_verified_references():
    visa = [c for c in EVAL_CASES if "V" in c.companies]
    assert {c.id for c in visa} == {"N10", "V01", "V02", "V03"}
    for case in visa:
        if case.reference_source:
            assert case.reference_source.startswith("visa-10k-fy2025.pdf"), case.id
    assert CASES_BY_ID["V03"].gated_for_retrieval


def test_reference_sources_only_cite_corpus_files():
    corpus = {"jpmorgan-chase-10k-fy2025.pdf", "goldman-sachs-10k-fy2025.pdf", "bank-of-america-10k-fy2025.pdf",
              "blackrock-10k-fy2025.pdf", "visa-10k-fy2025.pdf"}
    for case in EVAL_CASES:
        if case.reference_source:
            cited = {part.strip().split(" ")[0] for part in case.reference_source.split(";")}
            assert cited <= corpus, (case.id, cited)
        assert "mastercard" not in (case.reference_source or "").lower(), case.id


def test_no_active_case_expects_mastercard_retrieval():
    for case in EVAL_CASES:
        assert "MA" not in case.companies, case.id


def test_needs_review_cases_are_never_in_the_gated_population():
    for case in EVAL_CASES:
        if case.route_label_status == "needs_review":
            assert not case.gated_for_retrieval, case.id


# --- metrics ----------------------------------------------------------------------

@pytest.mark.parametrize("source, ticker", [
    (JPM_SRC, "JPM"),
    (GS_SRC, "GS"),
    ("s3://b/docs/bank-of-america-10k-fy2025.pdf", "BAC"),
    ("s3://b/docs/blackrock-10k-fy2025.pdf", "BLK"),
    ("s3://b/docs/visa-10k-fy2025.pdf", "V"),
    # Legacy object name (Visa content) until the S3 migration is complete.
    ("s3://financial-copilot-hl/docs/mastercard-10k-fy2025.pdf", "V"),
    # Any other Mastercard file is Mastercard, never Visa.
    ("s3://b/docs/mastercard-10k-fy2026.pdf", "MA"),
    ("s3://b/docs/MASTERCARD-10K-FY2025.PDF", "V"),
    ("s3://b/docs/apple-10k.pdf", "UNKNOWN"),
    ("", "UNKNOWN"),
])
def test_company_for_source(source, ticker):
    assert company_for_source(source) == ticker


def test_company_precision_and_contamination():
    sources = [JPM_SRC, JPM_SRC, GS_SRC, JPM_SRC]
    assert company_precision(sources, ("JPM",)) == 0.75
    assert is_contaminated(sources, ("JPM",)) is True
    assert is_contaminated(sources, ("JPM", "GS")) is False
    assert company_precision(sources, ()) is None
    assert is_contaminated([], ("JPM",)) is None


def test_percentile_nearest_rank():
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 100
    assert percentile([], 50) is None
    assert percentile([None, 5], 50) == 5


def test_pass_rate_counts_unjudged_as_failure():
    assert pass_rate([True, None, False, True]) == {"pass_rate": 0.5, "passed": 2, "n": 4}
    assert pass_rate([])["pass_rate"] is None


def test_enforced_thresholds_were_not_lowered():
    enforced = {g.metric: g.threshold for g in GATES if g.enforced}
    assert enforced == {"context_relevance_pass_rate": 0.80, "faithfulness_pass_rate": 0.80}


def test_missing_value_fails_an_enforced_gate():
    values = {g.metric: 1.0 for g in GATES}
    values["faithfulness_pass_rate"] = None
    results, overall = evaluate_gates(values)
    assert overall is False
    assert next(r for r in results if r["metric"] == "faithfulness_pass_rate")["passed"] is False


def test_report_only_gates_do_not_affect_overall():
    values = {g.metric: (1.0 if g.enforced else 0.0) for g in GATES}
    results, overall = evaluate_gates(values)
    assert overall is True
    assert any(not r["passed"] for r in results if not r["enforced"])


def test_threshold_boundary_is_inclusive():
    values = {g.metric: g.threshold for g in GATES}
    _, overall = evaluate_gates(values)
    assert overall is True


def test_estimate_cost_usd():
    calls = [
        {"model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0", "input_tokens": 1_000_000, "output_tokens": 100_000},
        {"model_id": "amazon.titan-embed-text-v2:0", "input_tokens": 1_000_000, "output_tokens": 0},
        {"model_id": "some-unknown-model", "input_tokens": 5, "output_tokens": 5},
    ]
    assert estimate_cost_usd(calls) == {"usd": pytest.approx(1.52), "unpriced_calls": 1}


# --- judge parsing ----------------------------------------------------------------------

@pytest.mark.parametrize("text, expected_score", [
    ('{"score": 4, "reasoning": "ok"}', 4),
    ('```json\n{"score": 5, "reasoning": "ok"}\n```', 5),
    ('Here is my verdict: {"score": 2, "reasoning": "weak"} Thanks.', 2),
    ("no json here", 0),
])
def test_parse_judge_response(text, expected_score):
    assert llm_judge._parse_judge_response(text)["score"] == expected_score


@pytest.mark.parametrize("result, expected", [
    ({"answer": "It was $5B."}, "It was $5B."),
    ({"summary": "S", "key_points": ["a"], "risk_flags": ["r"]}, "Summary: S\nKey points:\n- a\nRisk flags:\n- r"),
    ({"summary": "Parse error", "key_points": [], "risk_flags": []}, ""),
    ({}, ""),
])
def test_answer_text_from_result(result, expected):
    assert llm_judge.answer_text_from_result(result) == expected


# --- harness end-to-end with fakes ----------------------------------------------------------

def _qa_result(answer: str, sources: list[str]) -> dict:
    return {
        "task_type": "qa", "router_confidence": 0.9, "agent_used": "qa", "total_latency_ms": 100.0,
        "result": {"answer": answer, "citations": sorted(set(sources)), "confidence": 1.0, "agent": "qa",
                   "latency_ms": 90.0,
                   "retrieved_context": [{"text": f"chunk {i}", "source": s, "score": 0.5} for i, s in enumerate(sources)]},
    }


def _summary_result(summary: str = "S") -> dict:
    return {
        "task_type": "summarize", "router_confidence": 0.9, "agent_used": "summarize", "total_latency_ms": 50.0,
        "result": {"summary": summary, "key_points": ["k"], "risk_flags": [], "agent": "summarize", "latency_ms": 45.0},
    }


class FakeOrchestrator:
    """Returns canned results per query and records realistic trace data."""

    def __init__(self, results: dict[str, dict]):
        self.results = results
        self.trace_ids = []

    def process(self, query, trace_id=None):
        self.trace_ids.append(trace_id)
        result = self.results[query]
        observability.set_route(router_outcome="model", task_type=result.get("task_type"))
        with observability.stage("route"):
            pass
        observability.record_model_call("router", "us.anthropic.claude-haiku-4-5-20251001-v1:0", 240, 40, 600)
        return result


class FakeJudge:
    """Answers judge prompts from a per-query script; records every request.

    The faithfulness prompt does not include the query, so the script selected
    by the case's preceding context-relevance call is carried forward.
    """

    def __init__(self, script: dict[str, dict], default: dict | None = None):
        self.script = script
        self.default = default or {}
        self.current = self.default
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        system = kwargs["system"][0]["text"]
        user = kwargs["messages"][0]["content"][0]["text"]
        if "User Query: " in user:
            asked = user.split("User Query: ", 1)[1].split("\n", 1)[0]
            self.current = self.script.get(asked, self.default)
        plan = self.current
        if system == llm_judge.CONTEXT_RELEVANCE_PROMPT:
            payload = plan.get("cr", {"score": 5, "reasoning": "r", "pass": True})
        elif system == llm_judge.FAITHFULNESS_PROMPT:
            payload = plan.get("faith", {"score": 5, "reasoning": "r", "pass": True})
        elif system == llm_judge.SUMMARY_GROUNDING_PROMPT:
            payload = plan.get("grounding", {"score": 4, "reasoning": "r"})
        else:
            payload = plan.get("assess", {"abstained": False, "correctness_score": 5, "reasoning": "r"})
        if isinstance(payload, Exception):
            raise payload
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return converse_text(text, input_tokens=4500, output_tokens=60)


def _case(id_, query, **kw) -> EvalCase:
    defaults = dict(category="numeric_qa", expected_route="qa", route_label_status="clear",
                    expected_behavior="answer", companies=("JPM",), reference_answer="$1", reference_source="p1")
    defaults.update(kw)
    return EvalCase(id_, query, **defaults)


def _run(tmp_path, cases, results, judge, evidence=None):
    evidence_calls = []

    def retrieve_evidence(query, n_results=5):
        evidence_calls.append(query)
        return evidence if evidence is not None else [{"content": "ev", "source": JPM_SRC, "score": 0.4}]

    path = tmp_path / "results" / "latest.json"
    summary = llm_judge.run_evaluation(
        cases, orchestrator=FakeOrchestrator(results), client=judge,
        retrieve_evidence=retrieve_evidence, results_path=str(path), sleep_seconds=0,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    return summary, data, evidence_calls


def test_misrouted_gated_case_counts_as_failure_not_exclusion(tmp_path):
    cases = [_case("A", "qa one"), _case("B", "qa two")]
    results = {"qa one": _qa_result("x", [JPM_SRC]), "qa two": _summary_result()}
    summary, data, _ = _run(tmp_path, cases, results, FakeJudge({}))
    assert summary["judged_queries"] == 2
    assert summary["context_relevance_pass_rate"] == 0.5
    assert summary["faithfulness_pass_rate"] == 0.5
    assert summary["retrieval"]["context_relevance"]["failures"] == ["B"]
    assert "no_retrieved_context" in data["results"][1]["context_relevance"]["reasoning"]
    assert summary["routing"]["mismatches"] == ["B"]
    assert summary["overall_pass"] is False


def test_pass_is_computed_from_score_not_the_judges_flag(tmp_path):
    cases = [_case("A", "q")]
    judge = FakeJudge({"q": {"cr": {"score": 2, "pass": True, "reasoning": "r"},
                             "faith": {"score": 3, "pass": True, "reasoning": "r"}}})
    summary, _, _ = _run(tmp_path, cases, {"q": _qa_result("x", [JPM_SRC])}, judge)
    assert summary["context_relevance_pass_rate"] == 0.0
    assert summary["faithfulness_pass_rate"] == 0.0


def test_judge_parse_error_is_a_failure_and_counted(tmp_path):
    cases = [_case("A", "q")]
    throttled = aws_error("ThrottlingException", ACCESS_DENIED_MESSAGE)
    judge = FakeJudge({"q": {"cr": "not json", "faith": throttled}})
    summary, data, _ = _run(tmp_path, cases, {"q": _qa_result("x", [JPM_SRC])}, judge)
    row = data["results"][0]
    assert row["context_relevance"]["pass"] is False and row["context_relevance"]["judge_error"] is True
    assert row["context_relevance"]["judge_infra_error"] is False  # bad output, not an outage
    assert row["faithfulness"]["reasoning"] == "judge_infra_error:throttled:ThrottlingException"
    assert row["faithfulness"]["judge_infra_error"] is True
    assert "123456789012" not in json.dumps(data)  # raw provider message is never stored
    assert summary["errors"]["judge_errors"] == 2
    assert summary["errors"]["judge_infra_errors"] == 1
    assert summary["overall_pass"] is False
    assert summary["run_validity"]["valid_for_baseline"] is False


def test_summarize_path_is_judged_for_grounding_with_harness_evidence(tmp_path):
    cases = [_case("S1", "summarize gs", category="summarize", expected_route="summarize",
                   reference_answer=None, reference_source=None, companies=("GS",))]
    judge = FakeJudge({"summarize gs": {"grounding": {"score": 2, "reasoning": "unsupported"}}})
    summary, data, evidence_calls = _run(tmp_path, cases, {"summarize gs": _summary_result("GS risks")}, judge)
    row = data["results"][0]
    assert evidence_calls == ["summarize gs"]
    assert row["summary_grounding"]["score"] == 2 and row["summary_grounding"]["pass"] is False
    assert row["answer_preview"].startswith("Summary: GS risks")
    assert row["context_relevance"] is None  # not a gated QA case
    assert summary["summary_grounding"]["pass_rate"] == 0.0
    grounding_prompt = next(c for c in judge.calls if c["system"][0]["text"] == llm_judge.SUMMARY_GROUNDING_PROMPT)
    assert "GS risks" in grounding_prompt["messages"][0]["content"][0]["text"]


def test_summary_without_evidence_fails_grounding(tmp_path):
    cases = [_case("S1", "s", expected_route="summarize", reference_answer=None, reference_source=None)]
    summary, data, _ = _run(tmp_path, cases, {"s": _summary_result()}, FakeJudge({}), evidence=[])
    assert data["results"][0]["summary_grounding"]["reasoning"] == "no_evidence_retrieved"


def test_abstention_scoring(tmp_path):
    cases = [
        _case("ABS_OK", "apple", category="out_of_corpus", expected_behavior="abstain",
              companies=(), reference_answer=None, reference_source=None),
        _case("ABS_MISSED", "wells", category="out_of_corpus", expected_behavior="abstain",
              companies=(), reference_answer=None, reference_source=None),
        _case("FALSE_ABS", "gs earnings", companies=("GS",)),
        _case("EITHER", "vague", route_label_status="needs_review", expected_behavior="either",
              reference_answer=None, reference_source=None),
    ]
    results = {q: _qa_result("text", [JPM_SRC]) for q in ("apple", "wells", "gs earnings", "vague")}
    judge = FakeJudge({
        "apple": {"assess": {"abstained": True, "correctness_score": None, "reasoning": "r"}},
        "wells": {"assess": {"abstained": False, "correctness_score": None, "reasoning": "r"}},
        "gs earnings": {"assess": {"abstained": True, "correctness_score": 1, "reasoning": "r"}},
        "vague": {"assess": {"abstained": True, "correctness_score": None, "reasoning": "r"}},
    })
    summary, data, _ = _run(tmp_path, cases, results, judge)
    rows = {r["id"]: r for r in data["results"]}
    assert rows["ABS_OK"]["abstention_appropriate"] is True
    assert rows["ABS_MISSED"]["abstention_appropriate"] is False
    assert rows["FALSE_ABS"]["abstention_appropriate"] is False
    assert rows["EITHER"]["abstention_appropriate"] is None
    assert summary["abstention"]["n"] == 3
    assert summary["abstention"]["false_abstentions"] == ["FALSE_ABS"]
    assert summary["abstention"]["missed_abstentions"] == ["ABS_MISSED"]
    assert summary["answer_correctness"]["failures"] == ["FALSE_ABS"]
    visible = {r["id"] for r in summary["boundary_and_out_of_corpus"]}
    assert {"ABS_OK", "ABS_MISSED"} <= visible


def test_system_error_is_reported_and_fails_correctness(tmp_path):
    cases = [_case("E", "boom")]
    results = {"boom": {"error": "kaboom", "task_type": "unknown", "result": {}}}
    summary, data, _ = _run(tmp_path, cases, results, FakeJudge({}))
    row = data["results"][0]
    assert row["system_error"] == "kaboom"
    assert row["answer_correctness"] == {"score": 0, "pass": False, "reasoning": "empty_answer",
                                         "judge_error": False, "judge_infra_error": False}
    assert row["abstention_appropriate"] is False
    assert summary["errors"]["cases_with_system_errors"] == ["E"]
    assert summary["context_relevance_pass_rate"] == 0.0


def test_contamination_is_measured_without_a_judge(tmp_path):
    cases = [_case("C", "jpm q", companies=("JPM",))]
    results = {"jpm q": _qa_result("x", [JPM_SRC, GS_SRC, JPM_SRC, JPM_SRC])}
    summary, data, _ = _run(tmp_path, cases, results, FakeJudge({}))
    assert data["results"][0]["retrieval"]["company_precision"] == 0.75
    assert summary["retrieval"]["companies"]["contaminated_cases"] == ["C"]


def test_results_file_has_run_id_every_case_and_measurements(tmp_path):
    cases = [_case("A", "a"), _case("B", "b", expected_route="summarize", reference_answer=None,
                                     reference_source=None)]
    results = {"a": _qa_result("x", [JPM_SRC]), "b": _summary_result()}
    summary, data, _ = _run(tmp_path, cases, results, FakeJudge({}))
    assert data["summary"]["run_id"] == summary["run_id"] and len(summary["run_id"]) == 32
    assert [r["id"] for r in data["results"]] == ["A", "B"]
    assert data["summary"]["schema_version"] == 2
    assert summary["latency_ms"]["total_ms"]["n"] == 2
    assert "route" in summary["latency_ms"]["stages_ms"]
    assert summary["tokens"]["system_under_test_by_call"]["router"]["calls"] == 2
    assert summary["tokens"]["judge"]["calls"] > 0
    assert summary["tokens"]["estimated_cost_usd"]["system_under_test"]["usd"] > 0
    assert all(g["metric"] for g in summary["gates"])


def test_each_case_gets_a_distinct_trace_id(tmp_path):
    cases = [_case("A", "a"), _case("B", "b")]
    orch_results = {"a": _qa_result("x", [JPM_SRC]), "b": _qa_result("y", [JPM_SRC])}
    orch = FakeOrchestrator(orch_results)
    llm_judge.run_evaluation(cases, orchestrator=orch, client=FakeJudge({}),
                             retrieve_evidence=lambda q, n_results=5: [], results_path=str(tmp_path / "r.json"),
                             sleep_seconds=0)
    assert len(set(orch.trace_ids)) == 2 and all(orch.trace_ids)


def test_judge_calls_are_deterministic(tmp_path):
    judge = FakeJudge({})
    _run(tmp_path, [_case("A", "a")], {"a": _qa_result("x", [JPM_SRC])}, judge)
    assert all(call["inferenceConfig"] == {"temperature": 0.0, "maxTokens": 400} for call in judge.calls)
    assert all(call["modelId"] == llm_judge.JUDGE_MODEL_ID for call in judge.calls)


def test_legacy_comparable_uses_pre_phase0_population(tmp_path):
    ids = ["L01", "L03", "L12", "L18"]  # qa, qa (Mastercard, out of corpus), summarize, boundary
    cases = [CASES_BY_ID[i] for i in ids]
    results = {
        CASES_BY_ID["L01"].query: _qa_result("x", [JPM_SRC]),
        CASES_BY_ID["L03"].query: _qa_result("not found", [JPM_SRC]),
        CASES_BY_ID["L12"].query: _summary_result(),
        CASES_BY_ID["L18"].query: _qa_result("not found", [JPM_SRC]),
    }
    judge = FakeJudge({CASES_BY_ID["L03"].query: {"cr": {"score": 1, "reasoning": "r"}}})
    summary, _, _ = _run(tmp_path, cases, results, judge)
    assert summary["legacy_comparable"]["n"] == 2  # L01 + L03; summarize and boundary excluded
    assert summary["legacy_comparable"]["context_relevance_pass_rate"] == 0.5
    # The gated population is label-based: only L01 is gated (L03 is expected to abstain).
    assert summary["judged_queries"] == 1
    assert summary["context_relevance_pass_rate"] == 1.0


def test_query_strings_are_accepted_for_backward_compatibility(tmp_path):
    query = LEGACY_QUERIES_2026_06[0]
    summary, data, _ = _run(tmp_path, [query, "an unlabeled query"],
                            {query: _qa_result("x", [JPM_SRC]), "an unlabeled query": _qa_result("y", [JPM_SRC])},
                            FakeJudge({}))
    assert [r["id"] for r in data["results"]] == ["L01", "ADHOC01"]
    assert data["results"][1]["route_label_status"] == "needs_review"


def test_default_results_path_can_be_overridden_by_env(tmp_path, monkeypatch):
    target = tmp_path / "env_path.json"
    monkeypatch.setenv("EVAL_RESULTS_PATH", str(target))
    summary = llm_judge.run_evaluation(
        [_case("A", "a")], orchestrator=FakeOrchestrator({"a": _qa_result("x", [JPM_SRC])}),
        client=FakeJudge({}), retrieve_evidence=lambda q, n_results=5: [], sleep_seconds=0,
    )
    assert summary["results_path"] == str(target)
    assert target.exists()


def test_full_dataset_runs_offline(tmp_path):
    results = {c.query: (_summary_result() if c.expected_route == "summarize" else _qa_result("x", [JPM_SRC]))
               for c in EVAL_CASES}
    summary, data, _ = _run(tmp_path, list(EVAL_CASES), results, FakeJudge({}))
    gated = [c for c in EVAL_CASES if c.gated_for_retrieval]
    assert summary["total_queries"] == len(EVAL_CASES) == 34
    assert summary["judged_queries"] == len(gated) == 19
    assert summary["routing"]["accuracy_all"]["pass_rate"] == 1.0
    assert {r["id"] for r in summary["boundary_and_out_of_corpus"]} == {
        "L03", "L08", "L17", "L18", "L19", "L20", "N11"}
    assert summary["forbidden_fact_leaks"]["cases_checked"] == ["L03", "L08"]
    assert summary["forbidden_fact_leaks"]["leaks"] == {}


def test_visa_figures_in_a_mastercard_answer_are_flagged(tmp_path):
    case = CASES_BY_ID["L03"]
    answer = "Mastercard is not covered, but Visa's net revenue was $40.0 billion."
    judge = FakeJudge({case.query: {"assess": {"abstained": True, "correctness_score": None, "reasoning": "r"}}})
    summary, data, _ = _run(tmp_path, [case], {case.query: _qa_result(answer, [VISA_SRC])}, judge)
    row = data["results"][0]
    assert row["forbidden_fact_hits"] == ["40.0 billion"]
    assert summary["forbidden_fact_leaks"]["leaks"] == {"L03": ["40.0 billion"]}
    # Abstention is judged separately and can still pass.
    assert row["abstention_appropriate"] is True


def test_clean_mastercard_abstention_is_appropriate_and_leak_free(tmp_path):
    case = CASES_BY_ID["L08"]
    answer = "The provided documents do not include Mastercard's filing, so I cannot answer."
    judge = FakeJudge({case.query: {"assess": {"abstained": True, "correctness_score": None, "reasoning": "r"}}})
    summary, data, _ = _run(tmp_path, [case], {case.query: _qa_result(answer, [VISA_SRC])}, judge)
    row = data["results"][0]
    assert row["abstention_appropriate"] is True
    assert row["forbidden_fact_hits"] == []
    assert row["retrieval"]["sources"] == ["V"]
    assert row["retrieval"]["contaminated"] is None  # no expected company for out-of-corpus


def test_visa_question_counts_visa_chunks_as_on_target(tmp_path):
    case = CASES_BY_ID["N10"]
    results = {case.query: _qa_result("$40,000 million", [VISA_SRC, VISA_LEGACY_SRC, JPM_SRC])}
    _, data, _ = _run(tmp_path, [case], results, FakeJudge({}))
    retrieval = data["results"][0]["retrieval"]
    assert retrieval["sources"] == ["V", "V", "JPM"]
    assert retrieval["company_precision"] == pytest.approx(2 / 3)
    assert retrieval["contaminated"] is True


def test_evidence_retrieval_failure_fails_grounding_without_crashing(tmp_path):
    from app.errors import ServiceFailure

    def failing_evidence(query, n_results=5):
        raise ServiceFailure("retrieval.embed", "access_denied", "AccessDeniedException")

    case = _case("S1", "summarize q", expected_route="summarize", reference_answer=None, reference_source=None)
    path = tmp_path / "r.json"
    llm_judge.run_evaluation([case], orchestrator=FakeOrchestrator({"summarize q": _summary_result()}),
                             client=FakeJudge({}), retrieve_evidence=failing_evidence,
                             results_path=str(path), sleep_seconds=0)
    row = json.loads(path.read_text(encoding="utf-8"))["results"][0]
    assert row["summary_grounding"]["pass"] is False
    assert row["summary_grounding"]["reasoning"] == "evidence_retrieval_failed: access_denied at retrieval.embed"


def test_structured_system_errors_are_recorded(tmp_path):
    detail = {"stage": "retrieval.embed", "kind": "access_denied", "code": "AccessDeniedException", "retryable": False}
    results = {"q": {"error": "denied", "error_detail": detail, "task_type": "unknown", "result": {}}}
    summary, data, _ = _run(tmp_path, [_case("A", "q")], results, FakeJudge({}))
    assert data["results"][0]["system_error"] == "denied"
    assert summary["errors"]["cases_with_system_errors"] == ["A"]
    assert summary["context_relevance_pass_rate"] == 0.0



# --- Preflight safeguards: validity, cost ceiling, provenance, legacy protection -------------

def _failure_result(kind: str, stage: str = "retrieval.embed") -> dict:
    return {"error": "e", "error_detail": {"stage": stage, "kind": kind, "code": "X", "retryable": False},
            "task_type": "unknown", "result": {}}


def test_clean_run_is_a_valid_baseline(tmp_path):
    summary, _, _ = _run(tmp_path, [_case("A", "a")], {"a": _qa_result("x", [JPM_SRC])}, FakeJudge({}))
    assert summary["run_validity"]["valid_for_baseline"] is True
    assert summary["run_validity"]["reasons"] == []
    assert summary["completion"]["complete"] is True


@pytest.mark.parametrize("kind, bucket", [
    ("access_denied", "system_infrastructure_failures"),
    ("throttled", "system_infrastructure_failures"),
    ("timeout", "system_infrastructure_failures"),
    ("configuration", "system_infrastructure_failures"),
])
def test_infrastructure_failures_invalidate_the_run(tmp_path, kind, bucket):
    summary, data, _ = _run(tmp_path, [_case("A", "a")], {"a": _failure_result(kind)}, FakeJudge({}))
    validity = summary["run_validity"]
    assert validity["valid_for_baseline"] is False
    assert validity[bucket] == {"A": kind}
    assert data["results"][0]["system_error_detail"]["kind"] == kind


@pytest.mark.parametrize("kind, bucket", [
    ("invalid_model_output", "system_model_output_failures"),
    ("model_error", "system_model_output_failures"),
    ("internal", "application_errors"),
])
def test_model_and_application_failures_are_findings_not_invalidations(tmp_path, kind, bucket):
    summary, _, _ = _run(tmp_path, [_case("A", "a")], {"a": _failure_result(kind)}, FakeJudge({}))
    validity = summary["run_validity"]
    assert validity["valid_for_baseline"] is True
    assert validity[bucket] == ["A"]
    assert summary["context_relevance_pass_rate"] == 0.0  # still a metric failure


def test_degraded_router_invalidates_the_run(tmp_path):
    class DegradedOrchestrator(FakeOrchestrator):
        def process(self, query, trace_id=None):
            from app.errors import ServiceFailure

            observability.record_failure(ServiceFailure("router", "throttled", "ThrottlingException"), fatal=False)
            return super().process(query, trace_id)

    path = tmp_path / "r.json"
    summary = llm_judge.run_evaluation(
        [_case("A", "a")], orchestrator=DegradedOrchestrator({"a": _qa_result("x", [JPM_SRC])}), client=FakeJudge({}),
        retrieve_evidence=lambda q, n_results=5: [], results_path=str(path), sleep_seconds=0)
    assert summary["run_validity"]["degraded_cases"] == {"A": ["throttled"]}
    assert summary["run_validity"]["valid_for_baseline"] is False


def test_harness_evidence_failure_invalidates_the_run(tmp_path):
    from app.errors import ServiceFailure

    def failing(query, n_results=5):
        raise ServiceFailure("retrieval.embed", "throttled", "ThrottlingException")

    case = _case("S", "s", expected_route="summarize", reference_answer=None, reference_source=None)
    summary = llm_judge.run_evaluation([case], orchestrator=FakeOrchestrator({"s": _summary_result()}),
                                       client=FakeJudge({}), retrieve_evidence=failing,
                                       results_path=str(tmp_path / "r.json"), sleep_seconds=0)
    assert summary["run_validity"]["harness_infrastructure_errors"] == 1
    assert summary["run_validity"]["valid_for_baseline"] is False


def test_judge_attempts_are_counted_even_when_invocation_fails(tmp_path):
    judge = FakeJudge({"q": {"cr": aws_error("ServiceUnavailableException", status=503)}})
    summary, _, _ = _run(tmp_path, [_case("A", "q")], {"q": _qa_result("x", [JPM_SRC])}, judge)
    assert summary["tokens"]["judge"]["calls"] == 3  # CR (failed) + faithfulness + assessment
    assert summary["tokens"]["judge"]["invoked"] == 2
    assert summary["run_validity"]["judge_infrastructure_error_kinds"] == ["unavailable"]


def test_cost_ceiling_stops_the_run_and_invalidates_it(tmp_path):
    cases = [_case(f"C{i}", f"q{i}") for i in range(4)]
    results = {c.query: _qa_result("x", [JPM_SRC]) for c in cases}
    path = tmp_path / "r.json"
    summary = llm_judge.run_evaluation(cases, orchestrator=FakeOrchestrator(results), client=FakeJudge({}),
                                       retrieve_evidence=lambda q, n_results=5: [], results_path=str(path),
                                       sleep_seconds=0, max_cost_usd=0.0001)
    assert summary["completion"]["evaluated_cases"] == 1
    assert summary["completion"]["complete"] is False
    assert "cost ceiling" in summary["completion"]["aborted_reason"]
    assert summary["run_validity"]["valid_for_baseline"] is False
    assert len(json.loads(path.read_text(encoding="utf-8"))["results"]) == 1


def test_cost_ceiling_defaults_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("EVAL_MAX_COST_USD", "7.5")
    summary, _, _ = _run(tmp_path, [_case("A", "a")], {"a": _qa_result("x", [JPM_SRC])}, FakeJudge({}))
    assert summary["completion"]["max_cost_usd"] == 7.5


@pytest.mark.parametrize("path", ["eval/results/legacy/new.json", "eval/results/legacy"])
def test_results_can_never_be_written_into_legacy(path):
    with pytest.raises(ValueError, match="legacy"):
        llm_judge.run_evaluation([_case("A", "a")], orchestrator=FakeOrchestrator({}), client=FakeJudge({}),
                                 retrieve_evidence=lambda q, n_results=5: [], results_path=path, sleep_seconds=0)


def test_rows_carry_trace_ids_and_provenance_is_recorded(tmp_path):
    orch = FakeOrchestrator({"a": _qa_result("x", [JPM_SRC])})
    path = tmp_path / "r.json"
    summary = llm_judge.run_evaluation([_case("A", "a")], orchestrator=orch, client=FakeJudge({}),
                                       retrieve_evidence=lambda q, n_results=5: [], results_path=str(path),
                                       sleep_seconds=0)
    row = json.loads(path.read_text(encoding="utf-8"))["results"][0]
    assert row["trace_id"] == orch.trace_ids[0]
    prov = summary["provenance"]
    assert "not the deployed Lambda" in prov["system_under_test"]
    assert len(prov["code"]["git_sha"]) == 40
    assert prov["dataset_sha256"] == llm_judge.dataset_fingerprint([_case("A", "a")])
    assert prov["corpus"] is None  # retriever not loaded with fakes


def test_dataset_fingerprint_changes_with_labels():
    base = llm_judge.dataset_fingerprint(list(EVAL_CASES))
    assert base == llm_judge.dataset_fingerprint(list(EVAL_CASES))
    changed = [_case("L01", EVAL_CASES[0].query, expected_behavior="abstain")] + list(EVAL_CASES[1:])
    assert llm_judge.dataset_fingerprint(changed) != base


def test_corpus_fingerprint_matches_serialized_metadata(monkeypatch):
    import hashlib

    import faiss

    from app.services import retriever

    meta = [{"chunk_id": 0, "source": "s3://b/docs/visa-10k-fy2025.pdf", "text": "t"}]
    index = faiss.IndexFlatIP(4)
    monkeypatch.setattr(retriever, "_index", index)
    monkeypatch.setattr(retriever, "_metadata", meta)
    fp = llm_judge._corpus_fingerprint()
    assert fp == {"index_vectors": 0, "metadata_rows": 1,
                  "metadata_sha256": hashlib.sha256(json.dumps(meta).encode("ascii")).hexdigest()}


# --- Report-only retrieval-quality tracking ------------------------------------------------

JPM_SMOKE_RETRIEVAL = [  # order and content shape observed in the 2026-09-28 production smoke test
    {"text": "Forward-Looking Statements on page 160 and Part I, Item 1A: Risk Factors", "source": JPM_SRC},
    {"text": "fees 1,184 874 697 All other income 563 456 1,037 Noninterest revenue 17,241", "source": JPM_SRC},
    {"text": "95,443 92,583 89,267 Total net revenue 7,025 17,394 8,038 182,447 177,556", "source": JPM_SRC},
    {"text": "lower fair value losses on credit protection", "source": JPM_SRC},
    {"text": "$1.5 trillion of liquidity sources", "source": JPM_SRC},
]


def test_evidence_rank_reproduces_the_jpm_boilerplate_observation():
    from eval.metrics import evidence_ranks

    result = evidence_ranks(JPM_SMOKE_RETRIEVAL, CASES_BY_ID["L01"].evidence)
    assert result["groups"][0]["rank"] == 3
    assert result["all_found"] is True and result["worst_rank"] == 3
    assert result["reciprocal_rank"] == pytest.approx(1 / 3)


def test_evidence_from_another_company_never_matches():
    from eval.metrics import evidence_ranks

    wrong_company = [{"text": "Total net revenue 182,447", "source": GS_SRC}]
    assert evidence_ranks(wrong_company, CASES_BY_ID["L01"].evidence)["all_found"] is False


def test_multi_company_evidence_needs_every_group():
    from eval.metrics import evidence_ranks

    only_jpm = [{"text": "182,447", "source": JPM_SRC}]
    both = only_jpm + [{"text": "Net revenues were $58.28 billion", "source": GS_SRC}]
    evidence = CASES_BY_ID["L10"].evidence
    assert evidence_ranks(only_jpm, evidence)["all_found"] is False
    assert evidence_ranks(only_jpm, evidence)["reciprocal_rank"] == pytest.approx(0.5)
    assert evidence_ranks(both, evidence)["worst_rank"] == 2


def test_cases_without_markers_are_not_tracked():
    from eval.metrics import evidence_ranks

    assert evidence_ranks(JPM_SMOKE_RETRIEVAL, ()) is None


@pytest.mark.parametrize("answer, refs", [
    ("Source: Form 10-K (page 50)", ["page 50"]),
    ("See pages 49-51 and p. 12; also pp. 3", ["pages 49-51", "p. 12", "pp. 3"]),
    ("Total net revenue was $182.447 billion.", []),
    ("The paging system", []),
])
def test_page_references(answer, refs):
    from eval.metrics import page_references

    assert page_references(answer) == refs


def test_tracking_is_reported_but_never_gated(tmp_path):
    case = CASES_BY_ID["L01"]
    answer = "Total net revenue was $182.447 billion. Source: Form 10-K (page 50)"
    result = _qa_result(answer, [JPM_SRC])
    result["result"]["retrieved_context"] = [{**c, "score": 0.7} for c in JPM_SMOKE_RETRIEVAL]
    summary, data, _ = _run(tmp_path, [case], {case.query: result}, FakeJudge({}))
    tracking = summary["retrieval_quality_tracking"]
    assert tracking["evidence_rank"]["evidence_not_top_ranked"] == {"L01": 3}
    assert tracking["unverified_page_references"] == {"L01": ["page 50"]}
    assert data["results"][0]["evidence"]["worst_rank"] == 3
    assert "retrieval_quality_tracking" not in {g["metric"] for g in summary["gates"]}
    assert summary["overall_pass"] is True  # tracking does not affect gates


def test_every_gated_case_has_evidence_markers():
    for case in EVAL_CASES:
        if case.gated_for_retrieval:
            assert case.evidence, case.id
            assert all(ticker in case.companies for ticker, _ in case.evidence), case.id


# --- Phase 0.5 measurement fixes ------------------------------------------------------------

def test_cli_main_prints_gates_and_exits_zero(monkeypatch, capsys, tmp_path):
    """Regression: the baseline run exited 1 because main indexed a Gate dataclass like a dict."""
    real_run_evaluation = llm_judge.run_evaluation

    def fake_run_evaluation():
        return real_run_evaluation(
            [_case("A", "a")], orchestrator=FakeOrchestrator({"a": _qa_result("x", [JPM_SRC])}),
            client=FakeJudge({}), retrieve_evidence=lambda q, n_results=5: [],
            results_path=str(tmp_path / "r.json"), sleep_seconds=0)

    monkeypatch.setattr(llm_judge, "run_evaluation", fake_run_evaluation)
    assert llm_judge.main() == 0
    out = capsys.readouterr().out
    assert "Enforced gates: ['context_relevance_pass_rate', 'faithfulness_pass_rate']" in out
    assert "Valid for baseline: True" in out


def test_refusal_cannot_count_as_grounded_summary(tmp_path):
    """Regression: L19 and N14 scored 5 for grounding while refusing to summarize."""
    refusing = _case("R", "overview please", category="summarize", expected_route="summarize",
                     reference_answer=None, reference_source=None)
    grounded = _case("G", "summarize risks", category="summarize", expected_route="summarize",
                     reference_answer=None, reference_source=None)
    judge = FakeJudge({
        "overview please": {"grounding": {"score": 5, "reasoning": "no claims to contradict"},
                            "assess": {"abstained": True, "correctness_score": None, "reasoning": "declined"}},
        "summarize risks": {"grounding": {"score": 4, "reasoning": "supported"},
                            "assess": {"abstained": False, "correctness_score": None, "reasoning": "ok"}},
    })
    results = {"overview please": _summary_result("I don't have access to the filing"),
               "summarize risks": _summary_result("Risks include credit and market risk")}
    summary, data, _ = _run(tmp_path, [refusing, grounded], results, judge)
    rows = {r["id"]: r for r in data["results"]}
    assert rows["R"]["summary_grounding"]["pass"] is False
    assert rows["R"]["summary_grounding"]["refusal"] is True
    assert rows["R"]["summary_grounding"]["judge_score"] == 5 and rows["R"]["summary_grounding"]["score"] == 0
    assert rows["G"]["summary_grounding"]["pass"] is True and rows["G"]["summary_grounding"]["refusal"] is False
    grounding = summary["summary_grounding"]
    assert grounding["pass_rate"] == 0.5
    assert grounding["refusals"] == ["R"]
    assert grounding["substantive"] == {"n": 1, "grounded_rate": 1.0}


@pytest.mark.parametrize("abstained, expected_pass", [(True, False), (False, True), (None, True)])
def test_apply_refusal_rule(abstained, expected_pass):
    judged = {"score": 5, "pass": True, "reasoning": "r", "judge_error": False, "judge_infra_error": False}
    assert llm_judge.apply_refusal_rule(judged, abstained)["pass"] is expected_pass
    assert llm_judge.apply_refusal_rule(None, True) is None


# Chunk texts copied from the indexed metadata (rows noted), trimmed around the evidence.
JPM_ROE_SEGMENT_TABLE = ("Net income 4,520 10,601 2,821 57,048 58,471 49,552 "
                         "Return on equity (“ROE”) NM NM NM 17 % 18 % 17 %")  # row 1620
JPM_ROE_NARRATIVE = "reported net income of $57.0 billion for 2025, down 2%, earnings per share of $20.02, ROE of 17%"  # 1603
GS_ROE_TABLE = "Diluted EPS $ 51.32 $ 40.54 $ 22.87 ROE 15.0% 12.7% 7.5% ROTE 16.0% 13.5% 8.1%"  # row 794
GS_ROE_SEGMENT = "Average common equity $ 108,726 $ 106,774 Return on average common equity 15.0% 12.7% 7.5%"  # 803


@pytest.mark.parametrize("case_id, text, source", [
    ("L06", JPM_ROE_SEGMENT_TABLE, JPM_SRC),
    ("L06", JPM_ROE_NARRATIVE, JPM_SRC),
    ("L06", "Return on common equity (“ROE”) 17 % 18 % 17 %", JPM_SRC),
    ("N06", GS_ROE_TABLE, GS_SRC),
    ("N06", GS_ROE_SEGMENT, GS_SRC),
    ("N06", "ROE was 15.0% for 2025, compared with 12.7% for 2024.", GS_SRC),
])
def test_roe_evidence_alternatives_match_genuine_phrasings(case_id, text, source):
    from eval.metrics import evidence_ranks

    result = evidence_ranks([{"text": "boilerplate", "source": source}, {"text": text, "source": source}],
                            CASES_BY_ID[case_id].evidence)
    assert result["all_found"] is True and result["worst_rank"] == 2


@pytest.mark.parametrize("case_id, text, source", [
    ("L06", "Return on equity (“ROE”) 32 % 32 % 38 % 18 % 18 % 14 %", JPM_SRC),  # segment ROEs, not firm
    ("L06", "Return on equity 18 % 17 %", JPM_SRC),  # 17% is the 2024 value in 2025/2024 order
    ("L06", "ROE of 17%", GS_SRC),  # right phrase, wrong company
    ("N06", "ROE 12.7% 15.0%", GS_SRC),  # wrong year order
    ("N06", "Return on average common equity 16.0%", GS_SRC),
    ("N06", "ROE was 15.0%", JPM_SRC),  # wrong company
])
def test_roe_evidence_is_not_weakened(case_id, text, source):
    from eval.metrics import evidence_ranks

    assert evidence_ranks([{"text": text, "source": source}], CASES_BY_ID[case_id].evidence)["all_found"] is False


def test_single_alternative_markers_still_require_every_string():
    from eval.metrics import evidence_ranks, marker_alternatives

    assert marker_alternatives(("a", "b")) == [("a", "b")]
    assert marker_alternatives((("a",), ("b", "c"))) == [("a",), ("b", "c")]
    evidence = (("JPM", ("Return on common equity", "17 %")),)
    assert evidence_ranks([{"text": "Return on common equity 18 %", "source": JPM_SRC}], evidence)["all_found"] is False
