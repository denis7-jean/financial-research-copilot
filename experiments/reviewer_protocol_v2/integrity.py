"""Read-only verification of fixed historical inputs and offline output manifests."""

import json
from pathlib import Path
from experiments.reviewer_protocol_v2.common import (
    canonical,
    contained,
    read_json,
    require,
    sha_bytes,
    verify_file,
)

PINS_SHA256 = "ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae"
RECOVERY_SHA256 = "f4b7291b28c3367b305db7c6b18f858366190f6ac8156298f212b4d67ea5088a"
DESIGN_HASHES = {
    "original-design-evidence.md": "14d994451820984fe61e830670f9ed2f43137a96d93d9d84357d9279a9ae22d3",
    "revised-design-evidence.md": "1e23b4cb6a2fcf052634c039fa91ad8173ef0e82cb13512e4e5f58291bc11fab",
}


def verify_historical(root):
    root = Path(root).resolve()
    pins_path = Path(__file__).with_name("input_hashes.json")
    verify_file(pins_path, PINS_SHA256)
    pins = read_json(pins_path)
    for relative, expected in pins.items():
        verify_file(contained(root, relative), expected)
    ext = root / "heldout-external"
    bindings = 0
    for directory, sidecar in (
        ("pilot-v1", "pilot-v1.SHA256SUMS"),
        ("reviewer-protocol-v1", "reviewer-protocol-v1.SHA256SUMS"),
    ):
        for line in (ext / sidecar).read_text(encoding="utf-8").splitlines():
            expected, relative = line.split(" ", 1)
            verify_file(
                contained(
                    ext / directory, relative.strip().lstrip("*").removeprefix("./")
                ),
                expected,
            )
            bindings += 1
    for directory in ("reviewer-trial-v1.1", "reviewer-trial-v1.2"):
        frozen = read_json(ext / directory / "FROZEN.json")
        # Historical manifest bytes have no final newline. Do not apply the new IO contract.
        payload = json.dumps(
            frozen["files"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        require(
            sha_bytes(payload) == frozen["freeze_manifest_sha256"],
            "historical_manifest_mismatch",
        )
        for relative, expected in frozen["files"].items():
            verify_file(contained(ext, relative), expected)
            bindings += 1
    receipt = read_json(ext / "owner-audit-trial-v1.1/audit_receipt.json")
    verify_file(
        contained(ext / "owner-audit-trial-v1.1", receipt["completed_file"]),
        receipt["completed_sha256"],
    )
    bindings += 1
    return {
        "protected_files": len(pins),
        "frozen_bindings": bindings,
        "pins_sha256": PINS_SHA256,
        "files": pins,
        "verified": True,
    }


def verify_output_manifest(directory):
    directory = Path(directory).resolve()
    manifest = read_json(directory / "manifest.json")
    require(
        manifest.get("artifact_type") == "offline_unselected_audit"
        and manifest.get("frozen") is False,
        "not_offline_audit_manifest",
    )
    require(
        set(manifest["files"])
        == {
            "inventory.json",
            "population_ledger.jsonl",
            "aggregate.json",
            "integrity.json",
        },
        "invalid_audit_file_set",
    )
    for relative, expected in manifest["files"].items():
        verify_file(contained(directory, relative), expected)
    require(
        canonical(manifest) == (directory / "manifest.json").read_bytes(),
        "manifest_not_canonical",
    )
    return sha_bytes(canonical(manifest))
