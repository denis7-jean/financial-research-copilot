"""Read-only historical provenance/frozen-procedure checks; never adopts or seals."""

import ast

from experiments.reviewer_protocol_v2.common import (
    ProtocolError,
    canonical,
    require,
    sha_bytes,
)
from experiments.reviewer_protocol_v2.control_serialization import (
    object_bytes,
    object_header,
)
from experiments.reviewer_protocol_v2.selection import (
    exact_keys,
    file_binding,
    hex256,
    jsonl_records,
    selection_bundle,
)

GENERATING_FILES = (
    "__init__.py",
    "__main__.py",
    "analysis.py",
    "audit.py",
    "common.py",
    "constraints.py",
    "eligibility.py",
    "exposure.py",
    "fixtures.py",
    "input_hashes.json",
    "integrity.py",
    "known_inventory.py",
    "packet_validation.py",
    "selection.py",
    "similarity.py",
    "validation.py",
)
RECIPE = """def implementation_hash():
    folder = Path(__file__).parent
    files = {
        path.name: sha_bytes(path.read_bytes())
        for path in sorted(folder.iterdir())
        if path.suffix in {".py", ".json"}
    }
    return sha_bytes(canonical(files))
"""
PAYLOADS = (
    "inventory.json",
    "population_ledger.jsonl",
    "aggregate.json",
    "integrity.json",
)
FREEZE_ROLES = (
    "population",
    "exposure_inventory",
    "eligibility_specification",
    "exposure_specification",
    "selection_specification",
    "remaining_interfaces_specification",
    "eligibility_exposure_code_bundle",
    "selection_code_bundle",
    "synthetic_test_manifest",
    "grouping_similarity_specification",
    "historical_similarity_source",
    "runtime_dependency_lock",
    "historical_integrity_manifest",
    "definitive_heldout_exclusion_policy",
    "design_approval_evidence",
)
RECORDED_RUNTIME = dict(implementation="CPython", python="3.13.12", unicode="15.1.0")


def read_binding(root, binding):
    raw = file_binding(root, binding).read_bytes()
    require(sha_bytes(raw) == binding["sha256"], "input_hash_mismatch")
    return raw


def _literal(source, name):
    tree = ast.parse(source.decode("utf-8", errors="strict"))
    nodes = [
        n.value
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
    ]
    require(len(nodes) == 1, "GENERATING_INPUT_CONTRACT_MISSING")
    try:
        return ast.literal_eval(nodes[0])
    except (ValueError, TypeError):
        raise ProtocolError("GENERATING_INPUT_CONTRACT_INVALID") from None


def generating_bundle(sources):
    exact_keys(sources, GENERATING_FILES, "GENERATING_SOURCE_INCOMPLETE")
    require(all(type(v) is bytes for v in sources.values()), "GENERATING_SOURCE_TYPE")
    tree = ast.parse(sources["audit.py"].decode("utf-8", errors="strict"))
    functions = [
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "implementation_hash"
    ]
    require(
        len(functions) == 1
        and ast.dump(functions[0], include_attributes=False)
        == ast.dump(ast.parse(RECIPE).body[0], include_attributes=False),
        "GENERATING_HASH_RECIPE",
    )
    files = {name: sha_bytes(raw) for name, raw in sources.items()}
    return files, sha_bytes(canonical(files))


def _history(root, manifest_binding, expected_manifest_sha256, sources):
    hex256(expected_manifest_sha256)
    require(
        manifest_binding.get("sha256") == expected_manifest_sha256,
        "HISTORICAL_MANIFEST_TRUSTED_HASH",
    )
    raw = read_binding(root, manifest_binding)
    manifest = object_bytes(raw)
    exact_keys(
        manifest,
        (
            "artifact_type",
            "byte_contract",
            "files",
            "frozen",
            "implementation_sha256",
            "runtime",
            "schema",
            "self_hash_rule",
        ),
        "HISTORICAL_MANIFEST_SCHEMA",
    )
    require(
        manifest["schema"] == "offline_audit_manifest_v2"
        and manifest["artifact_type"] == "offline_unselected_audit"
        and manifest["frozen"] is False,
        "HISTORICAL_MANIFEST_SCHEMA",
    )
    require(
        manifest["byte_contract"]
        == "UTF-8; escaped Unicode; sorted keys; compact JSON; finite numbers; LF terminator"
        and manifest["self_hash_rule"]
        == "manifest excluded from files; receipt holds exact manifest-byte hash",
        "HISTORICAL_BYTE_RECIPE",
    )
    exact_keys(manifest["files"], PAYLOADS, "HISTORICAL_PAYLOAD_SET")
    parent = manifest_binding["path"].rsplit("/", 1)[0]
    payloads = {
        name: read_binding(root, dict(path=parent + "/" + name, sha256=digest))
        for name, digest in manifest["files"].items()
    }
    files, digest = generating_bundle(sources)
    require(
        manifest["implementation_sha256"] == digest,
        "GENERATING_IMPLEMENTATION_MISMATCH",
    )
    require(
        canonical(manifest["runtime"]) == canonical(RECORDED_RUNTIME),
        "HISTORICAL_RUNTIME",
    )
    integrity = object_bytes(payloads["integrity.json"])
    exact_keys(
        integrity,
        ("protected_files", "frozen_bindings", "pins_sha256", "files", "verified"),
        "HISTORICAL_INTEGRITY_SCHEMA",
    )
    # Original pin bytes need not have the later canonical layout.
    from experiments.reviewer_protocol_v2.common import decode

    pins = decode(sources["input_hashes.json"].decode("utf-8", errors="strict"))
    require(
        type(pins) is dict
        and integrity["files"] == pins
        and integrity["pins_sha256"] == files["input_hashes.json"]
        and integrity["verified"] is True
        and type(integrity["protected_files"]) is int
        and integrity["protected_files"] == len(pins)
        and type(integrity["frozen_bindings"]) is int
        and integrity["frozen_bindings"] >= 0,
        "HISTORICAL_INPUT_PINS",
    )
    inputs = dict(pins)
    design = _literal(sources["integrity.py"], "DESIGN_HASHES")
    exact_keys(
        design,
        ("original-design-evidence.md", "revised-design-evidence.md"),
        "GENERATING_DESIGN_INPUTS",
    )
    extra = dict(design)
    extra["document-quotes.json"] = _literal(
        sources["known_inventory.py"], "DOC_QUOTES_SHA256"
    )
    extra["recovered-references.json"] = _literal(
        sources["integrity.py"], "RECOVERY_SHA256"
    )
    for name, value in extra.items():
        path = "heldout-external/reviewer-protocol-v2-offline/" + name
        require(
            path not in inputs or inputs[path] == value, "GENERATING_INPUT_CONFLICT"
        )
        inputs[path] = value
    for path, value in inputs.items():
        read_binding(root, dict(path=path, sha256=value))
    inventory = object_bytes(payloads["inventory.json"])
    require(
        type(inventory.get("supporting_files")) is dict,
        "INVENTORY_SOURCE_BINDINGS_MISSING",
    )
    for path, value in inventory["supporting_files"].items():
        require(path in inputs and inputs[path] == value, "INVENTORY_SOURCE_BINDING")
    for e in inventory.get("evidence", []):
        require(
            type(e) is dict
            and e.get("source") in inventory["supporting_files"]
            and e.get("source_sha256") == inventory["supporting_files"][e["source"]],
            "INVENTORY_EVIDENCE_SOURCE",
        )
    ledger = jsonl_records(payloads["population_ledger.jsonl"])
    require(
        b"".join(canonical(r) for r in ledger) == payloads["population_ledger.jsonl"],
        "HISTORICAL_LEDGER_CANONICAL",
    )
    require(
        bool(ledger) and all(r.get("implementation_sha256") == digest for r in ledger),
        "LEDGER_IMPLEMENTATION_BINDING",
    )
    aggregate = object_bytes(payloads["aggregate.json"])
    require(
        aggregate.get("implementation_sha256") == digest
        and aggregate.get("runtime") == RECORDED_RUNTIME,
        "AGGREGATE_GENERATING_BINDING",
    )
    return dict(
        manifest=manifest,
        payloads=payloads,
        sources=files,
        digest=digest,
        inputs=inputs,
        integrity=integrity,
    )


def _freeze(root, raw, expected_sha256, history, population_binding):
    hex256(expected_sha256)
    require(sha_bytes(raw) == expected_sha256, "FREEZE_TRUSTED_HASH")
    freeze = object_header(raw, "freeze-manifest", ("phase", "artifacts"))
    require(freeze["phase"] == "FREEZE_1", "FREEZE_PHASE")
    exact_keys(freeze["artifacts"], FREEZE_ROLES, "FREEZE_ROLE_SET")
    values = {role: read_binding(root, fb) for role, fb in freeze["artifacts"].items()}
    roles = freeze["artifacts"]
    require(
        roles["population"] == population_binding
        and population_binding["path"] in history["inputs"]
        and population_binding["sha256"]
        == history["inputs"][population_binding["path"]],
        "FREEZE_POPULATION_BINDING",
    )
    require(
        sha_bytes(values["exposure_inventory"])
        == history["manifest"]["files"]["inventory.json"],
        "FREEZE_INVENTORY_BINDING",
    )
    # The accepted role envelope does not specify the historical rule/input/runtime
    # encoding. Do not equate source files with specification or lock artifacts.
    require(False, "FREEZE_ADOPTION_ENCODING_UNSPECIFIED")


def verify_adoption(
    root,
    manifest_binding,
    expected_manifest_sha256,
    generating_sources,
    population_binding,
    ledger_binding,
    selection_binding,
    proposed_freeze1=None,
    expected_freeze1_sha256=None,
):
    """Ephemeral technical result, not an adoption/seal artifact or owner approval."""
    result = dict(
        historical_provenance_verified=False,
        proposed_freeze_compatible=None,
        operational_adoption_performed=False,
        code=None,
        hashes={},
    )
    try:
        history = _history(
            root, manifest_binding, expected_manifest_sha256, generating_sources
        )
        require(
            read_binding(root, ledger_binding)
            == history["payloads"]["population_ledger.jsonl"],
            "ORIGINAL_LEDGER_CHANGED",
        )
        require(
            population_binding["path"] in history["inputs"]
            and population_binding["sha256"]
            == history["inputs"][population_binding["path"]],
            "ORIGINAL_POPULATION_BINDING",
        )
        read_binding(root, population_binding)
        result.update(
            historical_provenance_verified=True,
            hashes=dict(
                manifest=expected_manifest_sha256,
                implementation=history["digest"],
                ledger=ledger_binding["sha256"],
            ),
        )
        require(selection_binding == selection_bundle(), "CURRENT_SELECTION_BINDING")
        require(
            history["digest"] != selection_binding["sha256"],
            "HISTORICAL_CURRENT_DIGEST_CONFUSION",
        )
        for path, digest in selection_binding["files"].items():
            read_binding(root, dict(path=path, sha256=digest))
        if proposed_freeze1 is not None:
            result["proposed_freeze_compatible"] = False
            _freeze(
                root,
                proposed_freeze1,
                expected_freeze1_sha256,
                history,
                population_binding,
            )
            result["proposed_freeze_compatible"] = True
        else:
            require(expected_freeze1_sha256 is None, "FREEZE_EVIDENCE_MISSING")
        result["code"] = "BINDINGS_VERIFIED_NOT_ADOPTED"
    except ProtocolError as error:
        # Exceptions originate only in sanitized local checks, never echo arbitrary messages.
        result["code"] = str(error)
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        SyntaxError,
    ):
        result["code"] = "MALFORMED_OR_MISSING_EVIDENCE"
    return result
