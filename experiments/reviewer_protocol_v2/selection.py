"""Bound offline selector. The real-selection entry point remains disabled."""

import json
import math
import platform
import re
import sys
from pathlib import Path

from experiments.reviewer_protocol_v2.common import (
    ProtocolError, canonical, check_runtime, contained, decode, question_hash,
    require, sha_bytes, verify_file, verified_bytes,
)
from experiments.reviewer_protocol_v2.eligibility import FIELDS, STRATA, reference_index
from experiments.reviewer_protocol_v2.similarity import SOURCE_SHA256, cos, grams, verify_isolation

SEED = 20261001
STRATUM_ORDER = STRATA
STRATUM_ENTRIES = tuple(
    dict(stratum=label, source=source, native_sampling_stratum=native, quota=quota)
    for label, source, native, quota in (
        ("TAT-QA", "tatqa", "T1_qa", 4), ("FinQA", "finqa", "T1_qa", 4),
        ("FinLFQA numerical", "finlfqa", "num", 4),
        ("FinLFQA interpretive", "finlfqa", "interp", 6),
        ("FinLFQA other", "finlfqa", "other", 4),
        ("FinLFQA mixed", "finlfqa", "mixed", 2),
    )
)
PREFIX = "main/experiments/reviewer_protocol_v2/"
BUNDLE_PATHS = (
    "main/experiments/__init__.py", PREFIX + "__init__.py", PREFIX + "common.py",
    PREFIX + "eligibility.py", PREFIX + "similarity.py", PREFIX + "selection.py",
    PREFIX + "packet_serialization.py",
)
# Manifest keys retain their historical "main/" namespace. Physical sources
# belong to this checkout, which need not itself be named "main".
SOURCE_ROOT = Path(__file__).resolve().parents[2]


def repository_source_path(relative):
    """Resolve a logical repository binding, never an external evidence path."""
    require(type(relative) is str and "\\" not in relative and ":" not in relative,
            "repository_source_path")
    parts = relative.split("/")
    require(len(parts) > 1 and parts[0] == "main"
            and all(p not in {"", ".", ".."} for p in parts),
            "repository_source_path")
    return contained(SOURCE_ROOT, "/".join(parts[1:]))


def select(*args, **kwargs):
    raise ProtocolError("selection_disabled_pending_real_authorization")


def exact_keys(value, keys, code="schema_keys"):
    require(type(value) is dict and set(value) == set(keys), code)


def hex256(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "sha256_type")


def B(value):
    try:
        return json.dumps(value, ensure_ascii=True, allow_nan=False,
                          separators=(",", ":")).encode("utf-8", errors="strict")
    except (UnicodeError, ValueError, TypeError):
        raise ProtocolError("invalid_preimage") from None


def identity(row):
    return {"source": row["source"], "candidate_id": row["cand_id"]}


def validate_identity(source, candidate_id):
    require(type(source) is str and source in {"tatqa", "finqa", "finlfqa"}, "source")
    require(type(candidate_id) is str and re.fullmatch(r"c_[0-9a-f]{10}", candidate_id), "candidate_id")


def stratum_label(row):
    validate_identity(row.get("source"), row.get("cand_id"))
    require(type(row.get("sampling_stratum")) is str, "native_stratum")
    matches = [e["stratum"] for e in STRATUM_ENTRIES
               if (e["source"], e["native_sampling_stratum"]) ==
               (row["source"], row["sampling_stratum"])]
    require(len(matches) == 1, "source_stratum_pair")
    return matches[0]


def ranking_preimage(row):
    return B(["reviewer-protocol-v2-rank-v1", SEED, stratum_label(row),
              row["source"], row["cand_id"]])


def ranking_digest(row):
    import hashlib
    return hashlib.sha256(ranking_preimage(row)).digest()


def ranking_key(row):
    return ranking_digest(row), row["cand_id"].encode("utf-8"), row["source"].encode("utf-8")


def runtime_binding():
    checked = check_runtime()
    return dict(python_implementation=checked["implementation"], python_version=checked["python"],
                unicode_version=checked["unicode"], platform=platform.platform(),
                machine=platform.machine(), byteorder=sys.byteorder,
                float_radix=sys.float_info.radix, float_mant_dig=sys.float_info.mant_dig,
                float_max_exp=sys.float_info.max_exp)


def selection_bundle():
    files = {p: sha_bytes(repository_source_path(p).read_bytes()) for p in BUNDLE_PATHS}
    return {"files": files, "sha256": sha_bytes(canonical(files))}


def bound_path(root, relative):
    require(type(relative) is str and "\\" not in relative and ":" not in relative,
            "relative_path")
    parts = relative.split("/")
    require(len(parts) > 1 and parts[0] in {"main", "heldout-external"}
            and all(p not in {"", ".", ".."} for p in parts), "relative_path")
    path = contained(root, relative)
    approved = contained(root, parts[0])
    require(path.is_relative_to(approved), "approved_root")
    return path


def file_binding(root, value):
    exact_keys(value, ("path", "sha256"))
    hex256(value["sha256"])
    path = bound_path(root, value["path"])
    verify_file(path, value["sha256"])
    return path


def read_file_binding(root, value):
    exact_keys(value, ("path", "sha256"))
    hex256(value["sha256"])
    return verified_bytes(bound_path(root, value["path"]), value["sha256"])


def verify_input_binding(root, binding, expected_sha256):
    """Legacy path view; parsing consumers use captured verified buffers."""
    return _verify_input_binding(root, binding, expected_sha256)[0]


def _verify_input_binding(root, binding, expected_sha256):
    hex256(expected_sha256)
    exact_keys(binding, ("schema", "artifacts", "code", "runtime", "seed", "strata"))
    require(sha_bytes(canonical(binding)) == expected_sha256, "inputs_binding_hash")
    require(binding["schema"] == "reviewer-protocol-v2-selection-inputs-v1", "inputs_schema")
    require(type(binding["seed"]) is int and binding["seed"] == SEED, "seed")
    require(type(binding["strata"]) is list and len(binding["strata"]) == 6, "strata")
    for actual, expected in zip(binding["strata"], STRATUM_ENTRIES, strict=True):
        exact_keys(actual, expected)
        require(type(actual["quota"]) is int and canonical(actual) == canonical(expected), "strata")
    expected_runtime = runtime_binding()
    exact_keys(binding["runtime"], expected_runtime)
    require(all(type(binding["runtime"][k]) is type(v) for k, v in expected_runtime.items())
            and binding["runtime"] == expected_runtime, "runtime_binding")
    names = ("population", "exposure_inventory", "eligibility_ledger", "selection_specification")
    exact_keys(binding["artifacts"], names)
    buffers = {name: read_file_binding(root, binding["artifacts"][name]) for name in names}
    paths = {name: bound_path(root, binding["artifacts"][name]["path"]) for name in names}
    require(all(binding["artifacts"][n]["path"].startswith("heldout-external/") for n in names)
            and len(set(paths.values())) == 4, "artifact_paths")
    code = binding["code"]
    exact_keys(code, ("ledger_audit_implementation_sha256", "eligibility_module", "similarity_module",
                      "historical_similarity_source", "selection_bundle"))
    hex256(code["ledger_audit_implementation_sha256"])
    for name, filename in (("eligibility_module", "eligibility.py"), ("similarity_module", "similarity.py")):
        exact_keys(code[name], ("path", "sha256"))
        require(code[name]["path"] == PREFIX + filename, "module_path")
        file_binding(root, code[name])
        require(code[name]["sha256"] == sha_bytes(repository_source_path(PREFIX + filename).read_bytes()),
                "executing_module_hash")
    historical_raw = read_file_binding(root, code["historical_similarity_source"])
    historical = bound_path(root, code["historical_similarity_source"]["path"])
    require(code["historical_similarity_source"]["sha256"] == SOURCE_SHA256, "historical_similarity_hash")
    verify_isolation(historical, historical_raw)
    exact_keys(code["selection_bundle"], ("files", "sha256"))
    require(canonical(code["selection_bundle"]) == canonical(selection_bundle()), "executing_bundle")
    for relative, digest in code["selection_bundle"]["files"].items():
        verify_file(bound_path(root, relative), digest)
    return paths, buffers


def jsonl_records(raw):
    require(type(raw) is bytes and raw.endswith(b"\n") and not raw.startswith(b"\xef\xbb\xbf"), "jsonl_bytes")
    try:
        rows = [decode(line) for line in raw.decode("utf-8", errors="strict").split("\n")[:-1]]
    except UnicodeError:
        raise ProtocolError("jsonl_utf8") from None
    require(all(type(row) is dict for row in rows), "jsonl_records")
    return rows


def prepare_inputs(root, binding, expected_sha256):
    _, buffers = _verify_input_binding(root, binding, expected_sha256)
    population = jsonl_records(buffers["population"])
    rows = jsonl_records(buffers["eligibility_ledger"])
    refs = reference_index(population)
    require(len(rows) == len(population), "ledger_population_size")
    seen = set()
    for row in rows:
        require(all(type(row.get(f)) is str for f in FIELDS), "ledger_field_type")
        stratum_label(row)
        require(row["cand_id"] not in seen and row["cand_id"] in refs, "ledger_identity")
        seen.add(row["cand_id"])
        original = next(p for p in population if p["cand_id"] == row["cand_id"])
        require(all(row[f] == original[f] for f in FIELDS), "ledger_metadata")
        try:
            for f in FIELDS:
                row[f].encode("utf-8", errors="strict")
            actual_hash = question_hash(row["question"])
        except UnicodeError:
            raise ProtocolError("question_utf8") from None
        hex256(row.get("question_sha256"))
        require(row["question_sha256"] == actual_hash, "question_hash")
        require(row.get("implementation_sha256") == binding["code"]["ledger_audit_implementation_sha256"],
                "ledger_implementation")
        require(type(row.get("eligibility")) is dict and row["eligibility"].get("disposition")
                in {"SCREEN_PASS", "DEPENDENCE_EXCLUDED", "DIAGNOSTIC_ONLY", "INPUT_INVALID"}, "eligibility_disposition")
        require(type(row.get("exposure")) is dict, "exposure")
        flags = [row["exposure"].get(k) for k in ("direct", "native_group", "near_duplicate")]
        require(all(type(v) is bool for v in flags) and type(row.get("final_unexposed_screen_pass")) is bool,
                "eligibility_flags")
        require(row["final_unexposed_screen_pass"] ==
                (row["eligibility"]["disposition"] == "SCREEN_PASS" and not any(flags)), "final_flag")
    return rows


def ranked_stratum(rows, label):
    prepared = [(ranking_key(row), row) for row in rows
                if row["final_unexposed_screen_pass"] and stratum_label(row) == label]
    return sorted(prepared, key=lambda pair: pair[0])


def conflicts_with(row, accepted):
    result = []
    for previous in accepted:
        base = dict(with_source=previous["source"], with_candidate_id=previous["cand_id"])
        if (row["source"], row["context_group"]) == (previous["source"], previous["context_group"]):
            result.append(dict(code="NATIVE_GROUP_CONFLICT", similarity_hex=None, **base))
        score = cos(grams(row["question"]), grams(previous["question"]))
        require(math.isfinite(score), "similarity_finite")
        if score >= 0.90:
            result.append(dict(code="DIRECT_SIMILARITY_CONFLICT", similarity_hex=score.hex(), **base))
    return result


def decision(row, label, index, digest, conflicts):
    return dict(stratum=label, scan_index=index, **identity(row), rank_sha256=digest.hex(),
                decision="SKIPPED" if conflicts else "ACCEPTED", conflicts=conflicts)


def scan(rows, inputs_sha256):
    accepted, decisions, results = [], [], []
    stopped = None
    for entry in STRATUM_ENTRIES:
        label, quota = entry["stratum"], entry["quota"]
        count = scanned = 0
        if stopped is None:
            for key, row in ranked_stratum(rows, label):
                scanned += 1
                conflicts = conflicts_with(row, accepted)
                decisions.append(decision(row, label, scanned, key[0], conflicts))
                if not conflicts:
                    accepted.append(row)
                    count += 1
                if count == quota:
                    break
            if count < quota:
                stopped = label
            status = "FILLED" if count == quota else "SHORTFALL"
        else:
            status = "NOT_STARTED"
        results.append(dict(stratum=label, quota=quota, status=status, scanned=scanned,
                            accepted=count, skipped=scanned-count))
    receipt = dict(schema="reviewer-protocol-v2-selection-receipt-v1",
                   status="SUCCESS" if stopped is None else "SHORTFALL", inputs_sha256=inputs_sha256,
                   seed=SEED, stratum_results=results, decisions=decisions,
                   accepted_identities=[identity(r) for r in accepted], stopped_stratum=stopped,
                   packet_sha256=None, mapping_sha256=None)
    return accepted, receipt


def replay_receipt(rows, receipt, inputs_sha256):
    """Independent event consumer; never trusts recorded decisions or counters."""
    exact_keys(receipt, ("schema", "status", "inputs_sha256", "seed", "stratum_results", "decisions",
                         "accepted_identities", "stopped_stratum", "packet_sha256", "mapping_sha256"))
    require(receipt["schema"] == "reviewer-protocol-v2-selection-receipt-v1"
            and receipt["inputs_sha256"] == inputs_sha256
            and type(receipt["seed"]) is int and receipt["seed"] == SEED, "receipt_binding")
    require(type(receipt["decisions"]) is list and type(receipt["stratum_results"]) is list
            and len(receipt["stratum_results"]) == 6, "receipt_arrays")
    accepted, cursor, stopped = [], 0, None
    for entry, result in zip(STRATUM_ENTRIES, receipt["stratum_results"], strict=True):
        label, quota = entry["stratum"], entry["quota"]
        count = scanned = 0
        status = "NOT_STARTED"
        if stopped is None:
            for key, row in ranked_stratum(rows, label):
                scanned += 1
                conflicts = conflicts_with(row, accepted)
                expected = decision(row, label, scanned, key[0], conflicts)
                require(cursor < len(receipt["decisions"])
                        and canonical(receipt["decisions"][cursor]) == canonical(expected), "receipt_decision")
                cursor += 1
                if not conflicts:
                    accepted.append(row)
                    count += 1
                if count == quota:
                    break
            status = "FILLED" if count == quota else "SHORTFALL"
            if count < quota:
                stopped = label
        expected_result = dict(stratum=label, quota=quota, status=status, scanned=scanned,
                               accepted=count, skipped=scanned-count)
        require(canonical(result) == canonical(expected_result), "receipt_counter")
    require(cursor == len(receipt["decisions"])
            and canonical(receipt["accepted_identities"]) == canonical([identity(r) for r in accepted])
            and receipt["stopped_stratum"] == stopped
            and receipt["status"] == ("SUCCESS" if stopped is None else "SHORTFALL"), "receipt_result")
    if stopped is not None:
        require(receipt["packet_sha256"] is None and receipt["mapping_sha256"] is None, "shortfall_outputs")
    else:
        require(len(accepted) == 24, "production_size")
        hex256(receipt["packet_sha256"])
        hex256(receipt["mapping_sha256"])
    return accepted


def select_bound_inputs(root, binding, expected_sha256):
    """Pure selection computation; caller authorization is outside this API."""
    rows = prepare_inputs(root, binding, expected_sha256)
    accepted, receipt = scan(rows, expected_sha256)
    from experiments.reviewer_protocol_v2.packet_serialization import build_external_outputs, validate_result
    payloads = {}
    if receipt["status"] == "SUCCESS":
        packet, mapping = build_external_outputs(accepted, expected_sha256)
        payloads.update({"external_blind.jsonl": packet, "private_mapping.json": mapping})
        receipt.update(packet_sha256=sha_bytes(packet), mapping_sha256=sha_bytes(mapping))
    payloads["selection_receipt.json"] = canonical(receipt)
    validate_result(root, binding, expected_sha256, payloads)
    return payloads
