"""Faithful pure isolation of the frozen pilot grams/cos functions; no selector import."""

import ast
import math
import re
from collections import Counter
from pathlib import Path
from experiments.reviewer_protocol_v2.common import require, verified_bytes, sha_bytes

SOURCE_SHA256 = "752a65fa744f04ae6854b2c8429fad9c43d3fc365fe763fb5d6600e64d7586a4"
THRESHOLD = 0.90


def grams(s, n=4):
    s = re.sub(r"\s+", " ", s.lower())
    return Counter(s[i : i + n] for i in range(max(1, len(s) - n + 1)))


def cos(a, b):
    num = sum(v * b[k] for k, v in a.items() if k in b)
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(
        sum(v * v for v in b.values())
    )
    return num / den if den else 0.0


def verify_isolation(path, raw=None):
    raw = verified_bytes(path, SOURCE_SHA256) if raw is None else raw
    require(sha_bytes(raw) == SOURCE_SHA256, "input_hash_mismatch")
    historical = ast.parse(raw.decode("utf-8", errors="strict"))
    isolated = ast.parse(Path(__file__).read_text(encoding="utf-8"))

    def pure(tree):
        return {
            node.name: ast.dump(node, include_attributes=False)
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in {"grams", "cos"}
        }

    require(pure(historical) == pure(isolated), "similarity_isolation_ast_mismatch")
    return SOURCE_SHA256


def conflicts(score):
    return score >= THRESHOLD
