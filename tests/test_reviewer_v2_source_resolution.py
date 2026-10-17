"""Current source paths are checkout-local; external evidence retains its pins."""

import json
import subprocess
import sys

import pytest

from experiments.reviewer_protocol_v2 import selection as s
from experiments.reviewer_protocol_v2.common import ProtocolError, canonical, sha_bytes


@pytest.mark.parametrize("name", ["renamed-checkout", "nested/worktrees/topic"])
def test_bundle_uses_relocated_checkout_not_sibling_main(tmp_path, name):
    checkout = tmp_path / name
    expected = {}
    for logical in s.BUNDLE_PATHS:
        raw = s.repository_source_path(logical).read_bytes()
        target = checkout / logical.removeprefix("main/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        expected[logical] = sha_bytes(raw)
        # A stale sibling must never supply the executing source bytes.
        decoy = checkout.parent / logical
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_bytes(b"# stale sibling source\n")
    program = '''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from experiments.reviewer_protocol_v2 import selection
assert selection.SOURCE_ROOT == Path(sys.argv[1]).resolve()
print(json.dumps(selection.selection_bundle()))
'''
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", program, str(checkout)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {
        "files": expected, "sha256": sha_bytes(canonical(expected)),
    }


@pytest.mark.parametrize("path", [
    "heldout-external/pinned.py", "main/../escape.py", "main//source.py",
    "/main/source.py", "main\\source.py", "main/C:/source.py", "main", None,
])
def test_repository_source_resolver_rejects_other_namespaces_and_escapes(path):
    with pytest.raises(ProtocolError, match="repository_source_path"):
        s.repository_source_path(path)


def test_missing_current_source_does_not_fall_back_to_sibling(tmp_path, monkeypatch):
    checkout = tmp_path / "topic"
    checkout.mkdir()
    for logical in s.BUNDLE_PATHS:
        decoy = tmp_path / logical
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_bytes(b"stale source")
    monkeypatch.setattr(s, "SOURCE_ROOT", checkout)
    with pytest.raises(FileNotFoundError):
        s.selection_bundle()


def test_current_source_mutation_changes_bundle_hash(tmp_path, monkeypatch):
    for logical in s.BUNDLE_PATHS:
        target = tmp_path / logical.removeprefix("main/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(s.repository_source_path(logical).read_bytes())
    monkeypatch.setattr(s, "SOURCE_ROOT", tmp_path)
    before = s.selection_bundle()
    s.repository_source_path(s.PREFIX + "common.py").write_bytes(b"changed source")
    after = s.selection_bundle()
    assert before["sha256"] != after["sha256"]
    assert before["files"][s.PREFIX + "common.py"] != after["files"][s.PREFIX + "common.py"]


def test_external_evidence_still_requires_its_explicit_root_and_raw_hash(tmp_path):
    external_root = tmp_path / "separate-evidence"
    path = external_root / "heldout-external/pinned.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"retained external bytes")
    binding = {"path": "heldout-external/pinned.txt", "sha256": sha_bytes(path.read_bytes())}
    assert s.read_file_binding(external_root, binding) == b"retained external bytes"
    path.write_bytes(b"changed evidence")
    with pytest.raises(ProtocolError, match="input_hash_mismatch"):
        s.read_file_binding(external_root, binding)
