"""Post-deploy / CI smoke check for /ask. LIVE when run: each case is one paid request.

Every case is a known in-corpus question. A case passes only if the response is
HTTP 200, carries no error, answers from the documents (not the no-evidence
answer), cites the expected filing and states the expected figure.

Usage:
  python -m scripts.smoke_check --base-url http://localhost:8000 [--case jpm_net_revenue]
"""
import argparse
import sys

NO_EVIDENCE_ANSWER = "No relevant documents found."

SMOKE_CASES: dict[str, dict] = {
    "jpm_net_revenue": {
        "query": "What was JPMorgan Chase's total net revenue for fiscal year 2025?",
        "citation": "jpmorgan-chase-10k-fy2025.pdf",
        "answer_any": ("182,447", "182.4"),
    },
    "visa_net_revenue": {
        "query": "What was Visa's net revenue for fiscal year 2025?",
        "citation": "visa-10k-fy2025.pdf",
        "answer_any": ("40,000", "40.0 billion", "40 billion"),
    },
}


def validate_response(status_code: int, body, case: dict) -> list[str]:
    """Return problems (empty list means the case passed). Pure; no I/O."""
    if status_code != 200:
        detail = body.get("error_detail") if isinstance(body, dict) else None
        return [f"HTTP {status_code} (error_detail={detail})"]
    if not isinstance(body, dict):
        return ["response body is not a JSON object"]
    problems = []
    if "error" in body:
        problems.append(f"application error: {body['error']}")
    if not body.get("trace_id"):
        problems.append("missing trace_id")
    result = body.get("result") or {}
    answer = (result.get("answer") or "").strip()
    if not answer:
        problems.append("empty answer")
    elif answer == NO_EVIDENCE_ANSWER:
        problems.append("no-evidence answer for an in-corpus question")
    citations = result.get("citations") or []
    if not any(case["citation"] in c for c in citations):
        problems.append(f"no citation of {case['citation']} (got {citations})")
    if answer and not any(fact.lower() in answer.lower() for fact in case["answer_any"]):
        problems.append(f"answer lacks expected figure {case['answer_any']}")
    return problems


def run(base_url: str, case_names: list[str], timeout: float = 60.0) -> int:
    import httpx

    failed = 0
    for name in case_names:
        case = SMOKE_CASES[name]
        response = httpx.post(f"{base_url.rstrip('/')}/ask", json={"query": case["query"]}, timeout=timeout)
        try:
            body = response.json()
        except ValueError:
            body = None
        problems = validate_response(response.status_code, body, case)
        trace_id = body.get("trace_id") if isinstance(body, dict) else None
        if problems:
            failed += 1
            print(f"FAIL {name} trace_id={trace_id}: " + "; ".join(problems))
        else:
            print(f"ok   {name} trace_id={trace_id}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--case", action="append", choices=sorted(SMOKE_CASES),
                        help="Run only these cases (default: all)")
    args = parser.parse_args(argv)
    return run(args.base_url, args.case or list(SMOKE_CASES))


if __name__ == "__main__":
    sys.exit(main())
