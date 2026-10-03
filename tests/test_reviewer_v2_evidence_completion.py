"""Invented wrappers and ledger only; TARGET substitutions are test-local fixtures."""

import copy
import json
import itertools
import re
from pathlib import Path

import pytest

from experiments.reviewer_protocol_v2 import ledger_adoption as a
from experiments.reviewer_protocol_v2 import ledger_reconciliation as r
from experiments.reviewer_protocol_v2 import procedure_evidence as e
from experiments.reviewer_protocol_v2 import production_preparation as p
from experiments.reviewer_protocol_v2 import selection as s
from experiments.reviewer_protocol_v2 import (
    packet_serialization,
    trial_interfaces,
    eligibility,
)
from experiments.reviewer_protocol_v2.common import (
    ProtocolError,
    canonical,
    question_hash,
    sha_bytes,
)
from tests.test_reviewer_v2_adoption_encoding import (
    invented_normative_identity as invented_normative_identity,
    complete_fixture,
    artifact,
    replace_artifact,
    verify,
)
from tests.test_reviewer_v2_review_remediation import rule_context, write_evidence


def invented_rows(rows):
    originals = copy.deepcopy(rows)
    rows[:] = [copy.deepcopy(originals[i % len(originals)]) for i in range(104)]
    for index, row in enumerate(rows):
        row.update(
            cand_id=f"c_{index + 1:010x}",
            question=f"Invented text {index}",
            context_group=f"invented-group-{index}",
        )
        row["question_sha256"] = question_hash(row["question"])
        row["eligibility"] = dict(
            rules=[],
            matches=[],
            invalid=[],
            disposition="SCREEN_PASS",
            text_evaluable=True,
            normalized=f"invented text {index}",
        )


def reconciliation_fixture(root, monkeypatch):
    f, freeze = complete_fixture(
        root, invented_rows, b"# Invented old eligibility source.\n"
    )
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    history = a._history(
        root,
        f["historical_manifest"],
        f["expected_historical_manifest_sha256"],
        f["generating_sources"],
    )
    current = p.verification_bundle(f["executing_sources"])
    generating_fb = freeze["artifacts"]["eligibility_exposure_code_bundle"]
    generating = artifact(f, freeze, "eligibility_exposure_code_bundle")

    def put(name, value):
        path = "heldout-external/invented-procedure/reconciliation-" + name
        raw = value if type(value) is bytes else canonical(value)
        (root / path).write_bytes(raw)
        return dict(path=path, sha256=sha_bytes(raw))

    lemma = put("lemma.md", b"Invented independently reviewed lemma; synthetic only.\n")
    monkeypatch.setattr(
        r,
        "TARGET",
        dict(
            manifest=history["manifest_binding"]["sha256"],
            ledger=history["manifest"]["files"]["population_ledger.jsonl"],
            generating=history["digest"],
            historical_source=history["sources"]["eligibility.py"],
            current_source=current["files"][r.SOURCE_PATH],
            lemma=lemma["sha256"],
        ),
    )
    record = dict(
        schema="reviewer-protocol-v2-historical-ledger-reconciliation-v1",
        manifest=history["manifest_binding"],
        ledger=f["artifacts"]["eligibility_ledger"],
        historical_generating_bundle=generating_fb,
        historical_source=generating["sources"]["eligibility.py"],
        current_source=dict(path=r.SOURCE_PATH, sha256=current["files"][r.SOURCE_PATH]),
        current_verification_bundle=current,
        lemma=lemma,
        counts_evidence=put(
            "counts.json",
            r.counts_receipt(
                r.TARGET["manifest"], history["payloads"]["population_ledger.jsonl"]
            ),
        ),
        independent_review=None,
    )
    origin = put(
        "review-record.txt", b"Invented review raw record, not real approval.\n"
    )
    review = dict(
        schema="reviewer-protocol-v2-ledger-reconciliation-review-v1",
        subject_sha256=r.review_subject(record),
        contract_sha256=sha_bytes(canonical(r.RECONCILIATION_CONTRACT)),
        lemma_sha256=lemma["sha256"],
        counts_sha256=record["counts_evidence"]["sha256"],
        record_reference="Invented independent review",
        record_path=origin["path"],
        record_sha256=origin["sha256"],
        reviewer="Invented reviewer",
        recorded_utc="2026-10-02T00:00:00Z",
        note="Synthetic technical review only.",
    )
    record["independent_review"] = put("review.json", review)
    rule = procedure["rules"]["eligibility_specification"]
    witness = json.loads(a.read_binding(root, rule["relationship_evidence"]))
    witness["historical_ledger_reconciliation"] = put("contract.json", record)
    rule["relationship_evidence"] = write_evidence(
        root, rule["relationship_evidence"], witness
    )
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    return dict(
        f=f,
        freeze=freeze,
        history=history,
        current=current,
        generating=generating,
        generating_fb=generating_fb,
        record=record,
        put=put,
        read=lambda fb: a.read_binding(root, fb),
    )


def check(context):
    return r.verify_reconciliation(
        canonical(context["record"]),
        context["history"],
        context["current"],
        context["generating"],
        context["generating_fb"],
        context["read"],
    )


def test_complete_synthetic_compatibility_no_writes_or_hooks(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    def forbidden(*args, **kwargs):
        raise AssertionError("Operational or write hook reached")

    for module, names in (
        (s, ("select", "scan", "ranking_digest", "ranking_key", "select_bound_inputs")),
        (packet_serialization, ("external_id", "build_external_outputs")),
        (trial_interfaces, ("build_trial", "build_presentations", "build_schedule")),
        (eligibility, ("classify", "classify_json", "textual", "normalize")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    result = verify(context["f"], context["freeze"])
    assert result["proposed_freeze_compatible"] is True, result
    assert result["operational_adoption_performed"] is False
    assert check(context) == "TECHNICAL_RECONCILIATION_VERIFIED_NOT_ADOPTED"
    assert before == {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }


def test_deterministic_reconciliation_and_counts_two_roots(tmp_path, monkeypatch):
    vectors = []
    for name in ("one", "two"):
        context = reconciliation_fixture(tmp_path / name, monkeypatch)
        assert check(context) == "TECHNICAL_RECONCILIATION_VERIFIED_NOT_ADOPTED"
        vectors.append(
            (
                canonical(context["record"]),
                context["read"](context["record"]["counts_evidence"]),
            )
        )
    assert vectors[0] == vectors[1]


@pytest.mark.parametrize(
    "field,code",
    [
        ("manifest", "RECONCILIATION_SUBJECT"),
        ("ledger", "RECONCILIATION_SUBJECT"),
        ("historical_generating_bundle", "RECONCILIATION_HISTORICAL_BUNDLE"),
        ("historical_source", "RECONCILIATION_HISTORICAL_SOURCE"),
        ("current_source", "RECONCILIATION_CURRENT_SOURCE"),
        ("lemma", "RECONCILIATION_LEMMA_SUBJECT"),
    ],
)
def test_wrong_reconciliation_subjects(tmp_path, monkeypatch, field, code):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["record"][field] = context["record"][field] | dict(sha256="0" * 64)
    with pytest.raises(ProtocolError) as failure:
        check(context)
    assert str(failure.value) == code


def test_current_digest_cannot_replace_historical(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["record"]["current_verification_bundle"] = dict(
        files=context["history"]["sources"], sha256=context["history"]["digest"]
    )
    with pytest.raises(ProtocolError, match="^RECONCILIATION_CURRENT_BUNDLE$"):
        check(context)


def test_historical_map_digest_mismatch(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["history"]["sources"]["exposure.py"] = "0" * 64
    with pytest.raises(ProtocolError, match="^RECONCILIATION_HISTORICAL_BUNDLE$"):
        check(context)


def test_captured_bytes_cannot_be_replaced(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["history"]["payloads"]["population_ledger.jsonl"] += b"\n"
    with pytest.raises(ProtocolError, match="^RECONCILIATION_CAPTURED_LEDGER_HASH$"):
        check(context)


def test_reconciliation_preserves_remaining_runtime_checks(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    lock = artifact(context["f"], context["freeze"], "runtime_dependency_lock")
    lock["runtime"]["python_version"] = "0.0"
    replace_artifact(context["f"], context["freeze"], "runtime_dependency_lock", lock)
    assert (
        verify(context["f"], context["freeze"])["code"] == "ADOPTION_PROPOSED_RUNTIME"
    )


@pytest.mark.parametrize("field", ["schema", "extra"])
def test_obsolete_or_untyped_reconciliation_rejected(tmp_path, monkeypatch, field):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["record"][field] = "obsolete" if field == "schema" else True
    with pytest.raises(ProtocolError) as failure:
        check(context)
    assert str(failure.value) == (
        "schema_version" if field == "schema" else "schema_keys"
    )


@pytest.mark.parametrize(
    "field",
    [
        "subject_sha256",
        "contract_sha256",
        "lemma_sha256",
        "counts_sha256",
        "record_sha256",
    ],
)
def test_incorrect_review_bindings(tmp_path, monkeypatch, field):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    review = json.loads(context["read"](context["record"]["independent_review"]))
    review[field] = "0" * 64
    context["record"]["independent_review"] = context["put"]("bad-review.json", review)
    expected = (
        "input_hash_mismatch"
        if field == "record_sha256"
        else "RECONCILIATION_REVIEW_BINDING"
    )
    with pytest.raises(ProtocolError) as failure:
        check(context)
    assert str(failure.value) == expected


def test_missing_review(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["record"].pop("independent_review")
    with pytest.raises(ProtocolError, match="^schema_keys$"):
        check(context)


def test_self_declared_review_flag_cannot_replace_evidence(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    context["record"]["independent_review"] = context["put"](
        "self-declared.json", dict(independently_reviewed=True)
    )
    with pytest.raises(ProtocolError, match="^schema_keys$"):
        check(context)


def test_absent_reconciliation_still_blocks_identified_source_difference(
    tmp_path, monkeypatch
):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    procedure = artifact(
        context["f"], context["freeze"], "historical_integrity_manifest"
    )
    rule = procedure["rules"]["eligibility_specification"]
    witness = json.loads(context["read"](rule["relationship_evidence"]))
    witness["historical_ledger_reconciliation"] = None
    rule["relationship_evidence"] = write_evidence(
        tmp_path, rule["relationship_evidence"], witness
    )
    replace_artifact(
        context["f"], context["freeze"], "historical_integrity_manifest", procedure
    )
    assert (
        verify(context["f"], context["freeze"])["code"]
        == "E03C_LEDGER_RECONCILIATION_REQUIRED"
    )


@pytest.mark.parametrize(
    "field", [*r.COUNT_KEYS, "manifest_sha256", "ledger_sha256", "procedure_sha256"]
)
def test_forged_count_declarations(tmp_path, monkeypatch, field):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    counts = json.loads(context["read"](context["record"]["counts_evidence"]))
    if field in r.COUNT_KEYS:
        counts["counts"][field] += 1
    else:
        counts[field] = "0" * 64
    context["record"]["counts_evidence"] = context["put"]("forged-counts.json", counts)
    with pytest.raises(ProtocolError, match="^RECONCILIATION_COUNTS_BINDING$"):
        check(context)


@pytest.mark.parametrize("kind", ["e03", "e03c", "empty", "wrong_total"])
def test_recomputed_nonzero_or_wrong_total_cannot_pass(tmp_path, monkeypatch, kind):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    rows = [
        json.loads(line)
        for line in context["history"]["payloads"][
            "population_ledger.jsonl"
        ].splitlines()
    ]
    if kind == "e03":
        rows[0]["eligibility"]["rules"] = ["E03"]
    elif kind == "e03c":
        rows[0]["eligibility"]["matches"] = [
            dict(rule="E03", subrule="E03c", span=[0, 1], text="i")
        ]
    elif kind == "empty":
        rows[0]["eligibility"]["invalid"] = ["normalized_empty_question"]
    else:
        rows.pop()
    raw = b"".join(canonical(row) for row in rows)
    context["history"]["payloads"]["population_ledger.jsonl"] = raw
    digest = sha_bytes(raw)
    context["history"]["manifest"]["files"]["population_ledger.jsonl"] = digest
    manifest_fb = context["put"](
        "changed-manifest.json", context["history"]["manifest"]
    )
    context["history"]["manifest_binding"] = manifest_fb
    context["record"]["manifest"] = manifest_fb
    context["record"]["ledger"] = dict(
        path=manifest_fb["path"].rsplit("/", 1)[0] + "/population_ledger.jsonl",
        sha256=digest,
    )
    monkeypatch.setattr(
        r, "TARGET", r.TARGET | dict(manifest=manifest_fb["sha256"], ledger=digest)
    )
    context["record"]["counts_evidence"] = context["put"](
        "changed-counts.json", r.counts_receipt(manifest_fb["sha256"], raw)
    )
    with pytest.raises(ProtocolError, match="^RECONCILIATION_COUNTS_PREREQUISITES$"):
        check(context)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{}\n",
        b'{"eligibility":{},"eligibility":{}}\n',
        b'{"eligibility":NaN}\n',
        b'{"eligibility":1e999}\n',
        b"\xff\n",
        b"[]\n",
        b"\n",
    ],
)
def test_structural_failures_are_sanitized(raw):
    with pytest.raises(ProtocolError) as failure:
        r.count_ledger(raw)
    assert str(failure.value) == "RECONCILIATION_LEDGER_STRUCTURE"


def test_counts_count_rows_not_matches():
    eligibility = dict(
        rules=["E03"],
        matches=[dict(rule="E03", subrule="E03c", span=[0, 1], text="i")] * 3,
        invalid=["normalized_empty_question"] * 2,
        disposition="INPUT_INVALID",
        text_evaluable=False,
        normalized="",
    )
    assert r.count_ledger(canonical(dict(eligibility=eligibility))) == dict(
        zip(r.COUNT_KEYS, (1, 1, 1, 1, 1), strict=True)
    )


@pytest.mark.parametrize("role", a.RULE_ROLES)
def test_obsolete_review_and_applicability_versions(tmp_path, role):
    f, freeze, procedure, history, read = rule_context(tmp_path)
    witness_fb = procedure["rules"][role]["relationship_evidence"]
    witness = json.loads(read(witness_fb))
    witness["schema"] = "reviewer-protocol-v2-rule-applicability-v2"
    procedure["rules"][role]["relationship_evidence"] = write_evidence(
        tmp_path, witness_fb, witness
    )
    with pytest.raises(ProtocolError, match="^evidence_version$"):
        e.rule_bindings(
            procedure,
            freeze["artifacts"],
            history,
            p.verification_bundle(f["executing_sources"]),
            read,
            a.RULE_ROLES,
        )
    witness["schema"] = "reviewer-protocol-v2-rule-applicability-v3"
    review = json.loads(read(witness["semantic_review_evidence"]))
    review["schema"] = "reviewer-protocol-v2-review-evidence-v3"
    witness["semantic_review_evidence"] = write_evidence(
        tmp_path, witness["semantic_review_evidence"], review
    )
    procedure["rules"][role]["relationship_evidence"] = write_evidence(
        tmp_path, witness_fb, witness
    )
    with pytest.raises(ProtocolError, match="^evidence_version$"):
        e.rule_bindings(
            procedure,
            freeze["artifacts"],
            history,
            p.verification_bundle(f["executing_sources"]),
            read,
            a.RULE_ROLES,
        )


@pytest.mark.parametrize(
    "kind,code",
    [
        ("altered_bytes", "input_hash_mismatch"),
        ("review_join", "RULE_REVIEW_NORMATIVE_DOCUMENT"),
        ("role_join", "RULE_NORMATIVE_DOCUMENT_JOIN"),
    ],
)
def test_normative_document_raw_hash_and_joins(tmp_path, kind, code):
    f, freeze, procedure, history, read = rule_context(tmp_path)
    role = (
        "exposure_specification" if kind == "role_join" else "eligibility_specification"
    )
    witness_fb = procedure["rules"][role]["relationship_evidence"]
    witness = json.loads(read(witness_fb))
    document = witness["normative_document"]
    if kind == "altered_bytes":
        (tmp_path / document["path"]).write_bytes(b"Altered invented document.\n")
    else:
        other = document | dict(path=document["path"] + ".other")
        (tmp_path / other["path"]).write_bytes(read(document))
        if kind == "review_join":
            review_fb = witness["semantic_review_evidence"]
            review = json.loads(read(review_fb))
            review["normative_document"] = other
            witness["semantic_review_evidence"] = write_evidence(
                tmp_path, review_fb, review
            )
        else:
            witness["normative_document"] = other
        procedure["rules"][role]["relationship_evidence"] = write_evidence(
            tmp_path, witness_fb, witness
        )
    with pytest.raises(ProtocolError) as failure:
        e.rule_bindings(
            procedure,
            freeze["artifacts"],
            history,
            p.verification_bundle(f["executing_sources"]),
            read,
            a.RULE_ROLES,
        )
    assert str(failure.value) == code


def test_mechanical_contract_matches_normative_literal_list():
    contract = e.rule_contract("eligibility_specification")
    document = (
        s.SOURCE_ROOT / "main/docs/experiments/reviewer-protocol-v2-current-rules-v1.md"
    ).read_text(encoding="utf-8")
    section = document.split("Count is 42:", 1)[1].split("**Algorithm:**", 1)[0]
    literals = [
        line[3:-1]
        for line in section.splitlines()
        if line.startswith("- `") and line.endswith("`")
    ]
    assert contract["e05_phrases"] == sorted(literals)
    assert len(set(literals)) == 42
    assert contract["e05_terminal"] == ["?", "."]
    assert contract["e05_algorithm"] == "Q_IN_P05_OR_ONE_TERMINAL_MARK_REMOVED_IN_P05"
    assert contract["e05_span"] == "ENTIRE_NORMALIZED_Q_INCLUDING_PERMITTED_MARK"
    assert len(contract["e07_conditions"]) == 8
    assert contract["e07_failure_scope"]["population_abort"] == [
        "POPULATION_FILE_HASH_MISMATCH",
        "DUPLICATE_INDEX_ID",
    ]
    assert contract["normalization_steps"] == [
        dict(operation="UNICODE_NORMALIZE", form="NFKC"),
        dict(operation="STR_CASEFOLD"),
        dict(operation="RE_SUB", pattern=r"\s+", replacement=" ", flags="UNICODE"),
        dict(operation="STR_STRIP", characters="PYTHON_UNICODE_WHITESPACE"),
    ]
    assert contract["text_evaluable"]["non_evaluable"]["matches"] == []
    assert "EMPTY_NORMALIZED_VIEW" in contract["text_evaluable"]["blocks"]
    assert (
        contract["text_rule_evaluation"]["non_evaluable"]
        == "NOT_EVALUABLE_NO_MATCHES_INCLUDING_EMPTY_VIEW"
    )


def test_invented_containment_probes_are_support_not_exhaustive_proof():
    suffix = " (?:the )?" + eligibility.T + eligibility.AM
    old = re.compile(
        eligibility.bounded(eligibility.alternatives("in from according to") + suffix)
    )
    corrected = eligibility.PATTERNS["E03c"]
    probes = 0
    for prep, article, material, adjective, prefix, ending in itertools.product(
        ("in", "from", "according to"),
        ("", "the "),
        ("attached", "provided"),
        ("", "annual ", "annual financial "),
        ("", "? ", "word "),
        ("", ".", " word"),
    ):
        view = (
            prefix
            + prep
            + " "
            + article
            + material
            + " "
            + adjective
            + "table"
            + ending
        )
        assert corrected.search(view) is not None
        assert old.search(view) is not None
        probes += 1
    assert probes == 324


def test_captured_ledger_not_reread(tmp_path, monkeypatch):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    original = context["read"]

    def read(binding):
        assert binding != context["record"]["ledger"], "Captured ledger was reread"
        return original(binding)

    context["read"] = read
    assert check(context) == "TECHNICAL_RECONCILIATION_VERIFIED_NOT_ADOPTED"


@pytest.mark.parametrize(
    "path",
    [
        "heldout-external/../outside.md",
        "main/../outside.md",
        "C:/outside.md",
        "heldout-external\\outside.md",
    ],
)
def test_review_record_path_escape(tmp_path, monkeypatch, path):
    context = reconciliation_fixture(tmp_path, monkeypatch)
    review = json.loads(context["read"](context["record"]["independent_review"]))
    review["record_path"] = path
    context["record"]["independent_review"] = context["put"](
        "escape-review.json", review
    )
    with pytest.raises(ProtocolError, match="^relative_path$"):
        check(context)
