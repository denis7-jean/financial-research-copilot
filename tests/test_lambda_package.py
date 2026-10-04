"""Invented wheels/workspaces only; installers are stubs, never pip or AWS."""

import ast
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from scripts import lambda_package as lp


TARGET = lp.target_contract(
    "python3.11", "manylinux2014_x86_64", "x86_64", "lambda_handler.handler"
)
LAYER = {
    "arn": "arn:aws:lambda:us-east-1:123456789012:layer:invented:2",
    "code_size_bytes": 123,
    "code_sha256": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "compatible_runtimes": ["python3.11"],
    "compatible_architectures": None,
}


def elf(machine=62):
    data = bytearray(64)
    data[:7] = b"\x7fELF\x02\x01\x01"
    data[18:20] = machine.to_bytes(2, "little")
    return bytes(data)


def wheel(
    directory,
    name="demo",
    tag="py3-none-any",
    requires=(),
    files=None,
    python=">=3.11",
    wheel_tag=None,
):
    filename = f"{name}-1.0-{tag}.whl"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\nRequires-Python: {python}\n"
    metadata += "".join(f"Requires-Dist: {r}\n" for r in requires)
    entries = {
        f"{name}/__init__.py": b"# invented, never executed\n",
        f"{name}-1.0.dist-info/METADATA": metadata.encode(),
        f"{name}-1.0.dist-info/WHEEL": f"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: {wheel_tag or tag}\n".encode(),
        f"{name}-1.0.dist-info/RECORD": b"",
    }
    entries.update(files or {})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for path, data in sorted(entries.items()):
            # ZipInfo otherwise normalizes Windows separators in the fixture.
            info = zipfile.ZipInfo()
            info.filename = path
            archive.writestr(info, data)
    path = directory / filename
    path.write_bytes(stream.getvalue())
    return {"filename": filename, "sha256": lp.sha(stream.getvalue())}


@pytest.fixture
def invented(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    for name in lp.SOURCE_NAMES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# invented\n")
    (root / "app/lambda_handler.py").write_bytes(
        b"from app.main import app\nhandler = app\n"
    )
    (root / "app/main.py").write_bytes(b"app = None\n")
    (root / "requirements-lambda.txt").write_bytes(b"demo==1.0\n")
    house = tmp_path / "wheelhouse"
    house.mkdir()
    entry = wheel(
        house,
        requires=(
            'child==1.0; sys_platform == "linux"',
            'absent==1; sys_platform == "win32"',
        ),
    )
    child = wheel(house, name="child")
    lock = {
        "schema": "lambda-wheel-lock-v1",
        "target": dict(TARGET),
        "wheels": [entry, child],
    }
    old = root / "deployment.zip"
    old.write_bytes(b"invented previous artifact")
    calls = []

    def install(command, stage):
        calls.append(list(command))
        for value in command:
            if value.endswith(".whl"):
                with zipfile.ZipFile(value) as archive:
                    for name in archive.namelist():
                        dest = stage / name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(archive.read(name))

    def build(output="new.zip", **kwargs):
        return lp.assemble(
            root,
            kwargs.pop("target", dict(TARGET)),
            house,
            kwargs.pop("lock", lock),
            kwargs.pop("layers", [copy.deepcopy(LAYER)]),
            tmp_path / output,
            installer=kwargs.pop("installer", install),
            **kwargs,
        )

    return root, house, lock, calls, install, build


def rejects(code, action):
    with pytest.raises(lp.PackageError, match=f"^{code}$"):
        action()


def test_complete_deterministic_assembly_and_unresolved_layers(invented, tmp_path):
    root, _, _, calls, _, build = invented
    for name in (
        ".env",
        "eval/results/private.json",
        "heldout-external/private.json",
        "app/private.py",
        "app/__pycache__/private.pyc",
        "app/services/build_index.py",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"invented private content")
    first, second = build(), build("other.zip")
    assert first == second
    assert first["status"] == "NOT_QUALIFIED_LINUX_EXECUTION_REQUIRED"
    assert first["layer_compressed_bytes"] == 123
    assert first["aggregate_uncompressed_bytes"] is None
    assert (root / "deployment.zip").read_bytes() == b"invented previous artifact"
    assert not list(tmp_path.glob(".lambda-stage-*"))
    command = calls[0]
    for flag in (
        "--isolated",
        "--no-index",
        "--no-deps",
        "--only-binary=:all:",
        "--no-compile",
    ):
        assert flag in command
    assert command[command.index("--platform") + 1] == TARGET["platform"]
    assert command[command.index("--python-version") + 1] == "3.11"
    assert command[command.index("--abi") + 1] == "cp311"
    with zipfile.ZipFile(tmp_path / "new.zip") as archive:
        manifest = json.loads(archive.read("lambda-build-manifest.json"))
        assert archive.read("lambda_handler.py") == archive.read(
            "app/lambda_handler.py"
        )
        assert len(manifest["source_sha256"]) == len(lp.SOURCE_NAMES) + 1
        assert manifest["declared_dependencies"] == {"demo": "==1.0"}
        assert {w["name"] for w in manifest["resolved_inspected_wheels"]} == {
            "demo",
            "child",
        }
        assert manifest["validation"]["linux_import_and_link"] == "NOT_RUN"
        assert (
            manifest["aggregate_uncompressed_size_status"]
            == "UNRESOLVED_LAYER_CONTENTS"
        )
        assert manifest["layer_evidence"]["uncompressed_layer_bytes"] is None
        assert not any("private" in n or "build_index" in n for n in archive.namelist())
        for name, expected in manifest["file_sha256"].items():
            assert lp.sha(archive.read(name)) == expected
    assert lp.sha((tmp_path / "new.zip").read_bytes()) == first["artifact_sha256"]


@pytest.mark.parametrize(
    "tag,files,code",
    [
        ("cp311-cp311-win_amd64", {}, "wheel_target"),
        ("cp313-cp313-manylinux2014_x86_64", {}, "wheel_target"),
        ("cp311-cp311-manylinux2014_aarch64", {}, "wheel_target"),
        ("cp311-cp311-manylinux_2_28_x86_64", {}, "wheel_target"),
        ("py3-none-any", {"demo/native.pyd": b"MZ"}, "non_linux_native"),
        ("py3-none-any", {"demo/native.so": elf(183)}, "native_architecture"),
        ("py3-none-any", {"demo/native.so": b"not ELF"}, "native_architecture"),
        (
            "py3-none-any",
            {"demo/native.cpython-313-x86_64-linux-gnu.so": elf()},
            "native_python_abi",
        ),
        ("py3-none-any", {"../escape.py": b""}, "unsafe_archive_path"),
        ("py3-none-any", {"C:/escape.py": b""}, "unsafe_archive_path"),
        ("py3-none-any", {"demo\\escape.py": b""}, "unsafe_archive_path"),
        (
            "py3-none-any",
            {"evil.pth": b"import secret"},
            "wheel_startup_or_private_file",
        ),
        ("py3-none-any", {"app/main.py": b""}, "package_collision"),
    ],
)
def test_wheel_rejection_before_installer(invented, tag, files, code):
    _, house, lock, calls, _, build = invented
    lock["wheels"] = [wheel(house, tag=tag, files=files)]
    rejects(code, build)
    assert not calls


def test_linux_native_header_passes_without_claiming_execution(invented):
    _, house, lock, _, _, build = invented
    lock["wheels"] = [
        wheel(
            house,
            tag="cp311-cp311-manylinux2014_x86_64",
            files={"demo/native.cpython-311-x86_64-linux-gnu.so": elf()},
        )
    ]
    assert build()["status"] == "NOT_QUALIFIED_LINUX_EXECUTION_REQUIRED"


@pytest.mark.parametrize(
    "change,code",
    [
        ({"runtime": "python3.13"}, "unsupported_target"),
        ({"architecture": "arm64"}, "target_platform_conflict"),
        ({"platform": "win_amd64"}, "target_platform_conflict"),
        ({"handler": "missing.handler"}, "handler_layout"),
    ],
)
def test_conflicting_target(invented, change, code):
    *_, build = invented
    target = dict(TARGET, **change)
    rejects(code, lambda: build(target=target))


def test_missing_target_is_required_before_work(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["lambda_package.py"])
    with pytest.raises(SystemExit) as result:
        lp.main()
    assert result.value.code == 2


@pytest.mark.parametrize(
    "requires,code",
    [
        (("absent==1.0",), "dependency_closure"),
        (("child>=2",), "dependency_closure"),
        (('child==1; python_full_version > "3.11.0"',), "unresolved_runtime_marker"),
        (
            ("demo @ https://invalid.example/package",),
            "unsupported_dependency_reference",
        ),
    ],
)
def test_dependency_closure(invented, requires, code):
    _, house, lock, calls, _, build = invented
    lock["wheels"][0] = wheel(house, requires=requires)
    rejects(code, build)
    assert not calls


def test_missing_distribution_and_undeclared_import(invented):
    root, _, lock, calls, _, build = invented
    lock["wheels"].pop()
    rejects("dependency_closure", build)
    assert not calls
    (root / "app/main.py").write_bytes(b"import boto3\napp=None\n")
    lock["wheels"][0] = wheel(invented[1])
    rejects("missing_runtime_dependencies", build)
    assert not calls


def test_stale_sources_and_requirements_preserve_previous(invented, tmp_path):
    root, _, _, _, install, build = invented

    def mutate(command, stage):
        install(command, stage)
        (root / "app/main.py").write_bytes(b"app = 'changed'\n")

    rejects("stale_source_binding", lambda: build(installer=mutate))
    assert not (tmp_path / "new.zip").exists()
    assert (root / "deployment.zip").read_bytes() == b"invented previous artifact"
    assert not list(tmp_path.glob(".lambda-stage-*"))


@pytest.mark.parametrize(
    "mode,code",
    [
        ("missing", "missing_installed_file"),
        ("altered", "installed_file_mismatch"),
        ("extra", "unexpected_installed_file"),
    ],
)
def test_installed_bytes_are_checked(invented, mode, code):
    *_, install, build = invented

    def modify(command, stage):
        install(command, stage)
        file = stage / "demo/__init__.py"
        if mode == "missing":
            file.unlink()
        elif mode == "altered":
            file.write_bytes(b"altered")
        else:
            (stage / ".env").write_bytes(b"invented secret")

    rejects(code, lambda: build(installer=modify))


def test_installer_exit_and_timeout_preserve_output(invented, tmp_path, monkeypatch):
    root, _, _, _, _, build = invented

    def failed(*args, **kwargs):
        assert kwargs["timeout"] == 300
        assert not kwargs["check"]
        return subprocess.CompletedProcess(
            args[0], 1, b"invented secret", b"invented secret"
        )

    monkeypatch.setattr(lp.subprocess, "run", failed)
    rejects("installer_failed", lambda: build(installer=lp.install_wheels))

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 300)

    monkeypatch.setattr(lp.subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        build(installer=lp.install_wheels)
    assert not (tmp_path / "new.zip").exists()
    assert (root / "deployment.zip").read_bytes() == b"invented previous artifact"


def test_existing_and_raced_outputs_never_replaced(invented, tmp_path):
    _, _, _, calls, install, build = invented
    (tmp_path / "new.zip").write_bytes(b"previous")
    rejects("output_exists_or_protected", build)
    assert not calls

    def race(command, stage):
        install(command, stage)
        (tmp_path / "raced.zip").write_bytes(b"other writer")

    with pytest.raises(FileExistsError):
        build("raced.zip", installer=race)
    assert (tmp_path / "raced.zip").read_bytes() == b"other writer"
    assert (tmp_path / "new.zip").read_bytes() == b"previous"


def test_protected_output_name_and_invalid_handler(invented):
    root, _, _, calls, _, build = invented
    rejects("output_exists_or_protected", lambda: build("deployment.zip"))
    (root / "app/lambda_handler.py").write_bytes(b"not_handler = None\n")
    rejects("handler_layout", build)
    assert not calls


def test_hash_tag_metadata_and_lock_target(invented):
    _, house, lock, calls, _, build = invented
    lock["wheels"][0]["sha256"] = "0" * 64
    rejects("wheel_hash", build)
    lock["wheels"][0] = wheel(house, wheel_tag="cp311-cp311-win_amd64")
    rejects("wheel_tag_metadata", build)
    lock["target"]["handler"] = "app.lambda_handler.handler"
    rejects("wheel_lock_contract", build)
    assert not calls


def test_layer_target_conflict_and_no_layer_accounting(invented):
    *_, build = invented
    incompatible = dict(LAYER, compatible_architectures=["arm64"])
    rejects("layer_target_conflict", lambda: build(layers=[incompatible]))
    result = build(layers=[])
    assert result["layer_compressed_bytes"] == 0
    assert result["aggregate_uncompressed_bytes"] == result["code_uncompressed_bytes"]
    assert result["status"] != "DEPLOYABLE"


def test_size_failures_are_not_layer_success(invented, tmp_path, monkeypatch):
    *_, build = invented
    monkeypatch.setattr(lp, "MAX_ZIP_BYTES", 1)
    rejects("direct_upload_zip_size", build)
    assert not (tmp_path / "new.zip").exists()


def test_source_symlink_escape(invented, tmp_path):
    root, _, _, calls, _, build = invented
    path = root / "app/main.py"
    path.unlink()
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"app=None\n")
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Windows symlink privilege unavailable")
    rejects("filesystem_link", build)
    assert not calls


def test_repository_pins_and_source_layout_static_only():
    root = Path(__file__).resolve().parents[1]
    pins = lp.declarations((root / "requirements-lambda.txt").read_bytes())
    old = (root / "requirements.txt").read_text()
    for name, spec in pins.items():
        assert any(
            lp.canonicalize_name(line.split("==")[0]) == name
            and line.strip().endswith(spec)
            for line in old.splitlines()
            if "==" in line
        )
    assert not {"pytest", "ruff", "uvicorn", "pymupdf", "pydantic-ai"}.intersection(
        pins
    )
    sources = lp.source_files(root, TARGET["handler"])
    assert len(sources) == 17
    # Static closure of import names; no app/client/model initialization.
    pretend_files = {module + "/__init__.py": b"" for module in lp.RUNTIME_IMPORTS}
    lp.runtime_imports(sources, pins, pretend_files)
    for raw in sources.values():
        ast.parse(raw, feature_version=(3, 11))


def test_powershell_wrapper_has_no_destructive_or_host_pip_path():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/package_lambda.ps1").read_text()
    assert "$LASTEXITCODE -ne 0" in script
    assert "Remove-Item" not in script and "Compress-Archive" not in script
    assert "pip.exe" not in script
    assert script.count("[Parameter(Mandatory)]") == 8


def test_generated_host_launcher_is_excluded(invented, tmp_path):
    *_, install, build = invented

    def with_bookkeeping(command, stage):
        install(command, stage)
        (stage / "bin").mkdir()
        (stage / "bin/demo.exe").write_bytes(b"MZ invented host launcher")
        (stage / "demo-1.0.dist-info/direct_url.json").write_bytes(
            b"invented local path"
        )

    build(installer=with_bookkeeping)
    with zipfile.ZipFile(tmp_path / "new.zip") as archive:
        assert not any(
            n.startswith("bin/") or "direct_url.json" in n for n in archive.namelist()
        )


def test_unrelated_development_wheel_is_rejected(invented):
    _, house, lock, calls, _, build = invented
    lock["wheels"].append(wheel(house, name="invented_dev_tool"))
    rejects("unrelated_distribution", build)
    assert not calls


def test_unselected_extras_do_not_expand_runtime_closure(invented):
    _, house, lock, _, _, build = invented
    lock["wheels"][0] = wheel(
        house, requires=("child==1.0", 'absent[tools]==1; extra == "dev"')
    )
    assert build()["status"] == "NOT_QUALIFIED_LINUX_EXECUTION_REQUIRED"


def test_relocated_library_paths_and_records(invented, tmp_path):
    _, house, lock, _, _, build = invented
    lock["wheels"] = [
        wheel(
            house,
            files={
                "demo-1.0.data/purelib/relocated.py": b"# invented relocated library\n"
            },
        )
    ]

    def relocated(command, stage):
        for value in command:
            if value.endswith(".whl"):
                files = lp.inspect_wheel(
                    Path(value), lp.sha(Path(value).read_bytes()), TARGET
                )["files"]
                for name, data in files.items():
                    dest = stage / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)

    build(installer=relocated)
    with zipfile.ZipFile(tmp_path / "new.zip") as archive:
        assert "relocated.py" in archive.namelist()
        assert not any(".data/" in n for n in archive.namelist())
        record = archive.read("demo-1.0.dist-info/RECORD").decode()
        assert "relocated.py,sha256=" in record and ".data/" not in record


@pytest.mark.parametrize(
    "python,code",
    [
        (">=3.12", "wheel_python_version"),
        (">=3.11.2", "unresolved_runtime_python_patch"),
    ],
)
def test_python_metadata_must_support_known_runtime(invented, python, code):
    _, house, lock, calls, _, build = invented
    lock["wheels"] = [wheel(house, python=python)]
    rejects(code, build)
    assert not calls


def test_app_qualified_handler_and_requirements_mutation(invented, tmp_path):
    root, _, lock, _, install, build = invented
    target = dict(TARGET, handler="app.lambda_handler.handler")
    lock["target"] = target
    build(target=target)
    with zipfile.ZipFile(tmp_path / "new.zip") as archive:
        assert "lambda_handler.py" not in archive.namelist()

    def changed(command, stage):
        install(command, stage)
        (root / "requirements-lambda.txt").write_bytes(b"demo==2.0\n")

    rejects(
        "stale_source_binding",
        lambda: build("changed.zip", target=target, installer=changed),
    )


def test_json_contract_rejects_duplicates_and_nonfinite(tmp_path):
    for raw, code in (
        (b'{"schema":1,"schema":2}', "duplicate_json_key"),
        (b'{"a":NaN}', "nonfinite_json"),
    ):
        path = tmp_path / "invented.json"
        path.write_bytes(raw)
        rejects(code, lambda: lp.json_read(path))


def test_archive_symlink_and_duplicate_paths(invented):
    _, house, lock, calls, _, build = invented
    import stat

    record = wheel(house)
    with zipfile.ZipFile(house / record["filename"], "a") as archive:
        info = zipfile.ZipInfo("demo/escape")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "../../outside")
    record["sha256"] = lp.sha((house / record["filename"]).read_bytes())
    lock["wheels"] = [record]
    rejects("archive_symlink", build)
    record = wheel(house)
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(house / record["filename"], "a") as archive:
            archive.writestr("demo/__init__.py", b"duplicate")
    record["sha256"] = lp.sha((house / record["filename"]).read_bytes())
    lock["wheels"] = [record]
    rejects("duplicate_archive_path", build)
    assert not calls


def test_cli_failure_is_sanitized(invented, tmp_path, monkeypatch, capsys):
    root, house, _, _, _, _ = invented
    invalid = tmp_path / "lock.json"
    invalid.write_bytes(b"invented secret not valid JSON")
    layers = tmp_path / "layers.json"
    layers.write_bytes(b"[]")
    args = [
        "lambda_package.py",
        "--root",
        str(root),
        "--wheelhouse",
        str(house),
        "--wheel-lock",
        str(invalid),
        "--layers-metadata",
        str(layers),
        "--output",
        str(tmp_path / "new.zip"),
    ]
    for key, value in TARGET.items():
        args.extend(["--" + key, value])
    monkeypatch.setattr(sys, "argv", args)
    assert lp.main() == 1
    captured = capsys.readouterr()
    assert json.loads(captured.err) == {
        "status": "FAILED",
        "code": "package_validation_failed",
    }
    assert "secret" not in captured.err and str(tmp_path) not in captured.err


def test_unresolved_layer_metadata_and_missing_source(invented):
    root, _, _, calls, _, build = invented
    rejects(
        "layer_metadata", lambda: build(layers=[dict(LAYER, code_sha256="not a hash")])
    )
    (root / "app/main.py").unlink()
    rejects("missing_file", build)
    assert not calls


def test_reparse_point_rejected_without_junction_api():
    from types import SimpleNamespace

    class InventedPath:
        def is_symlink(self):
            return False

        def lstat(self):
            return SimpleNamespace(st_file_attributes=0x400)

    assert lp.is_link(InventedPath())
