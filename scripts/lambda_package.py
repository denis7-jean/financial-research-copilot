"""Offline wheelhouse ZIP assembly. No app imports, downloads or deployability claim.

Requires explicit target and supplied hash-locked wheels; metadata/header checks
do not establish Linux import/link compatibility, layer contents or readiness.
"""

import argparse
import ast
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import compatible_tags, cpython_tags, parse_tag
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

MAX_CODE_BYTES = 250 * 1024 * 1024
MAX_ZIP_BYTES = 50 * 1024 * 1024
RUNTIME_IMPORTS = {
    "boto3": "boto3",
    "botocore": "botocore",
    "fastapi": "fastapi",
    "mangum": "mangum",
    "pydantic": "pydantic",
    "dotenv": "python-dotenv",
    "faiss": "faiss-cpu",
    "numpy": "numpy",
    "httpx": "httpx",
}
SOURCE_NAMES = (
    "app/__init__.py",
    "app/main.py",
    "app/lambda_handler.py",
    "app/errors.py",
    "app/observability.py",
    "app/agents/__init__.py",
    "app/agents/router.py",
    "app/agents/jev_router.py",
    "app/agents/router_configuration.py",
    "app/agents/routing_contract.py",
    "app/agents/orchestrator.py",
    "app/agents/qa_agent.py",
    "app/agents/summarizer_agent.py",
    "app/services/__init__.py",
    "app/services/bedrock_client.py",
    "app/services/retriever.py",
)


class PackageError(ValueError):
    """Sanitized rejection codes; never subprocess output or private data."""


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PackageError("duplicate_json_key")
        result[key] = value
    return result


def nonfinite(_):
    raise PackageError("nonfinite_json")


def json_read(path):
    return json.loads(
        safe_file(path).read_bytes(),
        object_pairs_hook=no_duplicates,
        parse_constant=nonfinite,
    )


def is_link(path):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        return True
    # Path.is_junction is absent in Python 3.11. Reject Windows reparse points
    # there as well, rather than trusting a directory junction as an ordinary path.
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def no_links(path):
    if any(is_link(p) for p in (path, *path.parents)):
        raise PackageError("filesystem_link")


def safe_file(path):
    path = Path(path).absolute()
    no_links(path)
    if not path.is_file():
        raise PackageError("missing_file")
    return path


def safe_name(name):
    if (
        not name
        or any(ord(c) < 32 for c in name)
        or "\\" in name
        or ":" in name
        or PurePosixPath(name).is_absolute()
        or any(p in ("", ".", "..") for p in name.rstrip("/").split("/"))
    ):
        raise PackageError("unsafe_archive_path")
    for part in name.rstrip("/").split("/"):
        if part.rstrip(" .") != part or part.split(".")[0].upper() in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }:
            raise PackageError("unsafe_archive_path")
    return PurePosixPath(name)


def target_contract(runtime, platform, architecture, handler):
    if runtime != "python3.11" or architecture not in ("x86_64", "arm64"):
        raise PackageError("unsupported_target")
    suffix = "x86_64" if architecture == "x86_64" else "aarch64"
    if platform not in (f"manylinux2014_{suffix}", f"manylinux_2_17_{suffix}"):
        raise PackageError("target_platform_conflict")
    if handler not in ("lambda_handler.handler", "app.lambda_handler.handler"):
        raise PackageError("handler_layout")
    return {
        "runtime": runtime,
        "platform": platform,
        "architecture": architecture,
        "handler": handler,
    }


def native_check(name, raw, target):
    lower = name.lower()
    if lower.endswith((".pyd", ".dll", ".dylib", ".exe")) or raw[:2] == b"MZ":
        raise PackageError("non_linux_native")
    if raw[:4] in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"):
        raise PackageError("non_linux_native")
    abi = re.search(r"(?:cpython-|\.cp)(\d{2,3})", lower)
    if abi and abi.group(1) != "311":
        raise PackageError("native_python_abi")
    if ".so" in PurePosixPath(lower).name or raw[:4] == b"\x7fELF":
        machine = 62 if target["architecture"] == "x86_64" else 183
        if (
            len(raw) < 64
            or raw[:4] != b"\x7fELF"
            or raw[4:7] != b"\x02\x01\x01"
            or int.from_bytes(raw[18:20], "little") != machine
        ):
            raise PackageError("native_architecture")


def declarations(raw):
    result = {}
    for line in raw.decode().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        req = Requirement(line)
        specs = list(req.specifier)
        if (
            req.url
            or req.extras
            or req.marker
            or len(specs) != 1
            or specs[0].operator != "=="
            or "*" in str(req.specifier)
        ):
            raise PackageError("declaration_not_exact_pin")
        name = canonicalize_name(req.name)
        if name in result:
            raise PackageError("duplicate_declaration")
        result[name] = str(req.specifier)
    if not result:
        raise PackageError("missing_runtime_dependencies")
    return result


def inspect_wheel(path, expected, target):
    raw = safe_file(path).read_bytes()
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected)) or sha(raw) != expected:
        raise PackageError("wheel_hash")
    name, version, _, filename_tags = parse_wheel_filename(path.name)
    suffix = "x86_64" if target["architecture"] == "x86_64" else "aarch64"
    platforms = [f"manylinux2014_{suffix}", f"manylinux_2_17_{suffix}"]
    allowed = set(cpython_tags((3, 11), abis=["cp311"], platforms=platforms))
    allowed.update(compatible_tags((3, 11), interpreter="cp311", platforms=platforms))
    if not filename_tags.intersection(allowed):
        raise PackageError("wheel_target")
    files = {}
    total = 0
    with zipfile.ZipFile(path) as archive:
        seen = set()
        for info in archive.infolist():
            safe_name(info.orig_filename)
            if info.orig_filename != info.filename:
                raise PackageError("unsafe_archive_path")
            safe_name(info.filename)
            if info.filename in seen:
                raise PackageError("duplicate_archive_path")
            seen.add(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise PackageError("archive_symlink")
            if info.is_dir():
                continue
            total += info.file_size
            if total > MAX_CODE_BYTES:
                raise PackageError("wheel_size")
            content = archive.read(info)
            native_check(info.filename, content, target)
            files[info.filename] = content
    metadata_names = [n for n in files if n.endswith(".dist-info/METADATA")]
    if len(metadata_names) != 1:
        raise PackageError("wheel_metadata")
    prefix = metadata_names[0].rsplit("/", 1)[0]
    if prefix + "/WHEEL" not in files:
        raise PackageError("wheel_metadata")
    metadata = BytesParser().parsebytes(files[metadata_names[0]])
    wheel = BytesParser().parsebytes(files[prefix + "/WHEEL"])
    folder = prefix.removesuffix(".dist-info").rsplit("-", 1)
    if (
        len(folder) != 2
        or "/" in prefix
        or canonicalize_name(folder[0]) != name
        or Version(folder[1]) != version
        or len(metadata.get_all("Name", [])) != 1
        or len(metadata.get_all("Version", [])) != 1
    ):
        raise PackageError("wheel_identity")
    if (
        canonicalize_name(metadata["Name"] or "") != name
        or Version(metadata["Version"] or "0") != version
    ):
        raise PackageError("wheel_identity")
    tags = set()
    for tag in wheel.get_all("Tag", []):
        tags.update(parse_tag(tag))
    if tags != filename_tags:
        raise PackageError("wheel_tag_metadata")
    if metadata["Requires-Python"]:
        python_spec = SpecifierSet(metadata["Requires-Python"])
        # No observed Lambda patch version: don't assume the build host patch.
        # Patch-specific holes/bounds require more target evidence.
        if any(
            s.version.startswith("3.11.") and s.version not in ("3.11.0", "3.11.*")
            for s in python_spec
        ):
            raise PackageError("unresolved_runtime_python_patch")
        if not all(python_spec.contains(v) for v in ("3.11.0", "3.11.999999")):
            raise PackageError("wheel_python_version")
    installed = {}
    for filename, content in files.items():
        parts = list(PurePosixPath(filename).parts)
        if parts[0].endswith(".data"):
            if len(parts) < 3 or parts[1] not in ("purelib", "platlib"):
                raise PackageError("wheel_data_scheme")
            filename = "/".join(parts[2:])
        if filename in installed or filename.split("/")[0] in (
            "app",
            "lambda_handler.py",
            "lambda-build-manifest.json",
        ):
            raise PackageError("package_collision")
        if filename.endswith((".pth", ".pyc")) or PurePosixPath(filename).name in (
            "sitecustomize.py",
            "usercustomize.py",
            ".env",
        ):
            raise PackageError("wheel_startup_or_private_file")
        installed[filename] = content
    return {
        "filename": path.name,
        "sha256": expected,
        "name": name,
        "version": str(version),
        "requires_dist": metadata.get_all("Requires-Dist", []),
        "files": installed,
    }


def resolve_wheels(wheelhouse, lock, declared, target):
    if (
        type(lock) is not dict
        or set(lock) != {"schema", "target", "wheels"}
        or lock["schema"] != "lambda-wheel-lock-v1"
        or lock["target"] != target
        or type(lock["wheels"]) is not list
        or not lock["wheels"]
    ):
        raise PackageError("wheel_lock_contract")
    wheels, installed = {}, {}
    for entry in lock["wheels"]:
        if type(entry) is not dict or set(entry) != {"filename", "sha256"}:
            raise PackageError("wheel_lock_contract")
        filename = entry["filename"]
        if (
            type(filename) is not str
            or safe_name(filename).name != filename
            or not filename.endswith(".whl")
        ):
            raise PackageError("wheel_lock_path")
        record = inspect_wheel(Path(wheelhouse) / filename, entry["sha256"], target)
        if record["name"] in wheels:
            raise PackageError("duplicate_distribution")
        wheels[record["name"]] = record
        for name, content in record["files"].items():
            if name in installed:
                raise PackageError("package_collision")
            installed[name] = content
    env = default_environment()
    env.update(
        python_version="3.11",
        python_full_version="3.11.0",
        sys_platform="linux",
        os_name="posix",
        platform_system="Linux",
        implementation_name="cpython",
        platform_python_implementation="CPython",
        implementation_version="3.11.0",
        platform_machine="x86_64" if target["architecture"] == "x86_64" else "aarch64",
        extra="",
    )
    visited = set()
    todo = [Requirement(name + spec) for name, spec in declared.items()]
    while todo:
        req = todo.pop()
        # Runtime minor version is known; patch/kernel facts are not. Never
        # resolve these markers using the Windows build host's default values.
        if req.marker and any(
            field in str(req.marker)
            for field in (
                "python_full_version",
                "implementation_version",
                "platform_release",
                "platform_version",
            )
        ):
            raise PackageError("unresolved_runtime_marker")
        if req.marker and not req.marker.evaluate(env):
            continue
        if req.url or req.extras:
            raise PackageError("unsupported_dependency_reference")
        name = canonicalize_name(req.name)
        if name not in wheels or not req.specifier.contains(wheels[name]["version"]):
            raise PackageError("dependency_closure")
        if name not in visited:
            visited.add(name)
            todo.extend(Requirement(r) for r in wheels[name]["requires_dist"])
    if visited != set(wheels):
        raise PackageError("unrelated_distribution")
    return wheels, installed


def source_files(root, handler):
    root = Path(root).absolute()
    no_links(root)
    result = {}
    # Fixed reviewed layout; never copy arbitrary Python files/private extras
    # merely because they happen to sit inside app/. New modules need review.
    for relative in SOURCE_NAMES:
        path = root / relative
        raw = safe_file(path).read_bytes()
        ast.parse(raw, feature_version=(3, 11))
        result[relative] = raw
    if not {"app/lambda_handler.py", "app/main.py"}.issubset(result):
        raise PackageError("handler_layout")
    tree = ast.parse(result["app/lambda_handler.py"])
    if not any(
        isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "handler" for t in n.targets)
        for n in tree.body
    ):
        raise PackageError("handler_layout")
    if handler == "lambda_handler.handler":
        result["lambda_handler.py"] = result["app/lambda_handler.py"]
    return result


def runtime_imports(sources, declared, installed):
    for content in sources.values():
        for node in ast.walk(ast.parse(content)):
            modules = (
                [node.module]
                if isinstance(node, ast.ImportFrom) and node.module
                else [n.name for n in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            for module in modules:
                top = module.split(".")[0]
                if top in RUNTIME_IMPORTS:
                    if RUNTIME_IMPORTS[top] not in declared or not any(
                        n == top + ".py" or n.startswith(top + "/") for n in installed
                    ):
                        raise PackageError("missing_runtime_dependencies")
                elif top == "app":
                    base = module.replace(".", "/")
                    if (
                        base + ".py" not in sources
                        and base + "/__init__.py" not in sources
                    ):
                        raise PackageError("application_import_closure")
                elif top != "__future__" and top not in sys.stdlib_module_names:
                    raise PackageError("unmapped_runtime_import")


def layer_evidence(layers, target):
    if type(layers) is not list:
        raise PackageError("layer_metadata")
    required = {
        "arn",
        "code_size_bytes",
        "code_sha256",
        "compatible_runtimes",
        "compatible_architectures",
    }
    seen = set()
    for layer in layers:
        if (
            type(layer) is not dict
            or set(layer) != required
            or not re.fullmatch(
                r"arn:aws:lambda:[a-z0-9-]+:\d{12}:layer:[\w-]+:\d+", str(layer["arn"])
            )
        ):
            raise PackageError("layer_metadata")
        if (
            type(layer["code_size_bytes"]) is not int
            or layer["code_size_bytes"] < 0
            or layer["arn"] in seen
        ):
            raise PackageError("layer_metadata")
        seen.add(layer["arn"])
        try:
            valid_hash = (
                len(base64.b64decode(layer["code_sha256"], validate=True)) == 32
            )
        except (ValueError, TypeError):
            valid_hash = False
        if not valid_hash:
            raise PackageError("layer_metadata")
        for field, value in (
            ("compatible_runtimes", target["runtime"]),
            ("compatible_architectures", target["architecture"]),
        ):
            if layer[field] is not None and (
                type(layer[field]) is not list or value not in layer[field]
            ):
                raise PackageError("layer_target_conflict")
    return {
        "source": "CALLER_SUPPLIED_METADATA_NOT_CONTENT_INSPECTION",
        "layers": layers,
        "compressed_layer_bytes": sum(x["code_size_bytes"] for x in layers),
        "uncompressed_layer_bytes": None if layers else 0,
        "contents_verified": False if layers else None,
    }


def install_wheels(command, stage):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        check=False,
    )
    if result.returncode:
        raise PackageError("installer_failed")


def shipped_records(wheels, actual):
    # RECORD binds shipped paths, including relocated purelib/platlib files,
    # without host launcher/bookkeeping paths added by pip.
    for wheel in wheels.values():
        names = sorted(wheel["files"])
        records = [n for n in names if n.endswith(".dist-info/RECORD")]
        if len(records) != 1:
            raise PackageError("wheel_record")
        record = records[0]
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        for name in names:
            if name == record:
                writer.writerow((name, "", ""))
            else:
                raw = actual[name]
                digest = (
                    base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
                    .rstrip(b"=")
                    .decode()
                )
                writer.writerow((name, "sha256=" + digest, str(len(raw))))
        actual[record] = stream.getvalue().encode()


def assemble(
    root, target, wheelhouse, wheel_lock, layers, output, *, installer=install_wheels
):
    root, output = Path(root).absolute(), Path(output).absolute()
    no_links(root)
    no_links(output)
    if output.exists() or output.name.lower() == "deployment.zip":
        raise PackageError("output_exists_or_protected")
    if not output.parent.is_dir() or output.suffix != ".zip":
        raise PackageError("output_parent_or_suffix")
    target = target_contract(**target)
    requirements = safe_file(root / "requirements-lambda.txt").read_bytes()
    declared = declarations(requirements)
    sources = source_files(root, target["handler"])
    layer_info = layer_evidence(layers, target)
    wheels, installed = resolve_wheels(wheelhouse, wheel_lock, declared, target)
    runtime_imports(sources, declared, installed)
    with tempfile.TemporaryDirectory(
        prefix=".lambda-stage-", dir=output.parent
    ) as temporary:
        temp = Path(temporary)
        stage = temp / "package"
        stage.mkdir()
        locked = temp / "wheels"
        locked.mkdir()
        wheel_paths = []
        for record in sorted(wheels.values(), key=lambda r: r["filename"]):
            raw = safe_file(Path(wheelhouse) / record["filename"]).read_bytes()
            if sha(raw) != record["sha256"]:
                raise PackageError("wheel_hash")
            copy = locked / record["filename"]
            copy.write_bytes(raw)
            wheel_paths.append(str(copy))
        command = [
            sys.executable,
            "-B",
            "-m",
            "pip",
            "--isolated",
            "--disable-pip-version-check",
            "install",
            "--no-index",
            "--no-deps",
            "--only-binary=:all:",
            "--no-compile",
            "--no-warn-script-location",
            "--platform",
            target["platform"],
            "--python-version",
            "3.11",
            "--implementation",
            "cp",
            "--abi",
            "cp311",
            "--target",
            str(stage),
            *wheel_paths,
        ]
        installer(command, stage)
        actual = {}
        for path in stage.rglob("*"):
            no_links(path)
            if not path.is_file():
                continue
            name = path.relative_to(stage).as_posix()
            safe_name(name)
            raw = safe_file(path).read_bytes()
            if name not in installed:
                # Pip bookkeeping/entry-point wrappers are excluded, never executed.
                if name.startswith(("bin/", "Scripts/")) or name.endswith(
                    (
                        ".dist-info/INSTALLER",
                        ".dist-info/REQUESTED",
                        ".dist-info/direct_url.json",
                    )
                ):
                    continue
                raise PackageError("unexpected_installed_file")
            native_check(name, raw, target)
            if not name.endswith(".dist-info/RECORD") and raw != installed[name]:
                raise PackageError("installed_file_mismatch")
            actual[name] = installed[name]
        if set(actual) != set(installed):
            raise PackageError("missing_installed_file")
        shipped_records(wheels, actual)
        if (
            source_files(root, target["handler"]) != sources
            or safe_file(root / "requirements-lambda.txt").read_bytes() != requirements
        ):
            raise PackageError("stale_source_binding")
        entries = dict(actual)
        for name, raw in sources.items():
            if name in entries:
                raise PackageError("package_collision")
            entries[name] = raw
        manifest = {
            "schema": "lambda-build-manifest-v1",
            "status": "NOT_QUALIFIED_LINUX_EXECUTION_REQUIRED",
            "target": target,
            "builder_sha256": sha(safe_file(__file__).read_bytes()),
            "record_policy": "REGENERATED_FOR_SHIPPED_FILES_ONLY",
            "requirements_sha256": sha(requirements),
            "declared_dependencies": declared,
            "wheel_lock_sha256": sha(canonical(wheel_lock)),
            "resolved_inspected_wheels": [
                {
                    k: r[k]
                    for k in ("filename", "sha256", "name", "version", "requires_dist")
                }
                for r in sorted(wheels.values(), key=lambda r: r["name"])
            ],
            "source_sha256": {n: sha(b) for n, b in sorted(sources.items())},
            "file_sha256": {n: sha(b) for n, b in sorted(entries.items())},
            "layer_evidence": layer_info,
            "code_payload_uncompressed_bytes": sum(map(len, entries.values())),
            "aggregate_uncompressed_size_status": "UNRESOLVED_LAYER_CONTENTS"
            if layers
            else "CODE_ONLY",
            "validation": {
                "wheel_tags_and_native_headers": "PASSED",
                "linux_import_and_link": "NOT_RUN",
                "layer_content_and_shadowing": "NOT_RUN"
                if layers
                else "NO_LAYERS_DECLARED",
            },
            "artifact_hash_recipe": "SHA256 of final ZIP raw bytes (reported separately; no self-hash)",
        }
        entries["lambda-build-manifest.json"] = canonical(manifest)
        if sum(map(len, entries.values())) > MAX_CODE_BYTES:
            raise PackageError("code_uncompressed_size")
        staged_zip = temp / "artifact.zip"
        with zipfile.ZipFile(staged_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, raw in sorted(entries.items()):
                safe_name(name)
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, raw)
        artifact = staged_zip.read_bytes()
        if len(artifact) > MAX_ZIP_BYTES:
            raise PackageError("direct_upload_zip_size")
        with zipfile.ZipFile(staged_zip) as archive:
            if archive.testzip() is not None or set(archive.namelist()) != set(entries):
                raise PackageError("final_archive_integrity")
        # Same-filesystem exclusive atomic publication. No overwrite/fallback.
        os.link(staged_zip, output)
    return {
        "schema": "lambda-package-result-v1",
        "status": manifest["status"],
        "artifact_sha256": sha(artifact),
        "manifest_sha256": sha(entries["lambda-build-manifest.json"]),
        "zip_bytes": len(artifact),
        "code_uncompressed_bytes": sum(map(len, entries.values())),
        "layer_compressed_bytes": layer_info["compressed_layer_bytes"],
        "aggregate_uncompressed_bytes": None
        if layers
        else sum(map(len, entries.values())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "root",
        "runtime",
        "platform",
        "architecture",
        "handler",
        "wheelhouse",
        "wheel-lock",
        "layers-metadata",
        "output",
    ):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        target = target_contract(
            args.runtime, args.platform, args.architecture, args.handler
        )
        result = assemble(
            args.root,
            target,
            args.wheelhouse,
            json_read(args.wheel_lock),
            json_read(args.layers_metadata),
            args.output,
        )
        print(canonical(result).decode(), end="")
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as error:
        code = (
            str(error)
            if isinstance(error, PackageError)
            else "package_validation_failed"
        )
        print(
            canonical({"status": "FAILED", "code": code}).decode(),
            end="",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
