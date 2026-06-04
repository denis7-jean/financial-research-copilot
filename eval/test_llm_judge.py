from dotenv import load_dotenv
load_dotenv()

import json
import pytest
from eval.llm_judge import run_evaluation

PASS_THRESHOLD = 0.80


@pytest.fixture(scope="module")
def eval_results():
    return run_evaluation()


@pytest.mark.llm
def test_context_relevance_pass_rate(eval_results) -> None:
    """Context relevance pass rate must meet or exceed 80% threshold."""
    pass_rate = eval_results["context_relevance_pass_rate"]
    assert pass_rate >= PASS_THRESHOLD, (
        f"Context relevance pass rate {pass_rate:.1%} is below "
        f"required threshold of {PASS_THRESHOLD:.1%}"
    )


@pytest.mark.llm
def test_faithfulness_pass_rate(eval_results) -> None:
    """Faithfulness pass rate must meet or exceed 80% threshold."""
    pass_rate = eval_results["faithfulness_pass_rate"]
    assert pass_rate >= PASS_THRESHOLD, (
        f"Faithfulness pass rate {pass_rate:.1%} is below "
        f"required threshold of {PASS_THRESHOLD:.1%}"
    )


@pytest.mark.llm
def test_eval_results_written_to_disk() -> None:
    """Confirm eval/results/latest.json was written and is valid JSON."""
    results_path = "eval/results/latest.json"
    with open(results_path, "r") as f:
        data = json.load(f)
    assert "summary" in data
    assert "context_relevance_pass_rate" in data["summary"]
    assert "faithfulness_pass_rate" in data["summary"]
