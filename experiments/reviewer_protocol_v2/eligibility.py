"""Accepted finite E01–E07 catalog, with independent normalized evidence spans."""

import re
import unicodedata
from experiments.reviewer_protocol_v2.common import (
    DuplicateKeys,
    ProtocolError,
    decode,
    question_hash,
    require,
)

FIELDS = (
    "cand_id",
    "question",
    "source",
    "sampling_stratum",
    "source_revision",
    "context_group",
)
STRATA = (
    ("tatqa", "T1_qa"),
    ("finqa", "T1_qa"),
    ("finlfqa", "num"),
    ("finlfqa", "interp"),
    ("finlfqa", "other"),
    ("finlfqa", "mixed"),
)
QUOTAS = dict(zip(STRATA, (4, 4, 4, 6, 4, 2)))


def normalize(question):
    return re.sub(
        r"\s+", " ", unicodedata.normalize("NFKC", question).casefold()
    ).strip()


def alternatives(words):
    literals = words.split() if isinstance(words, str) else words
    return (
        "(?:"
        + "|".join(
            re.escape(x) for x in sorted(set(literals), key=lambda x: (-len(x), x))
        )
        + ")"
    )


def bounded(pattern):
    return r"(?<!\w)" + pattern + r"(?!\w)"


A = alternatives("financial annual quarterly consolidated summary detailed")
M = alternatives(
    "table tables chart charts figure figures graph graphs diagram diagrams document documents report reports passage passages excerpt excerpts statement statements data information result results value values"
)
R = alternatives(
    "this that these those following above below attached provided shown given"
)
P = alternatives("above below following preceding")
T = alternatives("attached provided")
V = alternatives("shown reported presented listed indicated displayed")
L = alternatives("above below")
D = alternatives("directly immediately")
AM = "(?: " + A + "){0,2} " + M
PATTERNS = {
    "E01": re.compile(
        bounded(
            alternatives(
                "table tables chart charts graph graphs diagram diagrams screenshot screenshots image images"
            )
        )
    ),
    "E02": re.compile(bounded(R + AM)),
    "E03a_pre": re.compile(bounded(P + AM)),
    "E03a_post": re.compile(bounded(M + " " + L)),
    "E03b_location": re.compile(bounded(V + "(?: " + D + ")? " + L)),
    "E03b_material": re.compile(
        bounded(
            V
            + " in (?:the )?"
            + alternatives("above below following preceding attached provided")
            + AM
        )
    ),
    "E03c": re.compile(
        bounded(alternatives(("in", "from", "according to")) + " (?:the )?" + T + AM)
    ),
    "E04": re.compile(
        bounded(
            alternatives("previous preceding earlier last")
            + " "
            + alternatives(
                "question questions answer answers response responses discussion discussions"
            )
        )
    ),
}
N = r"(?:0|[1-9][0-9]*)(?![0-9]|[.,][0-9])"
LETTER = r"[a-z]"
COLUMN = r"[a-z]{1,3}"
ADDRESS = COLUMN + N


def wrappers(identifier):
    return "(?:" + identifier + "|# ?" + identifier + r"|\(" + identifier + r"\))"


for subrule, nouns, identifier in (
    ("d", "row rows", "(?:" + N + "|" + LETTER + ")"),
    ("e", "column columns", "(?:" + N + "|" + COLUMN + ")"),
    ("f", "cell cells", "(?:" + ADDRESS + "|" + N + "|" + LETTER + ")"),
    (
        "g",
        "table tables chart charts graph graphs diagram diagrams figure figures image images screenshot screenshots",
        "(?:" + N + "|" + LETTER + ")",
    ),
):
    PATTERNS["E03" + subrule] = re.compile(
        bounded(alternatives(nouns) + " " + wrappers(identifier))
    )

P05 = set()
for template in (
    "what does {} mean",
    "what did {} mean",
    "what is {}",
    "what was {}",
    "how does {} compare",
    "how did {} compare",
):
    P05.update(template.format(x) for x in ("this", "that", "it"))
for template in (
    "what are {}",
    "what were {}",
    "how do {} compare",
    "how did {} compare",
):
    P05.update(template.format(x) for x in ("these", "those", "they"))
for verb in ("explain", "summarize"):
    P05.update(verb + " " + x for x in ("this", "that", "these", "those", "it", "them"))
H = "company period year date table chart figure document context question amount value placeholder todo tbd"
INSERT_TARGETS = (
    "company period year date table chart figure document context question amount value"
)
for index, (left, right) in enumerate(
    (("[", "]"), ("<", ">"), ("{", "}"), ("{{", "}}"), ("${", "}"))
):
    PATTERNS["E06a_" + str(index)] = re.compile(
        re.escape(left) + " ?" + alternatives(H) + " ?" + re.escape(right)
    )
for index, (left, right) in enumerate((("[", "]"), ("<", ">"))):
    PATTERNS["E06b_" + str(index)] = re.compile(
        re.escape(left)
        + " ?insert "
        + alternatives(INSERT_TARGETS)
        + "(?: here)? ?"
        + re.escape(right)
    )
PATTERNS["E06c"] = re.compile(bounded(alternatives("__placeholder__ __todo__ __tbd__")))
PATTERNS["E06d"] = re.compile(r"(?<!\.)\.{3}$")


def reference(record):
    return {k: record[k] for k in FIELDS if k != "question"} | {
        "question_sha256": question_hash(record["question"])
    }


def reference_index(population):
    result = {}
    for record in population:
        require(
            isinstance(record, dict)
            and all(isinstance(record.get(k), str) for k in FIELDS),
            "invalid_canonical_record",
        )
        cid = record["cand_id"]
        require(
            re.fullmatch(r"c_[0-9a-f]{10}", cid) and cid not in result,
            "invalid_or_duplicate_canonical_id",
        )
        require(
            (record["source"], record["sampling_stratum"]) in STRATA,
            "invalid_canonical_source_stratum",
        )
        try:
            result[cid] = reference(record)
        except UnicodeError:
            raise ProtocolError("canonical_question_not_utf8") from None
    return result


def textual(question):
    view = normalize(question)
    matches = []
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(view):
            matches.append(
                {
                    "rule": name[:3],
                    "subrule": name,
                    "span": list(match.span()),
                    "text": match.group(0),
                }
            )
    if view in P05 or (view.endswith(("?", ".")) and view[:-1] in P05):
        matches.append(
            {"rule": "E05", "subrule": "E05", "span": [0, len(view)], "text": view}
        )
    return view, matches


def classify(record, refs, parse_error=None):
    invalid = [parse_error] if parse_error else []
    matches, view, usable = [], None, False
    if not isinstance(record, dict):
        invalid.append("not_json_object")
    else:
        for key in FIELDS:
            if key not in record:
                invalid.append("missing_" + key)
            elif not isinstance(record[key], str):
                invalid.append("nonstring_" + key)
        cid = record.get("cand_id")
        if isinstance(cid, str):
            if not re.fullmatch(r"c_[0-9a-f]{10}", cid):
                invalid.append("invalid_cand_id")
            if cid not in refs:
                invalid.append("unknown_cand_id")
        pair = (record.get("source"), record.get("sampling_stratum"))
        if not all(isinstance(x, str) for x in pair) or pair not in STRATA:
            invalid.append("invalid_source_stratum")
        ref = refs.get(cid) if isinstance(cid, str) else None
        if ref:
            for key in FIELDS:
                if key not in ("cand_id", "question") and record.get(key) != ref[key]:
                    invalid.append("reference_mismatch_" + key)
        question = record.get("question")
        if isinstance(question, str):
            try:
                digest = question_hash(question)
                usable = True
                view, matches = textual(question)
                if not view:
                    usable = False
                    invalid.append("normalized_empty_question")
                if ref and digest != ref["question_sha256"]:
                    invalid.append("question_hash_mismatch")
            except UnicodeEncodeError:
                invalid.append("question_not_strict_utf8")
    rules = {match["rule"] for match in matches}
    if invalid:
        rules.add("E07")
    disposition = (
        "INPUT_INVALID"
        if invalid
        else "DEPENDENCE_EXCLUDED"
        if rules & {"E02", "E03", "E04"}
        else "DIAGNOSTIC_ONLY"
        if rules & {"E05", "E06"}
        else "SCREEN_PASS"
    )
    return {
        "rules": sorted(rules),
        "matches": matches,
        "invalid": invalid,
        "disposition": disposition,
        "text_evaluable": usable,
        "normalized": view,
    }


def classify_json(raw, refs):
    try:
        return classify(decode(raw), refs)
    except DuplicateKeys:
        # JSON with duplicate keys has no unambiguous canonical question view.
        return classify(None, refs, "duplicate_json_key")
    except ProtocolError:
        return classify(None, refs, "invalid_json")
