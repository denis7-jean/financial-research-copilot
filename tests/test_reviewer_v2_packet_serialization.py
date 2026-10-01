import json

import pytest

from experiments.reviewer_protocol_v2 import packet_serialization as p
from experiments.reviewer_protocol_v2 import selection as s
from experiments.reviewer_protocol_v2.common import ProtocolError, canonical, question_hash, sha_bytes
from tests.test_reviewer_v2_selection import bound_fixture, synthetic_rows

VECTORS = [
    (dict(source="tatqa", cand_id="c_0000000001", sampling_stratum="T1_qa",
          question="What was SyntheticCo revenue in 2025?"),
     "fe4ae2507b49fd3568bfb25a1fbbd96376a045b59bb9ac8dc16e0d383d4d4d42",
     73, "c6a8af802433962ed8fa921fd65e9ce2e3b6aa48977961d97f3b79073c376172",
     138, "x_b32d2a088e5728921c18ae131e59862f8f5025767663f1960d105df65e64e985",
     132, "8cefceeb71da79f9bc225b001fd3000cb4eff699da413089ba91683e6db03f91"),
    (dict(source="finlfqa", cand_id="c_0000000002", sampling_stratum="interp",
          question="Explain SynthétiqueCo’s revenue.\nKeep the original line."),
     "4a2c133e64c121e047ac493f3a3e125a7b0566e2888df4d25965506512415926",
     89, "28bf1400ed9c478d93181d66bad664559de4c9121c4b40e4cc59aaee71771bdf",
     140, "x_bf58486c1b076d2330b36e5d9d213932b6aaa16298bfd237f0ae5caeb20db3d5",
     162, "dcf2fbec252e9d3cb5770da26f178979899bd2ab6c2e665e64bb9ac9c7648bad"),
]


@pytest.mark.parametrize("row,qhash,ranklen,rankhash,idlen,itemid,linelen,linehash", VECTORS)
def test_seven_assertions_per_vector(row, qhash, ranklen, rankhash, idlen, itemid, linelen, linehash):
    row = dict(row, question_sha256=qhash)
    assert question_hash(row["question"]) == qhash
    assert len(s.ranking_preimage(row)) == ranklen
    assert sha_bytes(s.ranking_preimage(row)) == rankhash
    assert len(p.external_id_preimage(row)) == idlen
    assert p.external_id(row) == itemid
    line = p.serialize_blind_records([dict(item_id=itemid, question=row["question"])])
    assert len(line) == linelen
    assert sha_bytes(line) == linehash


def test_combined_vector_two_assertions():
    records = [dict(item_id=v[5], question=v[0]["question"]) for v in VECTORS]
    raw = p.serialize_blind_records(records[::-1])
    assert len(raw) == 294
    assert sha_bytes(raw) == "6212b5b2dba0cf522f0421116ee3d697f187f4840bf3bb98900c068f52fa0abb"
    assert raw == p.serialize_blind_records(records)
    with pytest.raises(ProtocolError, match="production_size"):
        p.build_external_outputs([dict(v[0], question_sha256=v[1]) for v in VECTORS], "a" * 64)


@pytest.mark.parametrize("variant,length,digest", [
    ("string", 75, "5c81c5d9c2d5dcffae7e56d7c057b8f6003f19f850d005f05a33ac5757c5a727"),
    ("swap", 73, "c66f77b6b29a3716861e197f39f1c2bbdf0f2c4466cd81939c67864e01e1f5e7"),
    ("lf", 74, "faa60093a429cf990433e55c726eafe29712229705d9240431b9dc71dfdc2544"),
    ("bom", 76, "8f319f359327e0632615d1ab72c6b0a544db7681f8a41bb31917f8ffe636b086"),
])
def test_eight_negative_vector_assertions(variant, length, digest):
    values = ["reviewer-protocol-v2-rank-v1", s.SEED, "TAT-QA", "tatqa", "c_0000000001"]
    if variant == "string":
        values[1] = str(values[1])
    if variant == "swap":
        values[2], values[3] = values[3], values[2]
    raw = s.B(values)
    if variant == "lf":
        raw += b"\n"
    if variant == "bom":
        raw = b"\xef\xbb\xbf" + raw
    assert len(raw) == length
    assert sha_bytes(raw) == digest


def test_verbatim_escapes_and_order():
    question = 'É é e\u0301\n\r\t"\\<>𝄞'
    records = [dict(item_id="x_" + "b" * 64, question=question),
               dict(item_id="x_" + "a" * 64, question="invented")]
    raw = p.serialize_blind_records(records)
    assert all(b < 128 for b in raw)
    assert raw.endswith(b"\n") and not raw.startswith(b"\xef\xbb\xbf")
    decoded = [json.loads(line) for line in raw.splitlines()]
    assert decoded[1]["question"] == question
    assert raw == p.serialize_blind_records(records[::-1])
    assert all(set(r) == {"item_id", "question"} for r in decoded)


def test_collisions_duplicates_and_size(monkeypatch):
    rows = synthetic_rows()
    with pytest.raises(ProtocolError):
        p.build_external_outputs(rows[:-1] + [rows[0]], "a" * 64)
    monkeypatch.setattr(p, "external_id", lambda r: "x_" + "0" * 64)
    with pytest.raises(ProtocolError, match="duplicate_external_id"):
        p.build_external_outputs(rows, "a" * 64)


@pytest.mark.parametrize("record", [
    dict(item_id="x_" + "a" * 64, question="invented", source="tatqa"),
    dict(item_id="c_0000000001", question="invented"),
    dict(item_id="x_" + "a" * 64, question=True),
])
def test_exact_blind_schema(record):
    with pytest.raises(ProtocolError):
        p.serialize_blind_records([record])


@pytest.mark.parametrize("mutation", [
    lambda m: m["items"][0].update(source_revision="wrong"),
    lambda m: m["items"][0].update(context_group="wrong"),
    lambda m: m["items"][0].update(original_question_sha256="0" * 64),
    lambda m: m["items"][0].update(candidate_id=m["items"][1]["candidate_id"]),
    lambda m: m["items"][0].update(extra=True),
    lambda m: m["items"].reverse(), lambda m: m["items"].pop(),
    lambda m: m.update(inputs_sha256="0" * 64),
    lambda m: m.update(packet_sha256="0" * 64),
])
def test_mapping_metadata_bijection_and_order(tmp_path, mutation):
    binding, digest = bound_fixture(tmp_path)
    outputs = s.select_bound_inputs(tmp_path, binding, digest)
    mapping = json.loads(outputs["private_mapping.json"])
    mutation(mapping)
    outputs["private_mapping.json"] = canonical(mapping)
    with pytest.raises(ProtocolError):
        p.validate_result(tmp_path, binding, digest, outputs)


@pytest.mark.parametrize("mutate", [
    lambda raw: raw + b"\n", lambda raw: b"\xef\xbb\xbf" + raw,
    lambda raw: raw.replace(b'"schema":', b'"extra":0,"schema":'),
    lambda raw: raw.replace(b'"seed":20261001', b'"seed":NaN'),
    lambda raw: raw.replace(b'"seed":20261001', b'"seed":20261001,"seed":20261001'),
])
def test_private_canonical_rejection(tmp_path, mutate):
    binding, digest = bound_fixture(tmp_path)
    output = s.select_bound_inputs(tmp_path, binding, digest)
    output["selection_receipt.json"] = mutate(output["selection_receipt.json"])
    with pytest.raises((ProtocolError, UnicodeError)):
        p.validate_result(tmp_path, binding, digest, output)


def test_packet_question_mutation(tmp_path):
    binding, digest = bound_fixture(tmp_path)
    outputs = s.select_bound_inputs(tmp_path, binding, digest)
    rows = [json.loads(line) for line in outputs["external_blind.jsonl"].splitlines()]
    rows[0]["question"] += "invented mutation"
    outputs["external_blind.jsonl"] = p.serialize_blind_records(rows)
    with pytest.raises(ProtocolError):
        p.validate_result(tmp_path, binding, digest, outputs)
