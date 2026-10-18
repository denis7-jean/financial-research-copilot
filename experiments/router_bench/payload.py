"""The frozen Jev request and the approved-question allowlist.

A TypeSafe request carries exactly two kinds of text:
- the approved question text of an allowlisted case ID, looked up in the pinned
  routing dataset (never free text);
- the fixed instruction and criteria below, copied verbatim from the
  RouterAgent taxonomy (a test checks they still match app/agents/router.py).
Nothing else: no trace IDs, metadata, documents or retrieved chunks.
"""
import copy
import hashlib
import json

from experiments.router_bench.config import JEV_MODEL
from experiments.router_bench.safety import ArtifactSafetyError, assert_safe_for_output

INSTRUCTIONS = "Classify this financial research query into exactly one category."
QA_CRITERION = (
    "The user wants a specific fact, figure, or answer retrieved from financial documents.\n"
    "Examples: revenue numbers, earnings per share, debt levels, headcount, specific dates, "
    "comparisons between two figures."
)
SUMMARIZE_CRITERION = (
    "The user wants a high-level overview, narrative summary, or analysis of risks, themes, or trends.\n"
    "Examples: summarize annual report, explain key risks, describe business strategy, overview of performance."
)
LABELS = ("qa", "summarize")
STATE_PLACEHOLDER = "<approved question text>"
MAX_QUESTION_CHARS = 300  # approved questions are <= 90 chars; blocks document stuffing


def payload_template() -> dict:
    return {
        "state": STATE_PLACEHOLDER,
        "model": JEV_MODEL,
        "questions": {"route": {"type": "choice", "instructions": INSTRUCTIONS,
                                "criteria": {"qa": QA_CRITERION, "summarize": SUMMARIZE_CRITERION}}},
    }


def payload_fingerprint() -> str:
    return hashlib.sha256(json.dumps(payload_template(), sort_keys=True).encode("utf-8")).hexdigest()


PAYLOAD_TEMPLATE_SHA256 = "54e2deaa70a529ca7eb70d5e896c6118e8a7993b228013ca3b9e53ec8f67c0c9"


class QuestionNotApproved(RuntimeError):
    """A case ID outside the allowlist, or a question text that differs from the frozen dataset."""


class ApprovedQuestions:
    """The approved case IDs of one run, bound to the frozen dataset's question text."""

    def __init__(self, dataset_cases, allowed_ids):
        index = {case.id: case for case in dataset_cases}
        missing = [i for i in allowed_ids if i not in index]
        if missing:
            raise QuestionNotApproved(f"allowlisted IDs not in the dataset: {missing}")
        if len(set(allowed_ids)) != len(allowed_ids):
            raise QuestionNotApproved("duplicate IDs in the allowlist")
        self.ids = tuple(allowed_ids)
        self._text = {i: index[i].query for i in self.ids}

    def text_for(self, case) -> str:
        if case.id not in self._text:
            raise QuestionNotApproved(f"case {case.id} is not on the approved list for this run")
        if case.query != self._text[case.id]:
            raise QuestionNotApproved(f"case {case.id}: question text differs from the frozen dataset")
        return self._text[case.id]


def build_jev_payload(case, approved: ApprovedQuestions) -> dict:
    payload = payload_template()
    payload["state"] = approved.text_for(case)
    validate_outgoing(payload, approved)
    return payload


def validate_outgoing(payload: dict, approved: ApprovedQuestions) -> None:
    """Last check before anything is sent to TypeSafe."""
    template = payload_template()
    if set(payload) != set(template):
        raise ArtifactSafetyError("payload fields differ from the frozen template", "payload_template")
    rest = copy.deepcopy(payload)
    state = rest.pop("state")
    template.pop("state")
    if rest != template:
        raise ArtifactSafetyError("payload model, instruction or criteria differ from the frozen template",
                                  "payload_template")
    if not isinstance(state, str) or state not in approved._text.values() or len(state) > MAX_QUESTION_CHARS:
        raise ArtifactSafetyError("payload question is not an approved question text", "payload_question")
    assert_safe_for_output(payload, what="TypeSafe request")
