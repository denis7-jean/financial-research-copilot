"""Fixed accepted reconstruction recipe, not a discovery scan or exposure search."""

import ast
import csv
import re
from pathlib import Path
from experiments.reviewer_protocol_v2.common import (
    question_hash,
    read_json,
    read_jsonl,
    require,
    sha_bytes,
    verify_file,
)
from experiments.reviewer_protocol_v2.eligibility import FIELDS, reference_index
from experiments.reviewer_protocol_v2.exposure import (
    InventoryBuilder,
    validate_inventory,
)
from experiments.reviewer_protocol_v2.integrity import DESIGN_HASHES, RECOVERY_SHA256

DOC_QUOTES_SHA256 = "b8faf6989e4dcc52d13b2dc47eb793a30b79f1daa8a1d31a05208058e7ccb082"


def load_population(root):
    ext = Path(root) / "heldout-external"
    for relative, expected in {
        "out/candidates.jsonl": "89d840aacdd353928649bc72daa08921b428af217f9362786d524ef2a23e6775",
        "out/manifest.json": "e7929883b6ab73052aee912b8fd0a8ad97e4dd11a59adbd653f717688dac38b6",
        "out/blind_review_packet.jsonl": "1bb8c3200634cedfe621fdc2e06bce293e93c77040c01719184d9960a917fbb8",
    }.items():
        verify_file(ext / "pilot-v1" / relative, expected)
    rows = read_jsonl(ext / "pilot-v1/out/candidates.jsonl")
    # Drop label, source-answer and historical rank fields without inspecting their values.
    rows = [{key: row[key] for key in FIELDS} for row in rows]
    refs = reference_index(rows)
    manifest = read_json(ext / "pilot-v1/out/manifest.json")
    require(len(rows) == 104, "canonical_population_size")
    require(
        all(
            row["source_revision"] == manifest["inputs"][row["source"]]["revision"]
            for row in rows
        ),
        "canonical_source_revision",
    )
    blind = read_jsonl(ext / "pilot-v1/out/blind_review_packet.jsonl")
    require(
        len(blind) == 104 and len({r["cand_id"] for r in blind}) == 104,
        "pilot_blind_size",
    )
    require(
        all(
            r["cand_id"] in refs
            and question_hash(r["question"]) == refs[r["cand_id"]]["question_sha256"]
            for r in blind
        ),
        "pilot_blind_binding",
    )
    return rows


def reconstruct(root, population):
    root = Path(root).resolve()
    ext, main = root / "heldout-external", root / "main"
    private = ext / "reviewer-protocol-v2-offline"
    builder = InventoryBuilder(population)
    source_hashes = {}

    def digest(path):
        path = Path(path)
        key = path.relative_to(root).as_posix()
        source_hashes[key] = sha_bytes(path.read_bytes())
        return key, source_hashes[key]

    def add(category, path, locator, **kwargs):
        source, digest_ = digest(path)
        builder.add(category, source, digest_, locator, **kwargs)

    versions = ("reviewer-protocol-v1", "reviewer-trial-v1.1", "reviewer-trial-v1.2")
    maps, sets = {}, {}
    for version in versions:
        filename = (
            "trial_items.jsonl"
            if version == versions[0]
            else "PRIVATE_trial_items.jsonl"
        )
        path = ext / version / filename
        items = read_jsonl(path)
        sets[version] = {row["cand_id"] for row in items}
        require(len(items) == len(sets[version]) == 12, "historical_packet_size")
        for index, row in enumerate(items, 1):
            add(
                "historical_trial_packet",
                path,
                "line:" + str(index),
                cid=row["cand_id"],
                question=row["question"],
                stage=version,
            )
        mapping = {}
        path = ext / version / "trial_blind_packet.jsonl"
        for index, row in enumerate(read_jsonl(path), 1):
            ids, _ = builder.identify(question=row["question"])
            require(len(ids) == 1, "historical_blind_unique_identity")
            mapping[row.get("item_id", row.get("cand_id"))] = ids[0]
            add(
                "historical_trial_packet",
                path,
                "line:" + str(index),
                question=row["question"],
                stage=version,
            )
        require(
            set(mapping.values()) == sets[version], "historical_private_blind_agreement"
        )
        maps[version] = mapping
        path = ext / version / "trial_request_bodies.jsonl"
        requests = read_jsonl(path)
        require(len(requests) == 36, "historical_prepared_request_count")
        for index, row in enumerate(requests, 1):
            questions = []
            for message in row["converse_kwargs"]["messages"]:
                for block in message["content"]:
                    if "text" in block:
                        questions.extend(
                            re.findall(
                                r"<question>\n(.*?)\n</question>",
                                block["text"],
                                flags=re.DOTALL,
                            )
                        )
            require(len(questions) == 1, "historical_request_complete_question")
            cid = row.get("cand_id") or mapping.get(row.get("item_id"))
            add(
                "reviewer_request",
                path,
                "line:" + str(index),
                cid=cid,
                question=questions[0],
                stage=version + " prepared request",
                actor=row["reviewer_id"],
            )
    require(sets[versions[1]] == sets[versions[2]], "historical_trial_same_membership")
    control_path = ext / versions[1] / "PRIVATE_control_review.json"
    removed = []
    for index, row in enumerate(read_json(control_path)["current_controls"]):
        if row["decision"] == "replace":
            removed.append(row["cand_id"])
            add(
                "removed_control",
                control_path,
                "current_controls/" + str(index),
                cid=row["cand_id"],
                stage="v1.1 control review",
                completeness="canonical_id_binding",
            )
    require(len(removed) == 1, "removed_control_count")
    receipt = read_json(ext / "owner-audit-trial-v1.1/audit_receipt.json")
    paths = [ext / versions[0] / "owner_audit_packet_trial.csv"] + [
        ext / "owner-audit-trial-v1.1" / filename
        for filename in (
            "audit_trial_v1.1.BLANK.csv",
            "audit_trial_v1.1.csv",
            "audit_trial_v1.1.SEALED.csv",
        )
    ]
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 12, "historical_audit_size")
        for index, row in enumerate(rows, 2):
            sealed = path.name == receipt["completed_file"]
            add(
                "owner_audit",
                path,
                "csv_row:" + str(index),
                question=row["question"],
                stage="historical owner-facing audit",
                actor="owner",
                timestamp=receipt["sealed_utc"] if sealed else None,
                timestamp_basis="sealed audit receipt" if sealed else None,
            )
    for relative in (
        "reviewer-trial-v1.1/runs/dryrun-20260929T053325Z/journal.jsonl",
        "reviewer-trial-v1.1/runs/dryrun-20260929T053352Z/journal.jsonl",
        "reviewer-trial-v1.2/runs/live-20260930T223024Z/journal.jsonl",
    ):
        path = ext / relative
        rows = read_jsonl(path)
        version = path.parents[2].name
        live = next(row["live"] for row in rows if row["event"] == "run_started")
        calls = [
            (index, row)
            for index, row in enumerate(rows, 1)
            if row["event"] == "call_started"
        ]
        require(len(calls) == 36, "historical_journal_start_count")
        for index, row in calls:
            require(row["item_id"] in maps[version], "historical_journal_identity")
            add(
                "reviewer_request",
                path,
                "line:" + str(index),
                cid=maps[version][row["item_id"]],
                stage="historical live request"
                if live
                else "historical offline dry-run record",
                actor=row["reviewer_id"],
                timestamp=row["ts"],
                timestamp_basis="call_started journal record",
                completeness="canonical_id_binding",
            )
    prep = main / "docs/experiments/external-pilot-preparation.md"
    lines = prep.read_text(encoding="utf-8-sig").splitlines()
    disclosed = []
    for line in (79, 241, 243, 245):
        ids = re.findall(r"c_[0-9a-f]{10}", lines[line - 1])
        require(len(ids) == 1, "accepted_planning_id_locator")
        disclosed.append(ids[0])
        add(
            "planning_document_disclosure",
            prep,
            "line:" + str(line),
            cid=ids[0],
            stage="documented historical disclosure",
            completeness="canonical_id_binding",
        )
    path = ext / versions[1] / "CONTROL_RULE.md"
    require(
        removed[0] in path.read_text(encoding="utf-8-sig").splitlines()[3],
        "accepted_control_locator",
    )
    add(
        "removed_control",
        path,
        "line:4",
        cid=removed[0],
        stage="documented historical disclosure",
        completeness="canonical_id_binding",
    )
    for filename, expected in DESIGN_HASHES.items():
        verify_file(private / filename, expected)
    history = private / "original-design-evidence.md"
    text = history.read_text(encoding="utf-8")
    for cid in disclosed + removed:
        require(cid in text, "accepted_history_id_evidence")
        add(
            "work_history_disclosure",
            history,
            "explicit historical candidate reference:" + cid,
            cid=cid,
            stage="prior Work-session disclosure",
            completeness="canonical_id_binding",
            metadata={
                "chat": "01a0f4d3-eeb5-7d20-b31c-f09234c0ef1d",
                "turn": "01a0f5c7-3f42-7280-ab97-9d1dbab65fc6",
            },
        )
    for relative in (
        "eval/results/baselines/2026-09-phase0-baseline.json",
        "eval/results/latest.json",
        "eval/results/legacy/2026-06-04_pre_phase0_harness.json",
    ):
        path = main / relative
        for index, row in enumerate(read_json(path)["results"]):
            add(
                "other_documented_exposure",
                path,
                "results/" + str(index) + "/query",
                question=row["query"],
                stage="historical evaluation request",
            )
    eval_source = main / "eval/eval_queries.py"
    digest(eval_source)
    cases = {}
    for node in ast.walk(ast.parse(eval_source.read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "EvalCase"
            and len(node.args) >= 2
        ):
            key, question = (
                ast.literal_eval(node.args[0]),
                ast.literal_eval(node.args[1]),
            )
            require(
                isinstance(key, str) and isinstance(question, str),
                "historical_case_type",
            )
            cases[key] = question
    for relative in (
        "eval/results/experiments/2026-09-28-jev-verification/jev-verification-20260928T204426Z.json",
        "eval/results/experiments/2026-09-28-phase-a-benchmark/benchmark-20260928T233432Z.json",
    ):
        path = main / relative
        for index, row in enumerate(read_json(path)["records"]):
            require(row["case_id"] in cases, "historical_case_binding")
            add(
                "other_documented_exposure",
                path,
                "records/" + str(index) + "/case_id",
                question=cases[row["case_id"]],
                stage="historical Phase-A execution",
                metadata={
                    "question_source": digest(eval_source)[0],
                    "question_source_sha256": digest(eval_source)[1],
                },
            )
    doc = main / "docs/experiments/external-dataset-feasibility.md"
    text = doc.read_text(encoding="utf-8-sig")
    quotes_path = private / "document-quotes.json"
    verify_file(quotes_path, DOC_QUOTES_SHA256)
    for question in read_json(quotes_path):
        require(question in text, "accepted_document_quote_present")
        add(
            "planning_document_disclosure",
            doc,
            "full_quote_line:" + str(text.count("\n", 0, text.index(question)) + 1),
            question=question,
            stage="2026-09-28 dataset-feasibility disclosure",
        )
    for relative, line_numbers in (
        ("docs/experiments/heldout-routing-protocol.md", (190,)),
        ("docs/experiments/router-benchmark-design.md", (241, 635, 636, 638)),
    ):
        path = main / relative
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for line in line_numbers:
            quotes = re.findall(r'"([^"]+)"', lines[line - 1])
            require(
                len(quotes) == 1 and question_hash(quotes[0]) in builder.outside,
                "accepted_planning_full_quote_locator",
            )
            add(
                "planning_document_disclosure",
                path,
                "full_quote_line:" + str(line),
                question=quotes[0],
                stage="historical planning disclosure",
            )
    path = main / "README.md"
    text = path.read_text(encoding="utf-8-sig")
    examples = re.findall(r'"query":\s*"([^"]+)"', text)
    require(len(examples) == 2, "accepted_readme_example_count")
    for question in examples:
        add(
            "other_documented_exposure",
            path,
            "query_example_line:" + str(text.count("\n", 0, text.index(question)) + 1),
            question=question,
            stage="durable README request example",
        )
    recovery_path = private / "recovered-references.json"
    verify_file(recovery_path, RECOVERY_SHA256)
    recovered = read_json(recovery_path)
    require(len(recovered) == 5, "accepted_recovery_size")
    for record in recovered:
        require(
            record["complete"] is True
            and record["status"] == "RECOVERED_EXACT"
            and question_hash(record["question"]) == record["question_sha256"],
            "accepted_recovery_binding",
        )
        metadata = {key: value for key, value in record.items() if key != "question"}
        metadata.update(
            {
                "recovery_extract": digest(recovery_path)[0],
                "recovery_extract_sha256": RECOVERY_SHA256,
            }
        )
        add(
            "planning_document_disclosure",
            doc,
            "recovered_quote_line:" + str(record["line"]),
            question=record["question"],
            stage="accepted bounded provenance recovery",
            completeness="accepted_exact_recovery",
            metadata=metadata,
        )
    inventory = builder.finish()
    inventory["supporting_files"] = dict(sorted(source_hashes.items()))
    validate_inventory(inventory, population)
    require(
        len(inventory["pilot_items"]) == 15
        and len(inventory["outside_items"]) == 48
        and len(inventory["references"]) == 63
        and len(inventory["evidence"]) == 1480,
        "accepted_inventory_invariants",
    )
    return inventory
