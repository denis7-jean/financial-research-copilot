"""Unselected offline population audit; exposes only counts/hashes to the caller."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from experiments.reviewer_protocol_v2.common import (
    canonical,
    check_runtime,
    question_hash,
    require,
    sha_bytes,
)
from experiments.reviewer_protocol_v2.constraints import constraint_summary
from experiments.reviewer_protocol_v2.eligibility import (
    STRATA,
    classify,
    reference_index,
)
from experiments.reviewer_protocol_v2.exposure import exposure_ledger
from experiments.reviewer_protocol_v2.integrity import (
    verify_historical,
    verify_output_manifest,
)
from experiments.reviewer_protocol_v2.known_inventory import (
    load_population,
    reconstruct,
)
from experiments.reviewer_protocol_v2.similarity import verify_isolation


def implementation_hash():
    folder = Path(__file__).parent
    files = {
        path.name: sha_bytes(path.read_bytes())
        for path in sorted(folder.iterdir())
        if path.suffix in {".py", ".json"}
    }
    return sha_bytes(canonical(files))


def compute(population, inventory):
    refs = reference_index(population)
    exposed = exposure_ledger(population, inventory)
    ledger, retained = [], []
    for row, flags in zip(population, exposed):
        eligibility = classify(row, refs)
        final = eligibility["disposition"] == "SCREEN_PASS" and not any(
            flags[k] for k in ("direct", "native_group", "near_duplicate")
        )
        ledger.append(
            row
            | {
                "question_sha256": question_hash(row["question"]),
                "eligibility": eligibility,
                "exposure": flags,
                "final_unexposed_screen_pass": final,
            }
        )
        if final:
            retained.append(row)
    masks = {
        name: {i for i, flags in enumerate(exposed) if flags[name]}
        for name in ("direct", "native_group", "near_duplicate")
    }
    rule_masks = {
        "E0" + str(k): {
            i
            for i, record in enumerate(ledger)
            if "E0" + str(k) in record["eligibility"]["rules"]
        }
        for k in range(1, 8)
    }
    dispositions = Counter(record["eligibility"]["disposition"] for record in ledger)
    summary = {
        "artifact_type": "offline_unselected_audit",
        "frozen": False,
        "population": len(population),
        "final_unexposed_screen_pass": len(retained),
        "inventory": {
            "direct_pilot": len(inventory["pilot_items"]),
            "outside_complete": len(inventory["outside_items"]),
            "complete_computational_texts": len(inventory["references"]),
            "evidence_records": len(inventory["evidence"]),
            "unresolved": len(inventory["unresolved"]),
            "evidence_categories": dict(
                sorted(Counter(e["category"] for e in inventory["evidence"]).items())
            ),
        },
        "dispositions": {
            name: dispositions[name]
            for name in (
                "SCREEN_PASS",
                "DEPENDENCE_EXCLUDED",
                "DIAGNOSTIC_ONLY",
                "INPUT_INVALID",
            )
        },
        "rule_counts": {name: len(indices) for name, indices in rule_masks.items()},
        "exposure_counts": {name: len(indices) for name, indices in masks.items()},
        "exposure_pair_overlaps": {
            a + "&" + b: len(masks[a] & masks[b])
            for a, b in (
                ("direct", "native_group"),
                ("direct", "near_duplicate"),
                ("native_group", "near_duplicate"),
            )
        },
        "exposure_membership_counts": {
            str(n): sum(
                sum(i in values for values in masks.values()) == n
                for i in range(len(population))
            )
            for n in range(4)
        },
        "rule_exposure_overlaps": {
            rule: {mask: len(indices & values) for mask, values in masks.items()}
            for rule, indices in rule_masks.items()
        },
        "population_reference_comparisons": sum(
            flags["comparisons"] for flags in exposed
        ),
        "outside_reference_threshold_matches": sum(
            not match["pilot_ids"]
            for flags in exposed
            for match in flags["similarity_matches"]
        ),
        "strata": [],
        "constraints": constraint_summary(retained),
    }
    for source, stratum in STRATA:
        indices = [
            i
            for i, row in enumerate(population)
            if (row["source"], row["sampling_stratum"]) == (source, stratum)
        ]
        final_count = sum(ledger[i]["final_unexposed_screen_pass"] for i in indices)
        summary["strata"].append(
            {
                "source": source,
                "stratum": stratum,
                "original": len(indices),
                "final_screen_pass": final_count,
                "retained_fraction": {
                    "numerator": final_count,
                    "denominator": len(indices),
                },
                "raw_dispositions": dict(
                    sorted(
                        Counter(
                            ledger[i]["eligibility"]["disposition"] for i in indices
                        ).items()
                    )
                ),
                "rules": {
                    name: len(set(indices) & mask) for name, mask in rule_masks.items()
                },
                "exposure": {
                    name: len(set(indices) & mask) for name, mask in masks.items()
                },
            }
        )
    return ledger, summary


def run_audit(root, output):
    from tests.offline_guard import install

    install()
    root, output = Path(root).resolve(), Path(output).resolve()
    private = (root / "heldout-external/reviewer-protocol-v2-offline").resolve()
    require(
        private.is_relative_to((root / "heldout-external").resolve())
        and not output.is_relative_to((root / "main").resolve())
        and output.is_relative_to(private)
        and output != private
        and not output.exists(),
        "output_must_be_new_private_directory",
    )
    runtime = check_runtime()
    integrity = verify_historical(root)
    source_hash = verify_isolation(root / "heldout-external/pilot-v1/select_pilot.py")
    from experiments.reviewer_protocol_v2.fixtures import verify_registered

    fixture_result = verify_registered()
    population = load_population(root)
    inventory = reconstruct(root, population)
    ledger, summary = compute(population, inventory)
    impl_hash = implementation_hash()
    summary.update(
        {
            "runtime": runtime,
            "implementation_sha256": impl_hash,
            "similarity_source_sha256": source_hash,
            "registered_fixtures": fixture_result,
        }
    )
    require(verify_historical(root) == integrity, "historical_changed_during_audit")
    payloads = {
        "inventory.json": canonical(inventory),
        "aggregate.json": canonical(summary),
        "integrity.json": canonical(integrity),
        "population_ledger.jsonl": b"".join(
            canonical(record | {"implementation_sha256": impl_hash})
            for record in ledger
        ),
    }
    hashes = {name: sha_bytes(value) for name, value in payloads.items()}
    manifest = {
        "artifact_type": "offline_unselected_audit",
        "frozen": False,
        "schema": "offline_audit_manifest_v2",
        "files": hashes,
        "implementation_sha256": impl_hash,
        "runtime": runtime,
        "byte_contract": "UTF-8; escaped Unicode; sorted keys; compact JSON; finite numbers; LF terminator",
        "self_hash_rule": "manifest excluded from files; receipt holds exact manifest-byte hash",
    }
    payloads["manifest.json"] = canonical(manifest)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in payloads.items():
        with (output / name).open("xb") as stream:
            stream.write(value)
    manifest_hash = verify_output_manifest(output)
    receipt = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_type": "offline_audit_run_receipt",
        "frozen": False,
        "manifest_sha256": manifest_hash,
        "deterministic_hashes": hashes,
        "historical_integrity_verified": True,
    }
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return {
        "aggregate": summary,
        "deterministic_hashes": hashes | {"manifest.json": manifest_hash},
    }
