"""Technical evidence verification only. Never operational approval or readiness."""

import sys
from pathlib import Path

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
    repository_source_path,
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
from experiments.reviewer_protocol_v2.owner_audit import OWNER_BUNDLE_PATHS
from experiments.reviewer_protocol_v2.trial_interfaces import (
    INTERFACE_BUNDLE_PATHS,
    interface_bundle,
)

VERIFICATION_BUNDLE_PATHS = (
    *OWNER_BUNDLE_PATHS,
    PREFIX + "exposure.py",
    PREFIX + "ledger_adoption.py",
    PREFIX + "production_preparation.py",
    PREFIX + "procedure_evidence.py",
    PREFIX + "ledger_reconciliation.py",
)


def verification_bundle(sources):
    exact_keys(sources, VERIFICATION_BUNDLE_PATHS)
    require(all(type(v) is bytes for v in sources.values()), "verification_source_type")
    files = {p: sha_bytes(raw) for p, raw in sources.items()}
    return dict(files=files, sha256=sha_bytes(canonical(files)))


def _executing_sources(root, sources):
    """Compare origins and disk bytes, not loaded instructions or hostile processes."""
    exact_keys(sources, VERIFICATION_BUNDLE_PATHS, "executing_source_set")
    for path, raw in sources.items():
        module_name = path.removeprefix("main/").removesuffix(".py").replace("/", ".")
        if module_name.endswith(".__init__"):
            module_name = module_name.removesuffix(".__init__")
        module = sys.modules.get(module_name)
        require(
            module is not None
            and module.__spec__ is not None
            and Path(module.__spec__.origin).resolve()
            == repository_source_path(path),
            "executing_source_origin",
        )
        require(
            type(raw) is bytes
            and raw == repository_source_path(path).read_bytes()
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
        phase = "INPUT_SCHEMA"
        from experiments.reviewer_protocol_v2.procedure_evidence import (
            selection_specification,
        )

        selection_specification(
            read_binding(root, artifacts["selection_specification"])
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
        LookupError,
        RecursionError,
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
    verification_context=None,
):
    """Return explicit technical assessment; replay evidence when Freeze 1 is claimed."""
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
    level = "BINDING_ONLY"
    if trusted_expected_freeze1_sha256 is not None:
        require(
            type(verification_context) is dict
            and verification_context.get("root") == root,
            "preparation_replay_evidence_required",
        )
        proof = dict(verification_context)
        require(
            proof.get("trusted_expected_freeze1_sha256")
            == trusted_expected_freeze1_sha256,
            "preparation_replay_freeze_binding",
        )
        proof["trusted_expected_inputs_sha256"] = trusted_expected_inputs_sha256
        replay_binding, replay_report = prepare(**proof)
        require(
            replay_binding == binding_raw and replay_report == report_raw,
            "preparation_evidence_replay",
        )
        level = "EVIDENCE_REPLAYED"
    return dict(
        schema=schema("technical-preparation-assessment"),
        binding=binding,
        report_sha256=sha_bytes(report_raw),
        verification_level=level,
        approval_assessed=False,
        operational_readiness=False,
        freeze1_sha256=trusted_expected_freeze1_sha256,
        inputs_sha256=trusted_expected_inputs_sha256,
    )


def selection_phase_predicate(
    assessment,
    authorization_raw,
    trusted_authorization_sha256,
    phase,
    ledger_seal_sha256,
    procedure_sha256,
):
    """Necessary structural predicate for future operational tools; executes nothing.

    Phase/seal/trust must come from independently verified future operational
    evidence. This pure predicate cannot authenticate approval or durable history.
    """
    from experiments.reviewer_protocol_v2.control_serialization import (
        object_bytes,
        relative_path,
    )

    try:
        exact_keys(
            assessment,
            (
                "schema",
                "binding",
                "report_sha256",
                "verification_level",
                "approval_assessed",
                "operational_readiness",
                "freeze1_sha256",
                "inputs_sha256",
            ),
        )
        hex256(assessment["inputs_sha256"])
        hex256(assessment["report_sha256"])
        hex256(trusted_authorization_sha256)
        hex256(ledger_seal_sha256)
        hex256(procedure_sha256)
        require(
            sha_bytes(canonical(assessment["binding"])) == assessment["inputs_sha256"],
            "assessment_input_binding",
        )
        require(
            sha_bytes(authorization_raw) == trusted_authorization_sha256,
            "authorization_trusted_hash",
        )
        grant = object_bytes(authorization_raw)
        exact_keys(
            grant,
            (
                "schema",
                "operation",
                "inputs_sha256",
                "report_sha256",
                "freeze1_sha256",
                "ledger_seal_sha256",
                "procedure_sha256",
                "destination_policy",
            ),
        )
        require(
            grant["schema"] == "reviewer-protocol-v2-selection-authorization-v2",
            "authorization_version",
        )
        require(
            phase == "FREEZE_1_LEDGER_SEALED"
            and assessment["schema"] == schema("technical-preparation-assessment")
            and assessment["verification_level"] == "EVIDENCE_REPLAYED"
            and assessment["approval_assessed"] is False
            and assessment["operational_readiness"] is False,
            "selection_phase",
        )
        hex256(assessment["freeze1_sha256"])
        require(
            grant["operation"] in {"SELECTION", "SELECTION_AND_PUBLICATION"}
            and grant["inputs_sha256"] == assessment["inputs_sha256"]
            and grant["report_sha256"] == assessment["report_sha256"]
            and grant["freeze1_sha256"] == assessment["freeze1_sha256"]
            and grant["ledger_seal_sha256"] == ledger_seal_sha256
            and grant["procedure_sha256"] == procedure_sha256,
            "selection_phase_bindings",
        )
        exact_keys(grant["destination_policy"], ("path", "sha256"))
        relative_path(grant["destination_policy"]["path"])
        hex256(grant["destination_policy"]["sha256"])
        return True
    except (
        ProtocolError,
        OSError,
        ValueError,
        TypeError,
        LookupError,
        AttributeError,
        RecursionError,
    ):
        return False


def reconciliation_preflight(
    root,
    binding_raw,
    report_raw,
    authorization_raw,
    verification_context,
    *,
    phase,
    trusted_expectations=None,
):
    """Replay necessary technical conditions only; never authenticate or dispatch.

    Expected hashes and the seal-to-ledger association must be established by
    external trusted producers, which are not implemented. Caller declarations
    cannot prove approval, phase history or sealing. No operational seal schema
    is inferred from authorization-v2's opaque seal hash.
    """
    result = dict(
        status="FAILED",
        code=None,
        hashes={},
        approval_authenticated=False,
        phase_history_authenticated=False,
        ledger_sealing_authenticated=False,
        operational_adoption_performed=False,
        operational_dispatch_performed=False,
        freeze1_readiness="NOT_ASSESSED",
    )
    stage = "PREFLIGHT_TRUST_FORMAT"
    try:
        require(trusted_expectations is not None, "PREFLIGHT_TRUST_REQUIRED")
        hashes = (
            "inputs_sha256",
            "report_sha256",
            "freeze1_sha256",
            "procedure_sha256",
            "authorization_sha256",
            "ledger_seal_sha256",
        )
        exact_keys(
            trusted_expectations, (*hashes, "sealed_ledger"), "PREFLIGHT_TRUST_SCHEMA"
        )
        for key in hashes:
            hex256(trusted_expectations[key])
        sealed = trusted_expectations["sealed_ledger"]
        exact_keys(sealed, ("path", "sha256"), "PREFLIGHT_SEAL_BINDING_SCHEMA")
        hex256(sealed["sha256"])
        require(phase == "FREEZE_1_LEDGER_SEALED", "PREFLIGHT_PHASE")
        stage = "PREFLIGHT_CONTEXT_MALFORMED"
        exact_keys(
            verification_context,
            (
                "root",
                "artifacts",
                "code_bindings",
                "generating_sources",
                "historical_manifest",
                "expected_historical_manifest_sha256",
                "executing_sources",
                "proposed_freeze1",
                "trusted_expected_freeze1_sha256",
            ),
            "PREFLIGHT_CONTEXT_SCHEMA",
        )
        context = verification_context
        trust = trusted_expectations
        require(context["root"] == root, "PREFLIGHT_CONTEXT_ROOT")
        require(
            context["trusted_expected_freeze1_sha256"] == trust["freeze1_sha256"],
            "PREFLIGHT_CONTEXT_FREEZE_HASH",
        )
        stage = "PREFLIGHT_EVIDENCE_MALFORMED"
        for raw, key, code in (
            (binding_raw, "inputs_sha256", "PREFLIGHT_INPUT_HASH"),
            (report_raw, "report_sha256", "PREFLIGHT_REPORT_HASH"),
            (authorization_raw, "authorization_sha256", "PREFLIGHT_AUTHORIZATION_HASH"),
            (context["proposed_freeze1"], "freeze1_sha256", "PREFLIGHT_FREEZE_HASH"),
        ):
            require(type(raw) is bytes and sha_bytes(raw) == trust[key], code)
        binding = object_bytes(binding_raw)
        report = object_bytes(report_raw)
        exact_keys(
            binding, ("schema", "artifacts", "code", "runtime", "seed", "strata")
        )
        exact_keys(
            report, ("schema", "status", "inputs_sha256", "freeze1_sha256", "findings")
        )
        require(
            report["schema"] == schema("production-preparation")
            and report["status"] == "PREPARED"
            and report["findings"] == []
            and report["inputs_sha256"] == trust["inputs_sha256"]
            and report["freeze1_sha256"] == trust["freeze1_sha256"],
            "PREFLIGHT_REPORT_BINDING",
        )
        require(
            binding["artifacts"] == context["artifacts"]
            and binding["code"] == context["code_bindings"],
            "PREFLIGHT_CONTEXT_INPUT_BINDING",
        )
        require(
            sealed == binding["artifacts"]["eligibility_ledger"],
            "PREFLIGHT_SEALED_LEDGER_BINDING",
        )
        freeze = object_bytes(context["proposed_freeze1"])
        require(
            freeze["artifacts"]["historical_integrity_manifest"]["sha256"]
            == trust["procedure_sha256"],
            "PREFLIGHT_PROCEDURE_BINDING",
        )
        stage = "PREFLIGHT_COMPATIBILITY_MALFORMED"
        proof = verify_adoption(
            root,
            context["historical_manifest"],
            context["expected_historical_manifest_sha256"],
            context["generating_sources"],
            context["artifacts"]["population"],
            context["artifacts"]["eligibility_ledger"],
            context["code_bindings"]["selection_bundle"],
            context["proposed_freeze1"],
            trust["freeze1_sha256"],
            executing_sources=context["executing_sources"],
            input_binding_raw=binding_raw,
        )
        # Only the existing verifier's sanitized local codes can reach this branch.
        require(proof["code"] == "BINDINGS_VERIFIED_NOT_ADOPTED", proof["code"])
        require(
            proof["historical_provenance_verified"] is True
            and proof["proposed_freeze_compatible"] is True
            and proof["operational_adoption_performed"] is False,
            "PREFLIGHT_COMPATIBILITY_REQUIRED",
        )
        stage = "PREFLIGHT_REPLAY_MALFORMED"
        assessment = validate_preparation(
            root,
            binding_raw,
            report_raw,
            trust["inputs_sha256"],
            trust["freeze1_sha256"],
            verification_context=context,
        )
        require(
            assessment["verification_level"] == "EVIDENCE_REPLAYED",
            "PREFLIGHT_REPLAY_REQUIRED",
        )
        stage = "PREFLIGHT_AUTHORIZATION_MALFORMED"
        require(
            selection_phase_predicate(
                assessment,
                authorization_raw,
                trust["authorization_sha256"],
                phase,
                trust["ledger_seal_sha256"],
                trust["procedure_sha256"],
            ),
            "PREFLIGHT_AUTHORIZATION_BINDING",
        )
        result.update(
            status="TECHNICAL_PREFLIGHT_VERIFIED_NOT_AUTHORIZED",
            hashes={
                **{key: trust[key] for key in hashes},
                "ledger_sha256": sealed["sha256"],
                "current_verification_bundle_sha256": verification_bundle(
                    context["executing_sources"]
                )["sha256"],
            },
        )
    except ProtocolError as error:
        result["code"] = str(error)
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        LookupError,
        RecursionError,
        AttributeError,
        SyntaxError,
    ):
        result["code"] = stage
    return result
