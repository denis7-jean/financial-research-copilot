"""Owner identity pin and reconciliation residuals, using invented artifacts only."""

import json

import pytest

from experiments.reviewer_protocol_v2 import eligibility
from experiments.reviewer_protocol_v2 import ledger_adoption as a
from experiments.reviewer_protocol_v2 import procedure_evidence as e
from experiments.reviewer_protocol_v2.common import ProtocolError, sha_bytes
from experiments.reviewer_protocol_v2.fixtures import synthetic_record
from tests.test_reviewer_v2_adoption_encoding import (
    artifact,
    invented_normative_identity as invented_normative_identity,
    replace_artifact,
    verify,
)
from tests.test_reviewer_v2_evidence_completion import check, reconciliation_fixture
from tests.test_reviewer_v2_review_remediation import rule_context, write_evidence

# Capture shipped constants before the autouse synthetic fixture replaces the pin.
SHIPPED_DOCUMENT_ID = e.NORMATIVE_DOCUMENT_ID
SHIPPED_DOCUMENT_SHA256 = e.NORMATIVE_DOCUMENT_SHA256


def test_shipped_owner_version_anchor():
    assert SHIPPED_DOCUMENT_ID == "reviewer-protocol-v2-current-rules-v1"
    assert SHIPPED_DOCUMENT_SHA256 == (
        "4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7"
    )


def test_valid_synthetic_baseline_is_technical_only(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    result = verify(context["f"], context["freeze"])
    assert result["proposed_freeze_compatible"] is True, result
    assert result["operational_adoption_performed"] is False
    assert check(context) == "TECHNICAL_RECONCILIATION_VERIFIED_NOT_ADOPTED"


def test_consistent_document_substitution_fails_owner_anchor(tmp_path, monkeypatch):
    f, freeze, procedure, _, read = rule_context(tmp_path)
    raw = b"Another invented normative document, consistently substituted.\n"
    path = "heldout-external/invented-procedure/substitute-document.md"
    (tmp_path / path).write_bytes(raw)
    document = dict(path=path, sha256=sha_bytes(raw))
    for rule in procedure["rules"].values():
        witness = json.loads(read(rule["relationship_evidence"]))
        review = json.loads(read(witness["semantic_review_evidence"]))
        review["normative_document"] = document
        witness["semantic_review_evidence"] = write_evidence(
            tmp_path, witness["semantic_review_evidence"], review
        )
        witness["normative_document"] = document
        rule["relationship_evidence"] = write_evidence(
            tmp_path, rule["relationship_evidence"], witness
        )
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    monkeypatch.setattr(e, "NORMATIVE_DOCUMENT_SHA256", SHIPPED_DOCUMENT_SHA256)
    result = verify(f, freeze)
    assert result["code"] == "RULE_NORMATIVE_DOCUMENT_IDENTITY", result
    assert result["proposed_freeze_compatible"] is False
    assert result["operational_adoption_performed"] is False


@pytest.mark.parametrize(
    "role", ["exposure_specification", "grouping_similarity_specification"]
)
def test_reconciliation_rejected_on_noneligibility_role(tmp_path, role):
    f, freeze, procedure, _, read = rule_context(tmp_path)
    rule = procedure["rules"][role]
    witness = json.loads(read(rule["relationship_evidence"]))
    # A valid invented binding suffices: the role must reject before interpreting it.
    witness["historical_ledger_reconciliation"] = witness["normative_document"]
    rule["relationship_evidence"] = write_evidence(
        tmp_path, rule["relationship_evidence"], witness
    )
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    result = verify(f, freeze)
    assert result["code"] == "RULE_RECONCILIATION_ROLE", result
    assert result["operational_adoption_performed"] is False


@pytest.mark.parametrize(
    "recorded_utc",
    ["not-a-utc-timestamp", "2026-10-02T00:00:00+00:00", "2026-10-2T00:00:00Z"],
)
def test_invalid_review_utc_has_specific_code(tmp_path, monkeypatch, recorded_utc):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    review = json.loads(context["read"](context["record"]["independent_review"]))
    review["recorded_utc"] = recorded_utc
    context["record"]["independent_review"] = context["put"]("bad-utc.json", review)
    with pytest.raises(ProtocolError) as failure:
        check(context)
    assert str(failure.value) == "RECONCILIATION_REVIEW_UTC"


@pytest.mark.parametrize(
    "path",
    [
        "data/invented-counts.json",
        "../invented-counts.json",
        "heldout-external/../invented-counts.json",
    ],
)
def test_counts_outside_roots_has_specific_code(tmp_path, monkeypatch, path):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["record"]["counts_evidence"] |= dict(path=path)
    with pytest.raises(ProtocolError) as failure:
        check(context)
    assert str(failure.value) == "relative_path"


def test_missing_generating_context_has_specific_code(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    procedure = artifact(
        context["f"], context["freeze"], "historical_integrity_manifest"
    )
    args = (
        procedure,
        context["freeze"]["artifacts"],
        context["history"],
        context["current"],
        context["read"],
        a.RULE_ROLES,
    )
    assert e.rule_bindings(*args, generating=context["generating"]) is None
    with pytest.raises(ProtocolError) as failure:
        e.rule_bindings(*args)
    assert str(failure.value) == "RECONCILIATION_GENERATING_EVIDENCE_MISSING"


def test_contract_preserves_findings_and_e07_reasons_under_winning_disposition():
    contract = e.rule_contract("eligibility_specification")
    assert contract["ledger_preservation"] == dict(
        rule_ids="ASCENDING_RULE_ID_ORDER",
        subrule_identifiers="PRESERVED",
        normalized_match_spans="PRESERVED",
        e07_reasons="PRESERVED",
        winning_disposition="NEVER_ERASES_OTHER_FINDINGS",
        e01_prevalence="REPORTED_SEPARATELY",
    )
    row = synthetic_record("this table row 3 previous answer [company]")
    refs = {row["cand_id"]: eligibility.reference(row)}
    valid = eligibility.classify(row, refs)
    invalid = eligibility.classify(row | dict(source_revision="invented-other"), refs)
    assert invalid["disposition"] == "INPUT_INVALID"
    assert invalid["rules"] == ["E01", "E02", "E03", "E04", "E06", "E07"]
    assert invalid["invalid"] == ["reference_mismatch_source_revision"]
    assert invalid["matches"] == valid["matches"]
    for match in invalid["matches"]:
        assert match["subrule"].startswith(match["rule"])
        start, end = match["span"]
        assert invalid["normalized"][start:end] == match["text"]


def test_nonobject_blocks_text_and_shared_evaluation_covers_e01_through_e06():
    contract = e.rule_contract("eligibility_specification")
    assert "NONOBJECT_JSON" in contract["text_evaluable"]["blocks"]
    result = eligibility.classify_json('["[company]"]', {})
    assert result["text_evaluable"] is False
    assert result["matches"] == [] and result["normalized"] is None
    assert result["rules"] == ["E07"] and "not_json_object" in result["invalid"]
    assert contract["text_rule_evaluation"] == dict(
        rules=["E01", "E02", "E03", "E04", "E05", "E06"],
        usable="ALL_REGISTERED_TEXT_RULES_INDEPENDENT_EVEN_ON_METADATA_INVALID_ROWS",
        non_evaluable="NOT_EVALUABLE_NO_MATCHES_INCLUDING_EMPTY_VIEW",
    )
    assert contract["e06_evaluation"] == dict(
        bracketed="ANYWHERE_NO_OUTER_BOUNDARIES",
        delimiter_forms="INDEPENDENT_PAIRED_DELIMITERS_INDEPENDENT_ZERO_OR_ONE_INNER_SPACE",
        nested="PRESERVE_ALL_REGISTERED_SUBRULE_SPANS",
        higher_precedence="PRESERVE_MATCHES",
    )
