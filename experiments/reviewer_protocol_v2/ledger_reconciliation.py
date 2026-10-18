"""Identified captured-byte counts and technical joins; no adoption or operations."""

from datetime import datetime

from experiments.reviewer_protocol_v2.common import (
    ProtocolError,
    canonical,
    require,
    sha_bytes,
)
from experiments.reviewer_protocol_v2.control_serialization import (
    object_bytes,
    object_header,
    relative_path,
    text,
)
from experiments.reviewer_protocol_v2.selection import exact_keys, hex256

TARGET = dict(
    manifest="057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4",
    ledger="6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2",
    generating="105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc",
    historical_source="d3030b229c498db254ba936352d40262a24ad2df5a114fa2c0432d69f8811e37",
    current_source="04e36326c5445419a5e9ec0e6517c4d9623c52f6688c27b095005da597c3cc92",
    lemma="febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef",
)
SOURCE_PATH = "main/experiments/reviewer_protocol_v2/eligibility.py"
COUNT_KEYS = (
    "total_rows",
    "e03_rows",
    "e03c_rows",
    "union_rows",
    "normalized_empty_question_rows",
)
COUNT_PROCEDURE = dict(
    schema="reviewer-protocol-v2-ledger-count-procedure-v1",
    parse="STRICT_UTF8_UNIQUE_KEYS_FINITE_CANONICAL_JSONL_FINAL_LF_NO_BLANK_ROWS",
    structure="OBJECT_ELIGIBILITY_EXACT_SIX_FIELDS_TYPED_RULES_MATCHES_INVALID_SCALARS",
    matches="EXACT_RULE_SUBRULE_SPAN_TEXT_NONNEGATIVE_ORDERED_INTEGER_SPAN",
    total_rows="COUNT_ROWS",
    e03_rows="ROW_HAS_E03_IN_ELIGIBILITY_RULES",
    e03c_rows="ROW_HAS_ANY_E03C_SUBRULE_IN_ELIGIBILITY_MATCHES",
    union_rows="ROW_HAS_E03_OR_E03C",
    normalized_empty_question_rows="ROW_HAS_NORMALIZED_EMPTY_QUESTION_IN_ELIGIBILITY_INVALID",
    evaluation="NO_CLASSIFICATION_NORMALIZATION_OR_SELECTION",
)
RECONCILIATION_CONTRACT = dict(
    schema="reviewer-protocol-v2-ledger-reconciliation-contract-v1",
    scope="IDENTIFIED_MANIFEST_LEDGER_GENERATING_DIGEST_SOURCE_TRANSITION_AND_LEMMA_ONLY",
    counts=dict(zip(COUNT_KEYS, (104, 0, 0, 0, 0), strict=True)),
    proof="REVIEWED_ELIGIBILITY_OBJECT_EQUALITY_NOT_DISPOSITION_ONLY",
    review="EXACT_SUBJECT_CONTRACT_LEMMA_COUNTS_AND_RAW_RECORD_HASH",
    result="TECHNICAL_BINDINGS_ONLY_NOT_AUTHENTICATED_APPROVAL_OR_ADOPTION",
)


def checked_read(binding, read):
    exact_keys(binding, ("path", "sha256"), "RECONCILIATION_FILE_BINDING")
    relative_path(binding["path"])
    hex256(binding["sha256"])
    raw = read(binding)
    require(
        type(raw) is bytes and sha_bytes(raw) == binding["sha256"],
        "RECONCILIATION_ARTIFACT_HASH",
    )
    return raw


def count_ledger(raw):
    """Inspect stored fields only. No question evaluation, identities or row output."""
    require(
        type(raw) is bytes and raw.endswith(b"\n"), "RECONCILIATION_LEDGER_STRUCTURE"
    )
    counts = dict.fromkeys(COUNT_KEYS, 0)
    try:
        for line in raw.split(b"\n")[:-1]:
            row = object_bytes(line + b"\n")
            eligibility = row.get("eligibility")
            exact_keys(
                eligibility,
                (
                    "rules",
                    "matches",
                    "invalid",
                    "disposition",
                    "text_evaluable",
                    "normalized",
                ),
                "RECONCILIATION_LEDGER_STRUCTURE",
            )
            for key in ("rules", "invalid"):
                require(
                    type(eligibility[key]) is list
                    and all(type(v) is str for v in eligibility[key]),
                    "RECONCILIATION_LEDGER_STRUCTURE",
                )
            require(
                all(
                    rule in {"E01", "E02", "E03", "E04", "E05", "E06", "E07"}
                    for rule in eligibility["rules"]
                ),
                "RECONCILIATION_LEDGER_STRUCTURE",
            )
            require(
                eligibility["disposition"]
                in {
                    "INPUT_INVALID",
                    "DEPENDENCE_EXCLUDED",
                    "DIAGNOSTIC_ONLY",
                    "SCREEN_PASS",
                },
                "RECONCILIATION_LEDGER_STRUCTURE",
            )
            require(
                type(eligibility["text_evaluable"]) is bool
                and (
                    eligibility["normalized"] is None
                    or type(eligibility["normalized"]) is str
                ),
                "RECONCILIATION_LEDGER_STRUCTURE",
            )
            require(
                type(eligibility["matches"]) is list, "RECONCILIATION_LEDGER_STRUCTURE"
            )
            for match in eligibility["matches"]:
                exact_keys(
                    match,
                    ("rule", "subrule", "span", "text"),
                    "RECONCILIATION_LEDGER_STRUCTURE",
                )
                require(
                    all(type(match[key]) is str for key in ("rule", "subrule", "text")),
                    "RECONCILIATION_LEDGER_STRUCTURE",
                )
                span = match["span"]
                require(
                    type(span) is list
                    and len(span) == 2
                    and all(type(v) is int for v in span)
                    and 0 <= span[0] <= span[1],
                    "RECONCILIATION_LEDGER_STRUCTURE",
                )
            e03 = "E03" in eligibility["rules"]
            e03c = any(m["subrule"] == "E03c" for m in eligibility["matches"])
            counts["total_rows"] += 1
            counts["e03_rows"] += int(e03)
            counts["e03c_rows"] += int(e03c)
            counts["union_rows"] += int(e03 or e03c)
            counts["normalized_empty_question_rows"] += int(
                "normalized_empty_question" in eligibility["invalid"]
            )
    except (
        ProtocolError,
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        RecursionError,
    ):
        raise ProtocolError("RECONCILIATION_LEDGER_STRUCTURE") from None
    return counts


def counts_receipt(manifest_sha256, ledger_raw):
    hex256(manifest_sha256)
    return canonical(
        dict(
            schema="reviewer-protocol-v2-ledger-counts-evidence-v1",
            manifest_sha256=manifest_sha256,
            ledger_sha256=sha_bytes(ledger_raw),
            procedure_sha256=sha_bytes(canonical(COUNT_PROCEDURE)),
            counts=count_ledger(ledger_raw),
        )
    )


def review_subject(value):
    return sha_bytes(
        canonical(
            {key: item for key, item in value.items() if key != "independent_review"}
            | {
                "schema": "reviewer-protocol-v2-historical-ledger-reconciliation-subject-v1"
            }
        )
    )


def verify_reconciliation(raw, history, current, generating, generating_binding, read):
    """Only discharges the identified source mismatch after all technical joins."""
    value = object_header(
        raw,
        "historical-ledger-reconciliation",
        (
            "manifest",
            "ledger",
            "historical_generating_bundle",
            "historical_source",
            "current_source",
            "current_verification_bundle",
            "lemma",
            "counts_evidence",
            "independent_review",
        ),
    )
    parent = history["manifest_binding"]["path"].rsplit("/", 1)[0]
    ledger_fb = dict(
        path=parent + "/population_ledger.jsonl",
        sha256=history["manifest"]["files"]["population_ledger.jsonl"],
    )
    require(
        value["manifest"] == history["manifest_binding"]
        and value["ledger"] == ledger_fb
        and value["manifest"]["sha256"] == TARGET["manifest"]
        and ledger_fb["sha256"] == TARGET["ledger"],
        "RECONCILIATION_SUBJECT",
    )
    require(
        object_bytes(checked_read(value["manifest"], read)) == history["manifest"],
        "RECONCILIATION_MANIFEST",
    )
    captured = history["payloads"]["population_ledger.jsonl"]
    require(
        sha_bytes(captured) == ledger_fb["sha256"],
        "RECONCILIATION_CAPTURED_LEDGER_HASH",
    )
    require(
        value["historical_generating_bundle"] == generating_binding
        and object_bytes(checked_read(generating_binding, read)) == generating
        and generating["implementation_sha256"]
        == history["digest"]
        == TARGET["generating"]
        and len(history["sources"]) == 16
        and sha_bytes(canonical(history["sources"])) == history["digest"],
        "RECONCILIATION_HISTORICAL_BUNDLE",
    )
    require(
        value["historical_source"] == generating["sources"]["eligibility.py"]
        and value["historical_source"]["sha256"]
        == history["sources"]["eligibility.py"]
        == TARGET["historical_source"],
        "RECONCILIATION_HISTORICAL_SOURCE",
    )
    checked_read(value["historical_source"], read)
    require(
        value["current_verification_bundle"] == current
        and sha_bytes(canonical(current["files"])) == current["sha256"]
        and current["sha256"] != history["digest"],
        "RECONCILIATION_CURRENT_BUNDLE",
    )
    require(
        value["current_source"]
        == dict(path=SOURCE_PATH, sha256=current["files"][SOURCE_PATH])
        and value["current_source"]["sha256"] == TARGET["current_source"],
        "RECONCILIATION_CURRENT_SOURCE",
    )
    checked_read(value["current_source"], read)
    require(value["lemma"]["sha256"] == TARGET["lemma"], "RECONCILIATION_LEMMA_SUBJECT")
    checked_read(value["lemma"], read)
    counts_raw = checked_read(value["counts_evidence"], read)
    declared = object_header(
        counts_raw,
        "ledger-counts-evidence",
        ("manifest_sha256", "ledger_sha256", "procedure_sha256", "counts"),
    )
    exact_keys(declared["counts"], COUNT_KEYS, "RECONCILIATION_COUNTS_STRUCTURE")
    require(
        all(type(n) is int and n >= 0 for n in declared["counts"].values()),
        "RECONCILIATION_COUNTS_STRUCTURE",
    )
    actual = counts_receipt(TARGET["manifest"], captured)
    require(counts_raw == actual, "RECONCILIATION_COUNTS_BINDING")
    require(
        declared["counts"] == RECONCILIATION_CONTRACT["counts"],
        "RECONCILIATION_COUNTS_PREREQUISITES",
    )
    review = object_header(
        checked_read(value["independent_review"], read),
        "ledger-reconciliation-review",
        (
            "subject_sha256",
            "contract_sha256",
            "lemma_sha256",
            "counts_sha256",
            "record_reference",
            "record_path",
            "record_sha256",
            "reviewer",
            "recorded_utc",
            "note",
        ),
    )
    require(
        review["subject_sha256"] == review_subject(value)
        and review["contract_sha256"] == sha_bytes(canonical(RECONCILIATION_CONTRACT))
        and review["lemma_sha256"] == TARGET["lemma"]
        and review["counts_sha256"] == value["counts_evidence"]["sha256"],
        "RECONCILIATION_REVIEW_BINDING",
    )
    checked_read(dict(path=review["record_path"], sha256=review["record_sha256"]), read)
    for key in ("record_reference", "reviewer", "note", "recorded_utc"):
        text(review[key], True)
    try:
        parsed = datetime.strptime(review["recorded_utc"], "%Y-%m-%dT%H:%M:%SZ")
        require(
            parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == review["recorded_utc"],
            "RECONCILIATION_REVIEW_UTC",
        )
    except ValueError:
        raise ProtocolError("RECONCILIATION_REVIEW_UTC") from None
    return "TECHNICAL_RECONCILIATION_VERIFIED_NOT_ADOPTED"
