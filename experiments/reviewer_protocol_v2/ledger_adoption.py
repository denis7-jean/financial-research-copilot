"""Read-only historical provenance/frozen-procedure checks; never adopts or seals."""

import ast
import sys

from experiments.reviewer_protocol_v2.procedure_evidence import (
    rule_bindings,
    interface_specifications,
    freeze_roles,
)

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
    read_file_binding,
    hex256,
    jsonl_records,
    selection_bundle,
    prepare_inputs,
    runtime_binding,
    bound_path,
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
HASH_RECIPE = "SHA256_CANONICAL_FILENAME_HASH_MAP_LF_V1"
RULE_ROLES = {
    "eligibility_specification": "eligibility.py",
    "exposure_specification": "exposure.py",
    "grouping_similarity_specification": "similarity.py",
}
EXTRA_INPUTS = tuple(
    "heldout-external/reviewer-protocol-v2-offline/" + name
    for name in (
        "original-design-evidence.md",
        "revised-design-evidence.md",
        "document-quotes.json",
        "recovered-references.json",
    )
)


def read_binding(root, binding):
    return read_file_binding(root, binding)


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
        manifest_binding=dict(manifest_binding),
        payloads=payloads,
        sources=files,
        digest=digest,
        inputs=inputs,
        integrity=integrity,
    )


def dependency_modules(sources):
    """Static checks on reviewed hash-bound source, not a Python sandbox."""
    declared = set()
    packages = set()
    for path in sources:
        if path.startswith("main/experiments/"):
            module = path.removeprefix("main/").removesuffix(".py").replace("/", ".")
            if module.endswith(".__init__"):
                module = module.removesuffix(".__init__")
                packages.add(module)
            declared.add(module)
    modules = set()
    allowed_stdlib = {
        "ast",
        "collections",
        "hashlib",
        "json",
        "math",
        "pathlib",
        "platform",
        "re",
        "sys",
        "unicodedata",
        "datetime",
        "itertools",
    }
    access = {
        "ast": {
            "Assign",
            "Attribute",
            "Call",
            "FunctionDef",
            "Import",
            "ImportFrom",
            "Name",
            "dump",
            "literal_eval",
            "parse",
            "walk",
            "iter_child_nodes",
        },
        "collections": {"Counter", "defaultdict"},
        "datetime": {"datetime"},
        "hashlib": {"sha256"},
        "itertools": {"combinations"},
        "json": {"JSONDecodeError", "dumps", "loads"},
        "math": {"sqrt", "isfinite"},
        "pathlib": {"Path"},
        "platform": {"python_implementation", "python_version", "machine", "platform"},
        "re": {"compile", "escape", "fullmatch", "sub"},
        "sys": {"byteorder", "float_info", "stdlib_module_names", "version_info"},
        "unicodedata": {"normalize", "unidata_version"},
    }
    prohibited = {
        "__import__",
        "exec",
        "eval",
        "compile",
        "getattr",
        "__builtins__",
        "vars",
        "globals",
        "locals",
    }
    for path, raw in sources.items():
        tree = ast.parse(raw.decode("utf-8", errors="strict"))
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in allowed_stdlib:
                        aliases[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module in allowed_stdlib:
                require(
                    all(alias.name in access[node.module] for alias in node.names),
                    "RUNTIME_STDLIB_ACCESS",
                )
        for node in ast.walk(tree):
            require(
                not isinstance(node, ast.Name) or node.id not in prohibited,
                "RUNTIME_DYNAMIC_LOADING",
            )
            reviewed_re_compile = (
                isinstance(node, ast.Attribute)
                and node.attr == "compile"
                and isinstance(node.value, ast.Name)
                and aliases.get(node.value.id) == "re"
            )
            require(
                not isinstance(node, ast.Attribute)
                or reviewed_re_compile
                or node.attr
                not in {
                    "__import__",
                    "import_module",
                    "load_module",
                    "exec_module",
                    "__dict__",
                    "exec",
                    "eval",
                    "compile",
                    "vars",
                    "globals",
                    "locals",
                    "__globals__",
                    "__builtins__",
                },
                "RUNTIME_DYNAMIC_LOADING",
            )
            if isinstance(node, ast.Name) and node.id in aliases:
                require(
                    isinstance(parents.get(node), ast.Attribute), "RUNTIME_MODULE_ALIAS"
                )
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                module = aliases.get(node.value.id)
                if module:
                    allowed = node.attr in access[module]
                    if module == "sys" and node.attr == "modules":
                        member = parents.get(node)
                        call = parents.get(member)
                        assignment = parents.get(call)
                        ancestor = assignment
                        while ancestor is not None and not isinstance(
                            ancestor, ast.FunctionDef
                        ):
                            ancestor = parents.get(ancestor)
                        allowed = (
                            path
                            == "main/experiments/reviewer_protocol_v2/production_preparation.py"
                            and node.value.id == "sys"
                            and isinstance(member, ast.Attribute)
                            and member.attr == "get"
                            and isinstance(call, ast.Call)
                            and call.func is member
                            and len(call.args) == 1
                            and isinstance(call.args[0], ast.Name)
                            and call.args[0].id == "module_name"
                            and not call.keywords
                            and isinstance(assignment, ast.Assign)
                            and assignment.value is call
                            and len(assignment.targets) == 1
                            and isinstance(assignment.targets[0], ast.Name)
                            and assignment.targets[0].id == "module"
                            and ancestor is not None
                            and ancestor.name == "_executing_sources"
                        )
                    require(allowed, "RUNTIME_STDLIB_ACCESS")
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                require(node.level == 0 and node.module, "RUNTIME_DEPENDENCY_IMPORT")
                names = [node.module]
                if node.module in packages:
                    names += [node.module + "." + alias.name for alias in node.names]
            for name in names:
                root = name.split(".")[0]
                if root == "experiments":
                    require(name in declared, "RUNTIME_REPOSITORY_CLOSURE")
                else:
                    require(
                        root in sys.stdlib_module_names, "RUNTIME_DEPENDENCY_NONSTDLIB"
                    )
                    require(root in allowed_stdlib, "RUNTIME_UNSUPPORTED_LOADING")
                    modules.add(root)
    return sorted(modules)


def _generating(root, raw, history, supplied):
    value = object_header(
        raw,
        "historical-generating-bundle",
        ("recipe", "sources", "implementation_sha256"),
    )
    require(
        value["recipe"] == HASH_RECIPE
        and value["implementation_sha256"] == history["digest"],
        "FREEZE_GENERATING_RECIPE_DIGEST",
    )
    exact_keys(value["sources"], GENERATING_FILES, "FREEZE_GENERATING_SOURCE_SET")
    paths = set()
    for name, fb in value["sources"].items():
        require(
            read_binding(root, fb) == supplied[name]
            and fb["sha256"] == history["sources"][name],
            "FREEZE_GENERATING_SOURCE_BYTES",
        )
        path = bound_path(root, fb["path"])
        require(
            path.name == name and path not in paths, "FREEZE_GENERATING_SOURCE_PATH"
        )
        paths.add(path)
    return value


def _v2_header(raw, name, keys):
    value = object_bytes(raw)
    exact_keys(value, ("schema", *keys))
    require(
        value["schema"] == "reviewer-protocol-v2-" + name + "-v2",
        "adoption_encoding_version",
    )
    return value


def _freeze(
    root,
    raw,
    expected_sha256,
    history,
    population_binding,
    ledger_binding,
    selection_binding,
    generating_sources,
    executing_sources,
    input_binding_raw,
):
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
    procedure = _v2_header(
        values["historical_integrity_manifest"],
        "historical-adoption",
        (
            "audit",
            "generating_bundle",
            "recorded_runtime",
            "pin_map",
            "additional_inputs",
            "input_closure",
            "input_closure_sha256",
            "rules",
            "proposed_runtime_dependency_lock",
            "current_bindings",
            "selection_inputs",
        ),
    )
    exact_keys(procedure["audit"], ("manifest", "payloads"), "ADOPTION_AUDIT_SCHEMA")
    parent = history["manifest_binding"]["path"].rsplit("/", 1)[0]
    payloads = {
        name: dict(path=parent + "/" + name, sha256=history["manifest"]["files"][name])
        for name in PAYLOADS
    }
    require(
        procedure["audit"]["manifest"] == history["manifest_binding"]
        and procedure["audit"]["payloads"] == payloads,
        "ADOPTION_ORIGINAL_AUDIT_BINDING",
    )
    require(
        procedure["generating_bundle"] == roles["eligibility_exposure_code_bundle"],
        "ADOPTION_GENERATING_ROLE",
    )
    generating = _generating(
        root, values["eligibility_exposure_code_bundle"], history, generating_sources
    )
    require(
        procedure["pin_map"] == generating["sources"]["input_hashes.json"],
        "ADOPTION_PIN_MAP_BINDING",
    )
    require(
        procedure["additional_inputs"]
        == {path: history["inputs"][path] for path in EXTRA_INPUTS}
        and procedure["input_closure"] == history["inputs"]
        and procedure["input_closure_sha256"]
        == sha_bytes(canonical(history["inputs"])),
        "ADOPTION_INPUT_CLOSURE",
    )
    require(
        canonical(procedure["recorded_runtime"]) == canonical(RECORDED_RUNTIME),
        "ADOPTION_RECORDED_RUNTIME",
    )
    # Import lazily to preserve the existing acyclic import-time dependency closure.
    from experiments.reviewer_protocol_v2.production_preparation import (
        _executing_sources,
    )

    require(executing_sources is not None, "CURRENT_VERIFICATION_EVIDENCE_MISSING")
    current = _executing_sources(root, executing_sources)
    rule_bindings(
        procedure,
        roles,
        history,
        current,
        lambda fb: read_binding(root, fb),
        RULE_ROLES,
    )
    exact_keys(
        procedure["current_bindings"],
        ("selection_bundle", "remaining_interfaces"),
        "ADOPTION_CURRENT_SCHEMA",
    )
    require(
        procedure["current_bindings"]
        == dict(
            selection_bundle=roles["selection_code_bundle"],
            remaining_interfaces=roles["remaining_interfaces_specification"],
        ),
        "ADOPTION_CURRENT_ROLE_BINDING",
    )
    require(
        values["selection_code_bundle"] == canonical(selection_binding),
        "ADOPTION_CURRENT_SELECTION_BINDING",
    )
    interface = _v2_header(
        values["remaining_interfaces_specification"],
        "adoption-interface-binding",
        ("specifications", "verification_bundle"),
    )
    require(
        interface["verification_bundle"] == current
        and current["sha256"] != history["digest"],
        "ADOPTION_CURRENT_VERIFICATION_BINDING",
    )
    interface_specifications(
        interface["specifications"], lambda fb: read_binding(root, fb)
    )
    freeze_roles(roles, values, history, current, lambda fb: read_binding(root, fb))
    require(
        procedure["proposed_runtime_dependency_lock"]
        == roles["runtime_dependency_lock"],
        "ADOPTION_RUNTIME_ROLE_BINDING",
    )
    lock = object_header(
        values["runtime_dependency_lock"],
        "adoption-runtime-lock",
        ("scope", "runtime", "stdlib_modules", "third_party_distributions"),
    )
    require(
        lock["scope"] == "OFFLINE_PREPARATION_SELECTION"
        and canonical(lock["runtime"]) == canonical(runtime_binding()),
        "ADOPTION_PROPOSED_RUNTIME",
    )
    require(
        lock["stdlib_modules"] == dependency_modules(executing_sources)
        and type(lock["third_party_distributions"]) is list
        and lock["third_party_distributions"] == [],
        "ADOPTION_DEPENDENCY_BINDING",
    )
    inputs_raw = read_binding(root, procedure["selection_inputs"])
    if input_binding_raw is not None:
        require(inputs_raw == input_binding_raw, "ADOPTION_PREPARATION_INPUT_BINDING")
    inputs = object_bytes(inputs_raw)
    rows = prepare_inputs(root, inputs, procedure["selection_inputs"]["sha256"])
    from experiments.reviewer_protocol_v2.exposure import validate_inventory

    inventory = object_bytes(values["exposure_inventory"])
    validate_inventory(inventory, jsonl_records(read_binding(root, population_binding)))
    direct = {item["cand_id"] for item in inventory["pilot_items"]}
    require(
        all(row["exposure"]["direct"] == (row["cand_id"] in direct) for row in rows),
        "ADOPTION_INVENTORY_LEDGER_FLAGS",
    )
    require(
        inputs["artifacts"]["population"] == roles["population"]
        and inputs["artifacts"]["exposure_inventory"] == roles["exposure_inventory"]
        and inputs["artifacts"]["selection_specification"]
        == roles["selection_specification"]
        and inputs["artifacts"]["eligibility_ledger"]
        == ledger_binding
        == payloads["population_ledger.jsonl"]
        and inputs["code"]["ledger_audit_implementation_sha256"] == history["digest"]
        and inputs["code"]["selection_bundle"] == selection_binding
        and inputs["code"]["historical_similarity_source"]
        == roles["historical_similarity_source"]
        and canonical(inputs["runtime"]) == canonical(lock["runtime"]),
        "ADOPTION_INPUT_ROLE_BINDING",
    )


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
    executing_sources=None,
    input_binding_raw=None,
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
        if proposed_freeze1 is not None:
            result["proposed_freeze_compatible"] = False
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
                ledger_binding,
                selection_binding,
                generating_sources,
                executing_sources,
                input_binding_raw,
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
        LookupError,
        RecursionError,
        AttributeError,
        SyntaxError,
    ):
        result["code"] = "MALFORMED_OR_MISSING_EVIDENCE"
    return result
