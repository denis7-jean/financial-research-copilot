"""CI eval gate. LIVE: makes billable Bedrock calls (system under test + judge).

Thresholds come from eval.metrics.GATES (single source of truth). Only gates
marked enforced can fail the build; report-only gates are printed and written
to the results file.
"""
from dotenv import load_dotenv
load_dotenv()

import json

import pytest

from eval.eval_queries import EVAL_CASES
from eval.llm_judge import run_evaluation
from eval.metrics import GATES

ENFORCED = [gate for gate in GATES if gate.enforced]


@pytest.fixture(scope="module")
def eval_results():
    return run_evaluation()


def _gate(summary: dict, metric: str) -> dict:
    return next(g for g in summary["gates"] if g["metric"] == metric)


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
