import pytest
from experiments.reviewer_protocol_v2.common import ProtocolError, check_runtime
from experiments.reviewer_protocol_v2.eligibility import (
    classify,
    reference,
    reference_index,
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
