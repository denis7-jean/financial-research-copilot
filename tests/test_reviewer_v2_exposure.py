import copy
import math
from collections import Counter
import pytest
from experiments.reviewer_protocol_v2.common import (
    ProtocolError,
    canonical,
    question_hash,
    sha_bytes,
    verify_file,
)
from experiments.reviewer_protocol_v2.eligibility import normalize
from experiments.reviewer_protocol_v2.exposure import (
    InventoryBuilder,
    exposure_ledger,
    load_inventory,
    validate_inventory,
)
from experiments.reviewer_protocol_v2.fixtures import synthetic_record
from experiments.reviewer_protocol_v2.similarity import conflicts, cos, grams


def row(index, question):
    return synthetic_record(question) | {
        "cand_id": "c_%010x" % index,
        "context_group": "synthetic-group-%d" % index,
    }


def inventory(rows, cid=None, question=None):
    builder = InventoryBuilder(rows)
    builder.add(
        "work_history_disclosure",
        "synthetic",
        None,
        "fixture:1",
        cid=cid,
        question=question,
        stage="synthetic",
    )
    return builder.finish()


@pytest.mark.parametrize("missing", [False, True])
def test_missing_or_mutated_input(tmp_path, missing):
    path = tmp_path / "input"
    expected = sha_bytes(b"registered")
    if not missing:
        path.write_bytes(b"altered")
    with pytest.raises(ProtocolError, match="missing_input|hash_mismatch"):
        verify_file(path, expected)


def test_identity_binding_and_views_are_separate():
    rows = [row(1, " ＴＡＢＬＥ Straße ")]
    builder = InventoryBuilder(rows)
    assert (
        builder.identify(question="table strasse")[1]
        == "registered_normalized_equality"
    )
    with pytest.raises(ProtocolError, match="identity_mismatch"):
        builder.identify(cid=rows[0]["cand_id"], question="table strasse")
    assert normalize(rows[0]["question"]) == "table strasse"
    assert grams(rows[0]["question"]) != grams("table strasse")
    assert question_hash(rows[0]["question"]) != question_hash("table strasse")


def test_all_exact_identity_matches_preserved_and_text_deduplicated():
    rows = [
        row(1, "Synthetic duplicated question"),
        row(2, "Synthetic duplicated question"),
    ]
    value = inventory(rows, question=rows[0]["question"])
    assert len(value["pilot_items"]) == 2
    assert len(value["evidence"]) == 2
    assert len(value["references"]) == 1
    assert len(value["references"][0]["pilot_ids"]) == 2
    validate_inventory(value, rows)


def test_loader_rejects_truncated_text_admitted_complete(tmp_path):
    rows = [row(1, "Synthetic canonical question")]
    value = inventory(rows, question="Complete synthetic outside reference")
    path = tmp_path / "inventory.json"
    original = canonical(value)
    expected = sha_bytes(original)
    altered = copy.deepcopy(value)
    altered["references"][0]["question"] = "Complete synthetic..."
    # Claiming completeness does not defeat the independent inventory binding.
    altered["references"][0]["complete"] = True
    path.write_bytes(canonical(altered))
    with pytest.raises(ProtocolError, match="hash_mismatch"):
        load_inventory(path, expected, rows)
    with pytest.raises(ProtocolError, match="hash_or_dedup"):
        validate_inventory(altered, rows)
    path.write_bytes(original)
    assert load_inventory(path, expected, rows)["references"][0]["complete"]


def test_incomplete_provenance_cannot_be_admitted():
    builder = InventoryBuilder([row(1, "Synthetic question")])
    with pytest.raises(ProtocolError, match="incomplete_exposure"):
        builder.add(
            "work_history_disclosure",
            "synthetic",
            None,
            "fragment",
            question="fragment...",
            stage="synthetic",
            completeness="truncated",
        )


def test_no_transitive_chaining():
    # Each adjacent pair shares >90% grams; endpoints share <90%.
    base = "".join(chr(0x1000 + i) for i in range(100))
    a, b, c = base, "12345678" + base[8:], "12345678" + base[8:-8] + "87654321"
    assert conflicts(cos(grams(a), grams(b)))
    assert conflicts(cos(grams(b), grams(c)))
    assert not conflicts(cos(grams(a), grams(c)))
    rows = [row(1, a), row(2, b), row(3, c)]
    result = exposure_ledger(rows, inventory(rows, cid=rows[0]["cand_id"]))
    assert [r["near_duplicate"] for r in result] == [True, True, False]
    assert [r["direct"] for r in result] == [True, False, False]


def test_native_group_exclusion_does_not_become_seed():
    rows = [
        row(1, "aaa aaa aaa aaa"),
        row(2, "zzz zzz zzz zzz"),
        row(3, "zzz zzz zzz zzz"),
    ]
    rows[1]["context_group"] = rows[0]["context_group"]
    result = exposure_ledger(rows, inventory(rows, cid=rows[0]["cand_id"]))
    assert [r["native_group"] for r in result] == [True, True, False]
    assert [r["near_duplicate"] for r in result] == [True, False, False]


def test_threshold_exact_and_zero_vector_contract():
    assert conflicts(0.90)
    assert not conflicts(math.nextafter(0.90, 0))
    assert conflicts(math.nextafter(0.90, 1))
    assert cos(Counter(), Counter()) == 0.0
    assert cos(Counter({"a": 1}), Counter()) == 0.0
    assert grams("") == Counter({"": 1})
    assert grams("xy") == Counter({"xy": 1})


def test_provenance_loss_rejected():
    rows = [row(1, "Synthetic canonical question")]
    value = inventory(rows, cid=rows[0]["cand_id"])
    value["references"][0]["evidence_indices"] = []
    with pytest.raises(ProtocolError, match="without_provenance"):
        validate_inventory(value, rows)


def test_incomplete_outside_item_rejected_even_with_complete_reference():
    rows = [row(1, "Synthetic canonical question")]
    value = inventory(rows, question="Complete synthetic outside reference")
    value["outside_items"][0]["complete"] = False
    with pytest.raises(ProtocolError, match="incomplete_outside"):
        validate_inventory(value, rows)
