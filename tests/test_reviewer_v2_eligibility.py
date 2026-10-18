import pytest
from experiments.reviewer_protocol_v2.common import ProtocolError, check_runtime
from experiments.reviewer_protocol_v2.eligibility import (
    classify,
    reference,
    reference_index,
    classify_json,
    textual,
    normalize,
)
from experiments.reviewer_protocol_v2.fixtures import (
    additional_results,
    registered_results,
    synthetic_record,
)


@pytest.mark.parametrize("index", range(100), ids=lambda i: "registered-%03d" % i)
def test_registered_fixture(index):
    result = registered_results()[index]
    assert result["actual"] == result["expected"]


@pytest.mark.parametrize("index", range(37), ids=lambda i: "additional-%02d" % i)
def test_additional_contract(index):
    assert additional_results()[index]


def test_runtime_contract(monkeypatch):
    assert check_runtime()["unicode"] == "15.1.0"
    monkeypatch.setattr(
        "experiments.reviewer_protocol_v2.common.unicodedata.unidata_version", "0.0"
    )
    with pytest.raises(ProtocolError, match="unicode_requires"):
        check_runtime()


def test_duplicate_canonical_id_aborts():
    row = synthetic_record()
    with pytest.raises(ProtocolError, match="duplicate_canonical"):
        reference_index([row, row])


def test_precedence_preserves_every_rule_and_span():
    row = synthetic_record("this table row 3 previous answer [company]")
    result = classify(
        row | {"source_revision": "wrong"}, {row["cand_id"]: reference(row)}
    )
    assert result["disposition"] == "INPUT_INVALID"
    assert result["rules"] == ["E01", "E02", "E03", "E04", "E06", "E07"]
    for match in result["matches"]:
        start, end = match["span"]
        assert result["normalized"][start:end] == match["text"]


def test_non_string_metadata_is_invalid_without_losing_text():
    row = synthetic_record("previous answer")
    result = classify(row | {"source": []}, {row["cand_id"]: reference(row)})
    assert result["rules"] == ["E04", "E07"]
    assert result["text_evaluable"]


@pytest.mark.parametrize(
    "question",
    [
        "in the attached report",
        "from provided detailed data",
        "according to the attached financial statement",
        "Invented: ACCORDING\tTO the provided annual report?",
    ],
)
def test_e03c_literal_prepositions_exact_normalized_spans(question):
    q, matches = textual(question)
    phrase = q[q.index("according to") :] if "according to" in q else q
    phrase = phrase.removesuffix("?")
    start = q.index(phrase)
    found = [m for m in matches if m["subrule"] == "E03c"]
    assert found == [
        dict(rule="E03", subrule="E03c", span=[start, start + len(phrase)], text=phrase)
    ]
    assert any(m["subrule"] == "E02" for m in matches)


@pytest.mark.parametrize(
    "question",
    [
        "to the attached report",
        "according the attached report",
        "to provided values",
        "according attached chart",
    ],
)
def test_split_word_forms_keep_e02_without_e03c(question):
    q, matches = textual(question)
    assert not any(m["subrule"] == "E03c" for m in matches)
    assert "E03" not in {m["rule"] for m in matches}
    e02 = [m for m in matches if m["subrule"] == "E02"]
    assert len(e02) == 1
    tail = q[q.index("attached" if "attached" in q else "provided") :]
    assert e02[0]["span"] == [q.index(tail), len(q)]
    assert e02[0]["text"] == tail


@pytest.mark.parametrize("question", ["", " \t\n", "\ud800"])
def test_d4_unusable_question_is_not_text_evaluable(question):
    row = synthetic_record()
    result = classify(row | {"question": question}, {row["cand_id"]: reference(row)})
    assert result["text_evaluable"] is False
    assert result["rules"] == ["E07"] and result["matches"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {"cand_id": "c_fffffffffe"},
        {"source_revision": "Invented wrong revision"},
        {"question": "in the attached report"},
        {"source": None},
    ],
)
def test_d4_metadata_id_or_hash_error_preserves_usable_text(changes):
    row = synthetic_record("according to the attached financial statement")
    result = classify(row | changes, {row["cand_id"]: reference(row)})
    assert result["text_evaluable"] is True
    assert result["disposition"] == "INPUT_INVALID"
    assert {"E02", "E03", "E07"} <= set(result["rules"])


@pytest.mark.parametrize(
    "raw",
    [
        b'{"question":"in attached report", "question":"other"}',
        b'{"question":NaN}',
        b'{"question":Infinity}',
        b'{"other":"invented"}',
        b'{"question":17}',
        b"not JSON",
    ],
)
def test_d4_json_unusable_records_do_not_infer_text_rules(raw):
    result = classify_json(raw, {})
    assert result["text_evaluable"] is False
    assert result["matches"] == [] and result["disposition"] == "INPUT_INVALID"


def test_d4_extra_fields_permitted_and_e05_span_includes_terminal_mark():
    row = synthetic_record("Explain it?")
    result = classify(row | {"invented_extra": 17}, {row["cand_id"]: reference(row)})
    assert result["disposition"] == "DIAGNOSTIC_ONLY"
    assert result["matches"] == [
        dict(
            rule="E05",
            subrule="E05",
            span=[0, len(normalize(row["question"]))],
            text=normalize(row["question"]),
        )
    ]
