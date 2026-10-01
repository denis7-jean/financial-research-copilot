"""Owner-registered 100 synthetic fixtures and 37 independent contract checks."""

import json
import re
from experiments.reviewer_protocol_v2.common import require
from experiments.reviewer_protocol_v2.eligibility import (
    PATTERNS,
    P05,
    classify,
    classify_json,
    normalize,
    reference,
    textual,
)

TEXT_FIXTURES = {
    "E01": (
        [
            "What does the table show?",
            "Explain the chart’s purpose.",
            "TABLE",
            "ＴＡＢＬＥ",
        ],
        ["What figures are requested?", "datatable", "tablespoon", "table_name"],
    ),
    "E02": (
        [
            "this report",
            "those consolidated annual statements",
            "provided data",
            "this\ntable",
        ],
        [
            "this, report",
            "this preliminary report",
            "this detailed consolidated annual report",
            "annual reports",
            "their margins",
        ],
    ),
    "E03a": (
        ["preceding passage", "following financial statement", "report above"],
        ["profits above expectations", "the company reported growth"],
    ),
    "E03b": (
        [
            "as shown above",
            "reported immediately below",
            "presented in the preceding report",
        ],
        ["shown profits", "reported in 2020", "displayed clearly above"],
    ),
    "E03c": (
        [
            "in the attached report",
            "from provided data",
            "according to the attached financial statement",
        ],
        ["in the annual report", "from its revenue", "according to management"],
    ),
    "E03d": (
        ["row 3", "rows # 3", "row (a)"],
        ["row3", "row 01", "row 1,000", "row 1.5"],
    ),
    "E03e": (
        ["column B", "column AA", "columns #2"],
        ["column revenue", "column ABCD", "column02"],
    ),
    "E03f": (
        ["cell A1", "cell (BC12)", "cell #3"],
        ["cellA1", "cell A01", "cell A1.5"],
    ),
    "E03g": (
        ["figure 2", "table (b)", "chart # 4"],
        ["figures increased", "figure2", "figure two"],
    ),
    "E04": (
        ["previous question", "earlier responses", "last discussion:"],
        ["last year’s revenue", "previous owner answer", "previously answered"],
    ),
    "E05": (
        ["What does it mean?", "How do they compare.", "Summarize this"],
        [
            "What was its revenue?",
            "Explain their margins.",
            "What is this company’s revenue?",
            "Please explain this",
            "What is this??",
        ],
    ),
    "E06": (
        [
            "[company]",
            "< insert year here >",
            "{{period}}",
            "${value}",
            "__TODO__",
            "Revenue...",
            "Revenue…",
        ],
        [
            "TBD",
            "What does TBD mean?",
            "U.S.",
            "Revenue...then expenses?",
            "Revenue....",
            "Revenue...?",
            "Revenue……",
            '{ "company": "XYZ" }',
            "[company_name]",
        ],
    ),
}


def synthetic_record(question="What was revenue?"):
    return {
        "cand_id": "c_0000000001",
        "question": question,
        "source": "tatqa",
        "sampling_stratum": "T1_qa",
        "source_revision": "fixture-revision",
        "context_group": "fixture-context",
    }


def synthetic_classify(question):
    row = synthetic_record(question)
    return classify(row, {row["cand_id"]: reference(row)})


def registered_results():
    result = []
    for rule, (positive, negative) in TEXT_FIXTURES.items():
        for expected, questions in ((True, positive), (False, negative)):
            for question in questions:
                _, matches = textual(question)
                actual = any(m["subrule"].startswith(rule) for m in matches)
                result.append({"rule": rule, "expected": expected, "actual": actual})
    base = synthetic_record()
    refs = {base["cand_id"]: reference(base)}
    for changes in (
        {"question": None},
        {"question": " \t\n "},
        {"cand_id": "c_fffffffffe"},
        {"source_revision": "wrong"},
        {"context_group": "wrong"},
        {"question": "What was profit?"},
        {"question": "\ud800"},
    ):
        actual = "E07" in classify(base | changes, refs)["rules"]
        result.append({"rule": "E07", "expected": True, "actual": actual})
    raw = json.dumps(base)[:-1] + ',"question":"duplicate"}'
    result.append(
        {
            "rule": "E07",
            "expected": True,
            "actual": "E07" in classify_json(raw, refs)["rules"],
        }
    )
    for question in (
        base["question"],
        "Café 收入是多少？",
        "What does the table show?",
    ):
        result.append(
            {
                "rule": "E07",
                "expected": False,
                "actual": "E07" in synthetic_classify(question)["rules"],
            }
        )
    return result


def additional_results():
    checks = [
        normalize(" \tＴＡＢＬＥ\nStraße\u00a0K ") == "table strasse k",
        len(P05) == 42,
    ]
    cases = (
        ("TABLE", "SCREEN_PASS", {"E01"}),
        ("table-based", "SCREEN_PASS", {"E01"}),
        ("table_name", "SCREEN_PASS", set()),
        ("this report", "DEPENDENCE_EXCLUDED", {"E02"}),
        ("previous answer", "DEPENDENCE_EXCLUDED", {"E04"}),
        ("Explain it.", "DIAGNOSTIC_ONLY", {"E05"}),
        ("[table]", "DIAGNOSTIC_ONLY", {"E01", "E06"}),
        ("this table [company]", "DEPENDENCE_EXCLUDED", {"E01", "E02", "E06"}),
        ("as shown above [table]", "DEPENDENCE_EXCLUDED", {"E01", "E03", "E06"}),
        ("Revenue…", "DIAGNOSTIC_ONLY", {"E06"}),
        ("Revenue……", "SCREEN_PASS", set()),
    )
    for question, disposition, rules in cases:
        actual = synthetic_classify(question)
        checks.extend(
            (actual["disposition"] == disposition, set(actual["rules"]) == rules)
        )
    base = synthetic_record("this table [company]")
    invalid = classify(
        base | {"source_revision": "wrong"}, {base["cand_id"]: reference(base)}
    )
    checks.extend(
        (
            invalid["disposition"] == "INPUT_INVALID",
            set(invalid["rules"]) == {"E01", "E02", "E06", "E07"},
            invalid["text_evaluable"],
        )
    )
    base = synthetic_record()
    refs = {base["cand_id"]: reference(base)}
    missing = {key: value for key, value in base.items() if key != "context_group"}
    for record in (
        [],
        missing,
        base | {"context_group": 1},
        base | {"sampling_stratum": "num"},
        base | {"cand_id": "c_ABCDEF1234"},
    ):
        checks.append(classify(record, refs)["disposition"] == "INPUT_INVALID")
    for question in ("Explain it!", '"Explain it"', "Explain it..", "Explain it? now"):
        checks.append("E05" not in synthetic_classify(question)["rules"])
    checks.append(all(pattern.flags == re.UNICODE for pattern in PATTERNS.values()))
    return checks


def verify_registered():
    fixtures, additional = registered_results(), additional_results()
    require(
        len(fixtures) == 100 and sum(x["expected"] for x in fixtures) == 50,
        "registered_fixture_count",
    )
    require(
        all(x["expected"] == x["actual"] for x in fixtures),
        "registered_fixture_failure",
    )
    require(
        len(additional) == 37 and all(additional), "registered_additional_check_failure"
    )
    return {
        "fixtures_passed": 100,
        "positive": 50,
        "negative": 50,
        "additional_checks_passed": 37,
    }
