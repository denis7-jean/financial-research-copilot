"""Typed technical evidence joins. No human-approval authentication or operations."""

from datetime import datetime

from experiments.reviewer_protocol_v2.common import canonical, require, sha_bytes
from experiments.reviewer_protocol_v2.control_serialization import (
    object_header,
    object_bytes,
    relative_path,
)
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
        explanatory_note="KEY_REQUIRED_NONEMPTY_IF_ABSTAINED_OR_CONCERN",
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


def evidence_v2(raw, name, keys):
    return evidence_header(raw, name, keys, 2)


def evidence_header(raw, name, keys, version):
    value = object_bytes(raw)
    exact_keys(value, ("schema", *keys))
    require(
        value["schema"] == "reviewer-protocol-v2-" + name + "-v" + str(version),
        "evidence_version",
    )
    return value


def source_record(value, read):
    nonempty(value["record_reference"])
    relative_path(value["record_path"])
    hex256(value["record_sha256"])
    origin = dict(path=value["record_path"], sha256=value["record_sha256"])
    raw = read(origin)
    require(
        type(raw) is bytes and sha_bytes(raw) == origin["sha256"], "source_record_hash"
    )
    return origin


def text_evidence(raw, kind, contract, read, algorithm=False):
    value = evidence_header(
        raw,
        "rule-algorithm-evidence" if algorithm else "rule-text-evidence",
        (
            "role",
            "record_reference",
            "record_path",
            "record_sha256",
            "contract_sha256",
            "text",
            "section_locator",
        ),
        2 if algorithm else 3,
    )
    require(
        value["role"] == kind
        and value["contract_sha256"] == sha_bytes(canonical(contract)),
        "normative_source_binding",
    )
    source_record(value, read)
    nonempty(value["text"])
    nonempty(value["section_locator"])
    return value


def specification(raw, role, read):
    value = evidence_v2(
        raw,
        "rule-specification",
        (
            "role",
            "contract",
            "source_evidence",
            "decision_evidence",
            "algorithm_evidence",
            "shared_origins",
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
    require(
        value["algorithm_evidence"] not in value["source_evidence"],
        "algorithm_evidence_distinct",
    )
    texts = [
        text_evidence(read(fb), role, value["contract"], read)
        for fb in value["source_evidence"]
    ]
    algorithm = text_evidence(
        read(value["algorithm_evidence"]), role, value["contract"], read, algorithm=True
    )
    origins = {}
    for item in [*texts, algorithm]:
        identity = (item["record_path"], item["record_reference"])
        digest = item["record_sha256"]
        require(
            digest not in origins or origins[digest] == identity,
            "evidence_origin_alias",
        )
        origins[digest] = identity
    shared = (
        [dict(path=algorithm["record_path"], sha256=algorithm["record_sha256"])]
        if any(item["record_sha256"] == algorithm["record_sha256"] for item in texts)
        else []
    )
    require(value["shared_origins"] == shared, "evidence_shared_origins")
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
        witness = evidence_v2(
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
                "normative_document_id",
                "historical_ledger_policy",
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
                "CURRENT_E01_METADATA_AND_E03C_LITERAL_CORRECTION"
                if role == "eligibility_specification"
                else "UNCHANGED_POLICY"
            )
            and witness["normative_document_id"]
            == "reviewer-protocol-v2-current-rules-v1"
            and witness["historical_ledger_policy"]
            == (
                "IDENTICAL_CORRECTED_ELIGIBILITY_SOURCE_ONLY"
                if role == "eligibility_specification"
                else "NO_NEW_LEDGER_POLICY"
            ),
            "RULE_APPLICABILITY_BINDING",
        )
        read(witness["current_source"])
        review = evidence_header(
            read(witness["semantic_review_evidence"]),
            "review-evidence",
            (
                "subject_sha256",
                "contract_sha256",
                "record_reference",
                "record_path",
                "record_sha256",
                "reviewer",
                "recorded_utc",
                "note",
                "shared_origin_reviews",
            ),
            3,
        )
        require(
            review["subject_sha256"] == roles[role]["sha256"], "RULE_REVIEW_SUBJECT"
        )
        require(
            review["contract_sha256"] == sha_bytes(canonical(spec["contract"])),
            "RULE_REVIEW_CONTRACT",
        )
        source_record(review, read)
        for key in ("record_reference", "reviewer", "note"):
            nonempty(review[key])
        utc(review["recorded_utc"])
        shared_reviews = review["shared_origin_reviews"]
        require(
            type(shared_reviews) is list
            and len(shared_reviews) == len(spec["shared_origins"]),
            "RULE_REVIEW_SHARED_ORIGINS",
        )
        for declaration, origin in zip(
            shared_reviews, spec["shared_origins"], strict=True
        ):
            exact_keys(
                declaration,
                (
                    "record_path",
                    "record_sha256",
                    "supports_both_roles",
                    "note",
                    "source_sections",
                    "algorithm_sections",
                ),
                "RULE_REVIEW_SHARED_SCHEMA",
            )
            require(
                declaration["record_path"] == origin["path"]
                and declaration["record_sha256"] == origin["sha256"]
                and declaration["supports_both_roles"] is True,
                "RULE_REVIEW_SHARED_ORIGINS",
            )
            nonempty(declaration["note"])
            for field, refs in (
                ("source_sections", spec["source_evidence"]),
                ("algorithm_sections", [spec["algorithm_evidence"]]),
            ):
                citations = [object_bytes(read(fb)) for fb in refs]
                expected = sorted(
                    {
                        c["section_locator"]
                        for c in citations
                        if c["record_sha256"] == origin["sha256"]
                    }
                )
                require(declaration[field] == expected, "RULE_REVIEW_SHARED_SECTIONS")
    # A declaration alone cannot clear the ledger evidence implications of D8.
    require(
        history["sources"]["eligibility.py"]
        == current["files"]["main/experiments/reviewer_protocol_v2/eligibility.py"],
        "E03C_LEDGER_RECONCILIATION_REQUIRED",
    )


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
            text_evidence(read(source), kind, value["contract"], read)


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
