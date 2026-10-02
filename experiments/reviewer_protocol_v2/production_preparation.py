"""Read-only binding preparation. No ranking, selection, publication or sealing."""

from experiments.reviewer_protocol_v2.common import (
    ProtocolError,
    canonical,
    require,
    sha_bytes,
)
from experiments.reviewer_protocol_v2.control_serialization import object_bytes, schema
from experiments.reviewer_protocol_v2.exposure import validate_inventory
from experiments.reviewer_protocol_v2.ledger_adoption import (
    _history,
    verify_adoption,
    read_binding,
)
from experiments.reviewer_protocol_v2.selection import (
    PREFIX,
    SOURCE_ROOT,
    STRATUM_ENTRIES,
    SEED,
    bound_path,
    exact_keys,
    hex256,
    jsonl_records,
    prepare_inputs,
    runtime_binding,
    selection_bundle,
)
from experiments.reviewer_protocol_v2.trial_interfaces import (
    INTERFACE_BUNDLE_PATHS,
    interface_bundle,
)

VERIFICATION_BUNDLE_PATHS = (
    *INTERFACE_BUNDLE_PATHS,
    PREFIX + "exposure.py",
    PREFIX + "ledger_adoption.py",
    PREFIX + "production_preparation.py",
)


def verification_bundle(sources):
    exact_keys(sources, VERIFICATION_BUNDLE_PATHS)
    require(all(type(v) is bytes for v in sources.values()), "verification_source_type")
    files = {p: sha_bytes(raw) for p, raw in sources.items()}
    return dict(files=files, sha256=sha_bytes(canonical(files)))


def _executing_sources(root, sources):
    exact_keys(sources, VERIFICATION_BUNDLE_PATHS, "executing_source_set")
    for path, raw in sources.items():
        require(
            type(raw) is bytes
            and raw == (SOURCE_ROOT / path).read_bytes()
            and raw == bound_path(root, path).read_bytes(),
            "executing_source_mismatch",
        )
    return verification_bundle(sources)


def prepare(
    root,
    artifacts,
    code_bindings,
    generating_sources,
    historical_manifest,
    expected_historical_manifest_sha256,
    executing_sources,
    trusted_expected_inputs_sha256=None,
    proposed_freeze1=None,
    trusted_expected_freeze1_sha256=None,
):
    """Return canonical InputBinding bytes (or None) and accepted PreparationReport bytes.

    Caller-supplied trusted hashes are separate from calculated evidence. PREPARED
    never means authorized, operationally adopted, frozen, or selection-ready.
    """
    digest = freeze_hash = None
    findings = []
    phase = "CODE_BINDING"
    try:
        _executing_sources(root, executing_sources)
        exact_keys(
            code_bindings,
            (
                "ledger_audit_implementation_sha256",
                "eligibility_module",
                "similarity_module",
                "historical_similarity_source",
                "selection_bundle",
            ),
        )
        require(
            code_bindings["selection_bundle"] == selection_bundle(),
            "selection_source_binding",
        )
        # Explicitly check the unchanged interface sources separately from the historical audit.
        current_interface = interface_bundle(
            {p: executing_sources[p] for p in INTERFACE_BUNDLE_PATHS}
        )
        require(
            current_interface["sha256"]
            != code_bindings["ledger_audit_implementation_sha256"],
            "historical_current_digest_confusion",
        )
        phase = "RUNTIME_BINDING"
        runtime = runtime_binding()
        value = dict(
            schema="reviewer-protocol-v2-selection-inputs-v1",
            artifacts=artifacts,
            code=code_bindings,
            runtime=runtime,
            seed=SEED,
            strata=list(STRATUM_ENTRIES),
        )
        raw = canonical(value)
        digest = sha_bytes(raw)
        phase = "INPUT_HASH"
        if trusted_expected_inputs_sha256 is not None:
            hex256(trusted_expected_inputs_sha256)
            require(
                digest == trusted_expected_inputs_sha256, "trusted_input_hash_mismatch"
            )
        phase = "IDENTITY_BINDING"
        rows = prepare_inputs(root, value, digest)
        phase = "INPUT_SCHEMA"
        population = jsonl_records(read_binding(root, artifacts["population"]))
        inventory = object_bytes(read_binding(root, artifacts["exposure_inventory"]))
        validate_inventory(inventory, population)
        direct = {item["cand_id"] for item in inventory["pilot_items"]}
        require(
            all(
                row["exposure"]["direct"] == (row["cand_id"] in direct) for row in rows
            ),
            "inventory_ledger_direct_flags",
        )
        phase = "CODE_BINDING"
        history = _history(
            root,
            historical_manifest,
            expected_historical_manifest_sha256,
            generating_sources,
        )
        require(
            history["digest"] == code_bindings["ledger_audit_implementation_sha256"],
            "historical_current_digest_confusion",
        )
        phase = "INPUT_HASH"
        require(
            read_binding(root, artifacts["eligibility_ledger"])
            == history["payloads"]["population_ledger.jsonl"]
            and read_binding(root, artifacts["exposure_inventory"])
            == history["payloads"]["inventory.json"],
            "original_audit_payload_binding",
        )
        require(
            all(r["implementation_sha256"] == history["digest"] for r in rows),
            "ledger_provenance_binding",
        )
        phase = "FREEZE_BINDING"
        adoption = verify_adoption(
            root,
            historical_manifest,
            expected_historical_manifest_sha256,
            generating_sources,
            artifacts["population"],
            artifacts["eligibility_ledger"],
            code_bindings["selection_bundle"],
            proposed_freeze1,
            trusted_expected_freeze1_sha256,
            executing_sources=executing_sources,
            input_binding_raw=raw,
        )
        require(
            adoption["historical_provenance_verified"]
            and adoption["code"] == "BINDINGS_VERIFIED_NOT_ADOPTED",
            "adoption_provenance_failure",
        )
        if proposed_freeze1 is not None:
            require(
                adoption["proposed_freeze_compatible"] is True,
                "proposed_freeze_mismatch",
            )
            freeze_hash = trusted_expected_freeze1_sha256
        return raw, canonical(
            dict(
                schema=schema("production-preparation"),
                status="PREPARED",
                inputs_sha256=digest,
                freeze1_sha256=freeze_hash,
                findings=[],
            )
        )
    except ProtocolError as error:
        code = str(error)
        if "path" in code or "root" in code:
            phase = "PATH_BINDING"
        elif "runtime" in code or "unicode_requires" in code:
            phase = "RUNTIME_BINDING"
        elif "question" in code:
            phase = "QUESTION_HASH"
        findings.append(dict(code=phase, artifact=None))
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        SyntaxError,
    ):
        findings.append(dict(code=phase, artifact=None))
    return None, canonical(
        dict(
            schema=schema("production-preparation"),
            status="FAILED",
            inputs_sha256=digest,
            freeze1_sha256=freeze_hash,
            findings=findings,
        )
    )


def validate_preparation(
    root,
    binding_raw,
    report_raw,
    trusted_expected_inputs_sha256,
    trusted_expected_freeze1_sha256=None,
):
    """Check completed report/binding bytes against a separately supplied expected hash."""
    hex256(trusted_expected_inputs_sha256)
    binding = object_bytes(binding_raw)
    exact_keys(binding, ("schema", "artifacts", "code", "runtime", "seed", "strata"))
    prepare_inputs(root, binding, trusted_expected_inputs_sha256)
    report = object_bytes(report_raw)
    exact_keys(
        report, ("schema", "status", "inputs_sha256", "freeze1_sha256", "findings")
    )
    require(
        report["schema"] == schema("production-preparation")
        and report["status"] == "PREPARED"
        and report["findings"] == []
        and report["inputs_sha256"] == trusted_expected_inputs_sha256
        and sha_bytes(binding_raw) == trusted_expected_inputs_sha256,
        "trusted_preparation_hash",
    )
    require(
        report["freeze1_sha256"] == trusted_expected_freeze1_sha256,
        "trusted_preparation_freeze_hash",
    )
    if trusted_expected_freeze1_sha256 is not None:
        hex256(trusted_expected_freeze1_sha256)
    return binding
