"""Approved local JSON contract only. No provider/runtime settings are inferred."""

from experiments.reviewer_protocol_v2.common import DuplicateKeys, ProtocolError, decode

LABELS = ("qa", "summarize", "multi_intent", "out_of_scope", "unclear")
CERTAINTIES = ("sure", "unsure")
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["label", "components", "certainty", "rationale"],
    "properties": {
        "label": {"type": "string", "enum": list(LABELS)},
        "components": {
            "type": "array",
            "items": {"type": "string", "enum": ["qa", "summarize"]},
        },
        "certainty": {"type": "string", "enum": list(CERTAINTIES)},
        "rationale": {"type": "string", "minLength": 1, "maxLength": 300},
    },
}


def validate_text(text):
    """Return all safely evaluable findings in approved precedence order; never repair."""
    if not isinstance(text, str) or not text.strip():
        return {
            "valid": False,
            "primary": "F_NO_TEXT",
            "findings": ["F_NO_TEXT"],
            "vote": None,
        }
    try:
        vote = decode(text)
    except DuplicateKeys:
        return {
            "valid": False,
            "primary": "F_DUP_KEY",
            "findings": ["F_DUP_KEY"],
            "vote": None,
        }
    except ProtocolError:
        return {
            "valid": False,
            "primary": "F_JSON",
            "findings": ["F_JSON"],
            "vote": None,
        }
    if not isinstance(vote, dict):
        return {
            "valid": False,
            "primary": "F_JSON",
            "findings": ["F_JSON"],
            "vote": None,
        }
    findings = []
    if set(vote) != set(SCHEMA["required"]):
        findings.append("F_KEYS")
    strings = ("label", "certainty", "rationale")
    if any(key in vote and not isinstance(vote[key], str) for key in strings) or (
        "components" in vote
        and (
            not isinstance(vote["components"], list)
            or not all(isinstance(value, str) for value in vote["components"])
        )
    ):
        findings.append("F_TYPE")
    label, certainty, components, rationale = (
        vote.get(key) for key in ("label", "certainty", "components", "rationale")
    )
    if (
        isinstance(label, str)
        and label not in LABELS
        or isinstance(certainty, str)
        and certainty not in CERTAINTIES
        or isinstance(components, list)
        and all(isinstance(value, str) for value in components)
        and any(value not in ("qa", "summarize") for value in components)
    ):
        findings.append("F_ENUM")
    if (
        label in LABELS
        and isinstance(components, list)
        and all(isinstance(value, str) for value in components)
    ):
        if components != (["qa", "summarize"] if label == "multi_intent" else []):
            findings.append("F_COMPONENTS")
    if isinstance(rationale, str) and (
        not rationale.strip()
        or len(rationale) > 300
        or len(rationale.split()) > 25
        or any(character in rationale for character in "\n\r\v\f\x85\u2028\u2029")
    ):
        findings.append("F_RATIONALE")
    return {
        "valid": not findings,
        "primary": findings[0] if findings else None,
        "findings": findings,
        "vote": vote if not findings else None,
    }


def validate_service_response(*args, **kwargs):
    raise ProtocolError(
        "response_envelope_disabled_pending_approved_stop_and_reasoning_whitelists"
    )
