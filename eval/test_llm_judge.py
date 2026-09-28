"""CI eval gate. LIVE: makes billable Bedrock calls (system under test + judge).

Runs only when pytest is given --run-live-eval (see the repository-root
conftest.py); otherwise these tests are skipped, or rejected with a usage error
when they are the only tests selected:

    pytest eval/test_llm_judge.py -m llm --run-live-eval -v

Thresholds come from eval.metrics.GATES (single source of truth). Only gates
marked enforced can fail the build; report-only gates are printed and written
to the results file.
"""
# Imported first: importing the tests package installs the offline guard, so this
# module is guarded even if the root conftest.py is bypassed (--noconftest).
from tests import offline_guard

import json

import pytest
from dotenv import load_dotenv

from eval.eval_queries import EVAL_CASES
from eval.llm_judge import run_evaluation
from eval.metrics import GATES

ENFORCED = [gate for gate in GATES if gate.enforced]


def _authorize_live_run(config) -> None:
    """Defense in depth for the paid fixture, independent of the root conftest hooks.

    Skips unless --run-live-eval was given (the option does not exist when the root
    conftest is bypassed, so that case skips too), and fails if the offline guard is
    still installed, which would mean the live run is misconfigured.
    """
    if not config.getoption("run_live_eval", default=False):
        pytest.skip("live, billable evaluation not authorized: pass --run-live-eval")
    if offline_guard.is_installed():
        pytest.fail("offline network guard is still installed; refusing to start a live evaluation")


@pytest.fixture(scope="module")
def eval_results(request):
    _authorize_live_run(request.config)
    load_dotenv()
    return run_evaluation(live=True)


def _gate(summary: dict, metric: str) -> dict:
    return next(g for g in summary["gates"] if g["metric"] == metric)


@pytest.mark.llm
def test_run_is_valid_for_baseline(eval_results) -> None:
    """Separates environment problems from quality results.

    If this fails, the gate numbers below are not a quality verdict: the run was
    affected by infrastructure failures (system, judge or harness) or stopped early.
    """
    validity = eval_results["run_validity"]
    assert validity["valid_for_baseline"], (
        "Run invalidated by infrastructure or completeness problems (not a quality result): "
        + "; ".join(validity["reasons"])
    )


@pytest.mark.llm
@pytest.mark.parametrize("gate", ENFORCED, ids=[g.metric for g in ENFORCED])
def test_enforced_gate(eval_results, gate) -> None:
    result = _gate(eval_results, gate.metric)
    value = result["value"]
    shown = "no data" if value is None else f"{value:.1%}"
    assert result["passed"], (
        f"{gate.metric} = {shown} is below the required {gate.threshold:.0%} "
        f"(population: {gate.population})"
    )


@pytest.mark.llm
def test_results_file_is_from_this_run(eval_results) -> None:
    """Guards against passing on a stale results file."""
    with open(eval_results["results_path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["summary"]["run_id"] == eval_results["run_id"]
    assert data["summary"]["gates"] == eval_results["gates"]


@pytest.mark.llm
def test_every_case_is_reported(eval_results) -> None:
    """Boundary, out-of-corpus and corpus-defect cases must stay visible."""
    with open(eval_results["results_path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert [row["id"] for row in data["results"]] == [case.id for case in EVAL_CASES]
