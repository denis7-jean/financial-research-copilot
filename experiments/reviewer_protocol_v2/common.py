"""Strict local IO and reproducible byte contracts; errors never disclose item text."""

import hashlib
import json
import platform
import sys
import unicodedata
from pathlib import Path


class ProtocolError(ValueError):
    """Sanitized protocol/integrity failure."""


class DuplicateKeys(ProtocolError):
    pass


def require(condition, code):
    if not condition:
        raise ProtocolError(code)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def question_hash(value):
    return sha_bytes(value.encode("utf-8", errors="strict"))


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def decode(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise DuplicateKeys("duplicate_json_key")
            result[key] = value
        return result

    def constant(_):
        raise ProtocolError("nonfinite_json")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, UnicodeError):
        raise ProtocolError("invalid_json") from None


def read_json(path):
    return decode(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    return [
        decode(line)
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def verify_file(path, expected):
    try:
        actual = sha_bytes(Path(path).read_bytes())
    except OSError:
        raise ProtocolError("missing_input") from None
    require(actual == expected, "input_hash_mismatch")
    return actual


def contained(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), "path_outside_root")
    return path


def check_runtime():
    require(
        platform.python_implementation() == "CPython"
        and sys.version_info[:3] == (3, 13, 12),
        "runtime_requires_cpython_3_13_12",
    )
    require(unicodedata.unidata_version == "15.1.0", "unicode_requires_15_1_0")
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "unicode": unicodedata.unidata_version,
    }
