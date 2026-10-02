"""Typed technical evidence joins. No human-approval authentication or operations."""

from datetime import datetime

from experiments.reviewer_protocol_v2.common import canonical, require, sha_bytes
from experiments.reviewer_protocol_v2.control_serialization import object_header
from experiments.reviewer_protocol_v2.eligibility import PATTERNS
from experiments.reviewer_protocol_v2.selection import (
    SOURCE_ROOT,
    STRATUM_ENTRIES,
    exact_keys,
    hex256,
)

INTERFACE_CONTRACTS = {
    "control": dict(
        anchors=15,
        diagnostics=6,
        control_seed=20261003,
        id_shape="x_SHA256",
        diagnostics_scored=False,
    ),
    "trial_presentation": dict(
        external=24,
        anchors=15,
        diagnostics=6,
        reviewers=3,
        requests=135,
        retries=0,
        presentation_seed=20261002,
        membership="IDENTICAL_THREE_PERMUTATIONS",
        visible_fields=["item_id", "question"],
    ),
    "owner_audit": dict(
        external=24,
        raw_annotations="IMMUTABLE",
        abstention="INDEPENDENT_BOOLEAN",
        context_concern="INDEPENDENT_BOOLEAN",
        abstained_label=None,
        abstained_components=[],
        abstained_certainty=None,
        explanatory_note="REQUIRED",
    ),
    "analysis_population": dict(
        pair="BOTH_REVIEWER_VALID",
        fleiss="ALL_THREE_REVIEWER_VALID",
        owner="VALID_REVIEWER_AND_OWNER_LABEL_NO_ABSTENTION_NO_CONTEXT_CONCERN",
        external_only=True,
        reviewer_owner_filter="IGNORED",
        exclusions="OVERLAPPING",
        empty_agreement="UNDEFINED",
        planned_denominator=24,
    ),
}
INTERFACE_CONTRACTS["control"]["procedures"] = [
    "control-catalog",
    "control-references",
    "control-map",
    "control-keys",
    "control-packet",
]
INTERFACE_CONTRACTS["trial_presentation"]["procedures"] = [
    "trial-membership",
    "trial-packet",
    "presentations",
    "presentation-manifest",
    "request-schedule",
]
INTERFACE_CONTRACTS["owner_audit"]["procedures"] = [
    "owner-audit",
    "owner-audit-seal",
    "packet-rubric-id-bindings",
]
INTERFACE_CONTRACTS["analysis_population"]["procedures"] = [
    "reviewer-pair-cohen",
    "reviewer-fleiss",
    "owner-reviewer-cohen",
    "planned-coverage",
    "overlapping-exclusions",
]

TEST_PATHS = tuple(
    "main/tests/test_reviewer_v2_" + name + ".py"
    for name in (
        "eligibility",
        "exposure",
        "regression",
        "safety",
        "validation_analysis",
        "packet_serialization",
        "selection",
        "controls",
        "trial_interfaces",
        "owner_audit",
        "preparation",
        "adoption_encoding",
        "review_remediation",
    )
)


def nonempty(value):
    require(type(value) is str and bool(value.strip()), "evidence_text")
    value.encode("utf-8", errors="strict")


def utc(value):
    nonempty(value)
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value, "evidence_utc")


def current_decision(raw):
    value = object_header(
        raw,
        "current-owner-decisions",
        (
            "record_reference",
            "record_sha256",
            "historical_amendment",
            "decisions",
            "approval_authenticated",
        ),
    )
    nonempty(value["record_reference"])
    hex256(value["record_sha256"])
    require(
        value["historical_amendment"] is False
        and value["approval_authenticated"] is False
        and value["decisions"]
        == dict(
            E01="METADATA_ONLY_NO_DISPOSITION_CHANGE",
            rule_evidence="HISTORICAL_AND_CURRENT_SEPARATE",
            runtime="EXACT_NINE_FIELD_BINDING",
        ),
        "current_owner_decision",
    )
    return value


def rule_contract(role):
    """Consistency target, not an authoritative source or a specification writer."""
    if role == "eligibility_specification":
        return dict(
            normalization="NFKC_CASEFOLD_WHITESPACE_STRIP",
            rule_dispositions=dict(
                E01="METADATA_ONLY",
                E02="DEPENDENCE_EXCLUDED",
                E03="DEPENDENCE_EXCLUDED",
                E04="DEPENDENCE_EXCLUDED",
                E05="DIAGNOSTIC_ONLY",
                E06="DIAGNOSTIC_ONLY",
                E07="INPUT_INVALID",
            ),
            precedence=[
                "INPUT_INVALID",
                "DEPENDENCE_EXCLUDED",
                "DIAGNOSTIC_ONLY",
                "SCREEN_PASS",
            ],
            finite_patterns={
                name: dict(pattern=p.pattern, flags=p.flags)
                for name, p in PATTERNS.items()
            },
        )
    return dict(
        direct_pair_only=True,
        transitive=False,
        threshold_hex=(0.90).hex(),
        native_group=True,
        comparison=">=" if role == "exposure_specification" else "<",
    )


def text_evidence(raw, kind, contract):
    value = object_header(
        raw,
        "rule-text-evidence",
        ("role", "record_reference", "contract_sha256", "text"),
    )
    require(
        value["role"] == kind
        and value["contract_sha256"] == sha_bytes(canonical(contract)),
        "normative_source_binding",
    )
    nonempty(value["record_reference"])
    nonempty(value["text"])


def specification(raw, role, read):
    value = object_header(
        raw,
        "rule-specification",
        (
            "role",
            "contract",
            "source_evidence",
            "decision_evidence",
            "algorithm_evidence",
        ),
    )
    require(
        value["role"] == role
        and canonical(value["contract"]) == canonical(rule_contract(role)),
        "normative_rule_contract",
    )
    require(
        type(value["source_evidence"]) is list and bool(value["source_evidence"]),
        "normative_source_missing",
    )
    for fb in [*value["source_evidence"], value["algorithm_evidence"]]:
        text_evidence(read(fb), role, value["contract"])
    current_decision(read(value["decision_evidence"]))
    return value


def rule_bindings(procedure, roles, history, current, read, rule_roles):
    exact_keys(procedure["rules"], rule_roles, "RULE_EVIDENCE_SET")
    for role, name in rule_roles.items():
        record = procedure["rules"][role]
        exact_keys(
            record,
            ("original_evidence", "specification", "relationship_evidence"),
            "RULE_EVIDENCE_SCHEMA",
        )
        evidence = record["original_evidence"]
        require(type(evidence) is list and bool(evidence), "RULE_ORIGINAL_EVIDENCE_SET")
        for fb in evidence:
            read(fb)
            require(
                fb["path"] in history["inputs"]
                and fb["sha256"] == history["inputs"][fb["path"]],
                "RULE_ORIGINAL_EVIDENCE_BINDING",
            )
        require(record["specification"] == roles[role], "RULE_SPECIFICATION_BINDING")
        spec = specification(read(record["specification"]), role, read)
        witness = object_header(
            read(record["relationship_evidence"]),
            "rule-applicability",
            (
                "role",
                "historical_implementation_sha256",
                "historical_source",
                "current_source",
                "original_evidence",
                "specification",
                "decision_evidence",
                "semantic_review_evidence",
                "reconciliation",
            ),
        )
        current_path = "main/experiments/reviewer_protocol_v2/" + name
        require(
            witness["role"] == role
            and witness["historical_implementation_sha256"] == history["digest"]
            and witness["historical_source"]
            == dict(filename=name, sha256=history["sources"][name])
            and witness["current_source"]
            == dict(path=current_path, sha256=current["files"][current_path])
            and witness["original_evidence"] == evidence
            and witness["specification"] == roles[role]
            and witness["decision_evidence"] == spec["decision_evidence"]
            and witness["reconciliation"]
            == (
                "CURRENT_E01_METADATA_CLARIFICATION"
                if role == "eligibility_specification"
                else "UNCHANGED_POLICY"
            ),
            "RULE_APPLICABILITY_BINDING",
        )
        read(witness["current_source"])
        review = object_header(
            read(witness["semantic_review_evidence"]),
            "review-evidence",
            ("subject_sha256", "record_reference", "reviewer", "recorded_utc", "note"),
        )
        require(
            review["subject_sha256"] == roles[role]["sha256"], "RULE_REVIEW_SUBJECT"
        )
        for key in ("record_reference", "reviewer", "note"):
            nonempty(review[key])
        utc(review["recorded_utc"])


def interface_specifications(refs, read):
    exact_keys(refs, INTERFACE_CONTRACTS, "interface_specification_set")
    for kind, fb in refs.items():
        value = object_header(
            read(fb), "interface-specification", ("kind", "contract", "source_evidence")
        )
        require(
            value["kind"] == kind
            and canonical(value["contract"]) == canonical(INTERFACE_CONTRACTS[kind]),
            "interface_contract",
        )
        require(
            type(value["source_evidence"]) is list and bool(value["source_evidence"]),
            "interface_source_missing",
        )
        for source in value["source_evidence"]:
            text_evidence(read(source), kind, value["contract"])


def selection_specification(raw):
    value = object_header(
        raw,
        "selection-specification",
        (
            "seed",
            "strata",
            "rank_domain",
            "external_id_domain",
            "tie_breakers",
            "threshold_hex",
            "comparison",
            "shortfall",
        ),
    )
    require(
        canonical(value)
        == canonical(
            dict(
                schema=value["schema"],
                seed=20261001,
                strata=list(STRATUM_ENTRIES),
                rank_domain="reviewer-protocol-v2-rank-v1",
                external_id_domain="reviewer-protocol-v2-external-id-v1",
                tie_breakers=["digest", "candidate_id_utf8", "source_utf8"],
                threshold_hex=(0.9).hex(),
                comparison="<",
                shortfall="NO_PACKET",
            )
        ),
        "selection_specification_contract",
    )


def freeze_roles(roles, values, history, current, read):
    tests = object_header(
        values["synthetic_test_manifest"],
        "synthetic-test-manifest",
        ("sources", "tests", "code_bundle_sha256"),
    )
    require(
        tests["sources"] == current["files"]
        and tests["code_bundle_sha256"] == current["sha256"],
        "test_source_coverage",
    )
    exact_keys(tests["tests"], TEST_PATHS, "test_coverage_set")
    for path, digest in tests["tests"].items():
        raw = read(dict(path=path, sha256=digest))
        require(raw == (SOURCE_ROOT / path).read_bytes(), "executing_test_binding")
    selection_specification(values["selection_specification"])
    policy = object_header(
        values["definitive_heldout_exclusion_policy"],
        "definitive-exclusion-policy",
        (
            "population",
            "ledger",
            "inventory",
            "context_groups_sha256",
            "direct_pair_only",
            "transitive",
            "threshold_hex",
            "native_group",
            "eligible_disposition",
            "selection_comparison",
            "decision_evidence",
        ),
    )
    from experiments.reviewer_protocol_v2.selection import jsonl_records

    rows = jsonl_records(history["payloads"]["population_ledger.jsonl"])
    parent = history["manifest_binding"]["path"].rsplit("/", 1)[0]
    require(
        policy["population"] == roles["population"]
        and policy["inventory"] == roles["exposure_inventory"]
        and policy["ledger"]
        == dict(
            path=parent + "/population_ledger.jsonl",
            sha256=history["manifest"]["files"]["population_ledger.jsonl"],
        )
        and policy["context_groups_sha256"]
        == sha_bytes(
            canonical(
                [
                    {k: row[k] for k in ("source", "context_group", "cand_id")}
                    for row in rows
                ]
            )
        )
        and policy["direct_pair_only"] is True
        and policy["transitive"] is False
        and policy["native_group"] is True
        and policy["threshold_hex"] == (0.9).hex()
        and policy["eligible_disposition"] == "SCREEN_PASS"
        and policy["selection_comparison"] == "<",
        "exclusion_policy_binding",
    )
    current_decision(read(policy["decision_evidence"]))
    declaration = object_header(
        values["design_approval_evidence"],
        "design-approval-evidence",
        ("actor", "recorded_utc", "record_reference", "authority_evidence", "subjects"),
    )
    for key in ("actor", "record_reference"):
        nonempty(declaration[key])
    utc(declaration["recorded_utc"])
    current_decision(read(declaration["authority_evidence"]))
    require(
        declaration["subjects"]
        == {
            role: fb["sha256"]
            for role, fb in roles.items()
            if role not in {"design_approval_evidence", "historical_integrity_manifest"}
        },
        "design_evidence_subjects",
    )
