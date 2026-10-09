"""Recording constructors only; no actual SDK sessions, clients or native code."""

import ast
import builtins
from pathlib import Path
from threading import Barrier, Thread
from types import SimpleNamespace

import boto3
import botocore
from botocore import exceptions as e
from botocore.config import Config
from botocore.configprovider import ConfigValueStore, ConstantProvider
from botocore.session import Session
import pytest

from scripts import jev_rag_smoke_client_factory as factory
from scripts import jev_rag_smoke_live_adapter as adapter
from tests import offline_guard
from tests import test_jev_rag_smoke_adapter_consumer as consumer
from tests import test_jev_rag_smoke_live_adapter as fake

SETTINGS = {"max_attempts": 1, "connect_seconds": 2, "read_seconds": 10}
KEY = "INVENTED-STATIC-KEY"
SECRET = "INVENTED-STATIC-SECRET"
TOKEN = "INVENTED-EXPLICIT-TOKEN"


class RecordingSDK:
    boto3_version = botocore_version = "1.42.96"  # invented constructor contract
    expected_errors = (e.InvalidConfigError, e.PartialCredentialsError, OSError)
    Config = staticmethod(Config)  # installed definitions, not a client

    def __init__(self, client=None):
        self.client = client if client is not None else fake.Client()
        self.sessions = 0
        self.calls = []
        self.before = lambda: None
        self.error = None
        self.session_error = None

    def Session(self):
        self.before()
        self.sessions += 1
        if self.session_error:
            raise self.session_error
        return SimpleNamespace(create_client=self.create_client)

    def create_client(self, service, **kwargs):
        # Never log/store signing arguments, even invented ones. Verify inline.
        assert kwargs.pop("aws_access_key_id") == KEY
        assert kwargs.pop("aws_secret_access_key") == SECRET
        token = kwargs.pop("aws_session_token")
        assert token in (None, TOKEN)
        self.calls.append((service, kwargs))
        if self.error:
            raise self.error
        return self.client


def prepared(sdk, *, token=None, settings=None):
    value = factory.prepare(
        SETTINGS if settings is None else settings,
        access_key_id=KEY,
        secret_access_key=SECRET,
        session_token=token,
    )
    value._loader = lambda: sdk
    return value


def fail_again(value):
    with pytest.raises(adapter.AdapterError, match="^PARENT_ALREADY_ATTEMPTED$"):
        value()


def test_import_and_preparation_pure(monkeypatch):
    path = Path(factory.__file__)
    raw = path.read_bytes()
    tree = ast.parse(raw)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            assert node.module in {"threading", "types"}
        assert not isinstance(node, ast.Import)
    real_import = builtins.__import__

    def import_only_std(name, *args, **kwargs):
        assert name in {"threading", "types"}
        return real_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail("PREPARATION_SIDE_EFFECT")

    # Execute already read source, no import loader/file access in tested block.
    namespace = {"__name__": "invented_pure_factory"}
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden)
        m.setattr(builtins, "__import__", import_only_std)
        exec(compile(raw, "invented_module", "exec"), namespace)
        namespace["_load_sdk"] = forbidden
        result = namespace["prepare"](
            SETTINGS, access_key_id=KEY, secret_access_key=SECRET
        )
        assert repr(result) == "LambdaClientFactory(single_use=True)"


@pytest.mark.parametrize(
    "settings",
    [
        None,
        [],
        {},
        {**SETTINGS, "extra": True},
        {**SETTINGS, "max_attempts": 2},
        {**SETTINGS, "max_attempts": True},
        {**SETTINGS, "connect_seconds": 0},
        {**SETTINGS, "read_seconds": 121},
        {**SETTINGS, "read_seconds": 10.0},
        {**SETTINGS, "read_seconds": False},
    ],
)
def test_invalid_settings_before_sdk(settings, monkeypatch):
    monkeypatch.setattr(factory, "_load_sdk", lambda: pytest.fail("SDK_REACHED"))
    with pytest.raises(factory.FactoryError, match="^CLIENT_CONFIG_INVALID$"):
        factory.prepare(settings, access_key_id=KEY, secret_access_key=SECRET)


@pytest.mark.parametrize(
    "field", ["access_key_id", "secret_access_key", "session_token"]
)
@pytest.mark.parametrize(
    "bad", ["", b"bad", "has space", "line\nsecret", "é", "X" * 4097]
)
def test_invalid_material_sanitized(field, bad, monkeypatch):
    monkeypatch.setattr(factory, "_load_sdk", lambda: pytest.fail("SDK_REACHED"))
    inputs = {"access_key_id": KEY, "secret_access_key": SECRET, "session_token": TOKEN}
    inputs[field] = bad
    with pytest.raises(factory.FactoryError) as caught:
        factory.prepare(SETTINGS, **inputs)
    assert str(caught.value) == "CLIENT_CONFIG_INVALID"
    assert KEY not in repr(caught.value) and SECRET not in repr(caught.value)


@pytest.mark.parametrize("token", [None, TOKEN])
def test_explicit_args_config_and_no_secret_receipts(token, monkeypatch, capsys):
    # Conflicting invented environment settings must not alter explicit controls.
    for key in (
        "AWS_PROFILE",
        "AWS_ENDPOINT_URL_LAMBDA",
        "AWS_CA_BUNDLE",
        "HTTPS_PROXY",
        "AWS_MAX_ATTEMPTS",
        "AWS_DATA_PATH",
    ):
        monkeypatch.setenv(key, "invented-conflict")
    sdk = RecordingSDK()
    value = prepared(sdk, token=token)
    settings = value._settings
    assert value() is sdk.client
    assert sdk.sessions == len(sdk.calls) == 1
    service, args = sdk.calls[0]
    assert service == "lambda"
    assert args["region_name"] == "us-east-1"
    assert args["endpoint_url"] == adapter.ENDPOINT
    assert args["api_version"] == "2015-03-31"
    assert args["use_ssl"] is args["verify"] is True
    config = args["config"]
    for key, expected in factory._config_args(settings).items():
        assert getattr(config, key) == expected
    assert config.proxies == config.proxies_config == {}
    assert not hasattr(sdk.client, "simulation_only")
    assert all(s not in repr(value) + repr(sdk.calls) for s in (KEY, SECRET, TOKEN))
    fail_again(value)
    assert sdk.sessions == 1
    assert capsys.readouterr().out == ""


def test_settings_copied_and_boundaries():
    settings = {**SETTINGS, "connect_seconds": 1, "read_seconds": 120}
    sdk = RecordingSDK()
    sdk.client.meta.config.connect_timeout = 1
    sdk.client.meta.config.read_timeout = 120
    value = prepared(sdk, settings=settings)
    settings["read_seconds"] = 999
    value()
    assert sdk.calls[0][1]["config"].read_timeout == 120


@pytest.mark.parametrize("component", ["boto3", "botocore"])
def test_version_mismatch_before_constructor(component):
    sdk = RecordingSDK()
    setattr(sdk, component + "_version", "1.43.14")
    value = prepared(sdk)
    with pytest.raises(adapter.AdapterError, match="^CLIENT_CONFIG_INVALID$"):
        value()
    assert sdk.sessions == 0 and not sdk.calls
    fail_again(value)


def test_actual_environment_pin_without_any_session(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("ACTUAL_SESSION_CONSTRUCTION")

    monkeypatch.setattr(Session, "__init__", forbidden)
    monkeypatch.setattr(boto3.Session, "__init__", forbidden)
    if boto3.__version__ == botocore.__version__ == factory.SDK_PIN:
        sdk = factory._load_sdk()
        assert sdk.boto3_version == sdk.botocore_version == factory.SDK_PIN
        assert issubclass(sdk.Session, Session)
    else:
        with pytest.raises(adapter.AdapterError, match="^CLIENT_CONFIG_INVALID$"):
            factory._load_sdk()


def test_global_initializers_rejected_before_session(monkeypatch):
    monkeypatch.setattr(boto3, "__version__", factory.SDK_PIN)
    monkeypatch.setattr(botocore, "__version__", factory.SDK_PIN)
    monkeypatch.setattr(botocore, "_INITIALIZERS", [lambda _: pytest.fail("PLUGIN")])
    with pytest.raises(adapter.AdapterError, match="^CLIENT_CONFIG_INVALID$"):
        factory._load_sdk()


def test_pinned_session_controls_on_recording_base(monkeypatch):
    # Exercise actual subclass overrides with installed provider definitions;
    # the base is a recording object, NOT botocore.Session.
    components = {}
    reads = []

    class Base:
        SESSION_VARIABLES = Session.SESSION_VARIABLES

        def __init__(self):
            self._components = SimpleNamespace(
                register_component=lambda k, v: components.update({k: v}),
                lazy_register_component=lambda k, v: components.update({k: v}),
            )
            self._register_config_store()
            self._register_credential_provider()
            self._register_token_provider()
            self._register_user_agent_creator()
            self._register_data_loader()

    class Loader:
        BUILTIN_DATA_PATH = "invented-sdk-builtin-models"

        def __init__(self, **kwargs):
            reads.append(kwargs)

    sdk = SimpleNamespace(
        Session=Base,
        ConfigValueStore=ConfigValueStore,
        ConstantProvider=ConstantProvider,
        Loader=Loader,
        UserAgentString=lambda **kw: kw,
        errors=e,
    )
    # Read nothing from an invented competing credential/endpoint environment.
    import os

    class NoEnvironment(dict):
        def get(self, *args):
            pytest.fail("AMBIENT_ENVIRONMENT_READ")

        def __getitem__(self, *args):
            pytest.fail("AMBIENT_ENVIRONMENT_READ")

    with monkeypatch.context() as m:
        m.setattr(os, "environ", NoEnvironment())
        session = factory._session_type(sdk)()
        assert session.full_config == {"profiles": {}, "services": {}}
        assert session.get_scoped_config() == {}
        assert session.get_auth_token() is None
        assert session.user_agent() == "Botocore/1.42.96"
        session._register_client_plugins(None)
        session._add_configured_endpoint_provider("lambda", components["config_store"])
        with pytest.raises(e.PartialCredentialsError):
            session.get_credentials()
        components["data_loader"]()
        assert components["config_store"].get_config_variable("region") == "us-east-1"
        assert components["config_store"].get_config_variable("csm_enabled") is False
        assert components["config_store"].get_config_variable("unknown") is None
        assert components["config_store"].get_config_variable("endpoint_url") is None
    assert set(components) == {"config_store", "data_loader", "user_agent_creator"}
    assert components["user_agent_creator"]["execution_env"] is None
    assert reads == [
        {
            "extra_search_paths": [Loader.BUILTIN_DATA_PATH],
            "include_default_search_paths": False,
        }
    ]


@pytest.mark.parametrize("where", ["session", "client", "config"])
def test_expected_config_failure_sanitized_and_consumes_attempt(where):
    sdk = RecordingSDK()
    error = e.InvalidConfigError(error_msg=SECRET)
    if where == "session":
        sdk.session_error = error
    elif where == "client":
        sdk.error = error
    else:

        def fail(**kwargs):
            raise error

        sdk.Config = fail
    value = prepared(sdk)
    with pytest.raises(adapter.AdapterError) as caught:
        value()
    assert str(caught.value) == "CLIENT_CONFIG_INVALID"
    assert SECRET not in repr(caught.value)
    fail_again(value)


@pytest.mark.parametrize(
    "kind",
    [
        "endpoint",
        "region",
        "connect",
        "read",
        "retries",
        "boolean",
        "invoke",
        "close",
        "events",
    ],
)
def test_rejected_client_closed(kind):
    sdk = RecordingSDK()
    client = sdk.client
    if kind == "endpoint":
        client.meta.endpoint_url = "https://invented.invalid"
    elif kind == "region":
        client.meta.config.region_name = "us-west-2"
    elif kind in ("connect", "read"):
        setattr(client.meta.config, kind + "_timeout", 999)
    elif kind == "retries":
        client.meta.config.retries["max_attempts"] = 0
    elif kind == "boolean":
        client.meta.config.retries["total_max_attempts"] = True
    elif kind == "events":
        client.meta.events.register = None
    else:
        setattr(client, kind, None)
    value = prepared(sdk)
    with pytest.raises(adapter.AdapterError, match="^CLIENT_CONFIG_INVALID$"):
        value()
    assert client.closes == (0 if kind == "close" else 1)
    assert client.calls == 0
    fail_again(value)


def test_rejection_cleanup_does_not_replace_primary():
    sdk = RecordingSDK()
    sdk.client.meta.endpoint_url = "invented-invalid"
    sdk.client.close_error = RuntimeError("invented-cleanup-defect")
    with pytest.raises(adapter.AdapterError, match="^CLIENT_CONFIG_INVALID$"):
        prepared(sdk)()
    assert sdk.client.closes == 1


@pytest.mark.parametrize("where", ["loader", "session", "client", "validation"])
def test_programming_defects_original_traceback_and_cleanup(where):
    sdk = RecordingSDK()
    error = RuntimeError("invented-original-defect")
    value = prepared(sdk)

    def origin(*args, **kwargs):
        raise error

    if where == "loader":
        value._loader = origin
    elif where == "session":
        sdk.Session = origin
    elif where == "client":
        sdk.create_client = origin
    else:

        class BrokenMeta:
            @property
            def config(self):
                origin()

        sdk.client.meta = BrokenMeta()
        sdk.client.close_error = RuntimeError("invented-secondary")
    with pytest.raises(RuntimeError) as caught:
        value()
    assert caught.value is error
    frames = []
    tb = caught.value.__traceback__
    while tb:
        frames.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    assert "origin" in frames
    assert sdk.client.closes == (1 if where == "validation" else 0)
    fail_again(value)


def test_concurrent_and_repeat_calls_one_constructor():
    sdk = RecordingSDK()
    value = prepared(sdk)
    barrier = Barrier(3)
    outcomes = []

    def call():
        barrier.wait()
        try:
            outcomes.append(value())
        except adapter.AdapterError as err:
            outcomes.append(str(err))

    threads = [Thread(target=call) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert sdk.sessions == len(sdk.calls) == 1
    assert outcomes.count("PARENT_ALREADY_ATTEMPTED") == 1
    fail_again(value)


@pytest.fixture
def bundle(tmp_path):
    value = consumer.bundle.__wrapped__(tmp_path)
    sdk = RecordingSDK(value["client"])

    def closed_before_construction():
        directory = consumer.directory(value)
        for name in ("claim.json", "invocation-attempt.json"):
            # Persistent closed files, not merely an in-memory assertion.
            assert consumer.op.strict_json((directory / name).read_bytes())

    sdk.before = closed_before_construction
    value["sdk"] = sdk
    value["kwargs"]["client_factory"] = prepared(sdk)
    return value


@pytest.mark.parametrize("outcome", ["normal", "unknown", "config", "defect"])
def test_real_consumer_claim_factory_transport_and_duplicate(bundle, outcome):
    sdk = bundle["sdk"]
    if outcome == "unknown":
        sdk.client.error = e.ReadTimeoutError(endpoint_url="https://invented.invalid")
    if outcome == "config":
        sdk.error = e.InvalidConfigError(error_msg=SECRET)
    if outcome == "defect":
        sdk.error = RuntimeError("invented-propagated-defect")
    if outcome == "defect":
        with pytest.raises(RuntimeError) as caught:
            consumer.invoke(bundle)
        assert caught.value is sdk.error
        result = None
    else:
        result = consumer.invoke(bundle)
        record = consumer.index(bundle, result)
        assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
        assert record["initial_reservations_usd"]["whole_run"] == "9.1"
        assert record["assessment"]["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"
        assert not record["assessment"]["evidence_complete"]
        for field in (
            "owner_authorized",
            "invocation_authorized",
            "release_authorized",
        ):
            assert record[field] is False
        if outcome == "normal":
            assert result["status"] == "COMPLETE"
            assert consumer.op.confirm(result, consumer.directory(bundle)) == record
            request = consumer.op.strict_json(
                (consumer.directory(bundle) / "request.json").read_bytes()
            )["request"]
            assert request["FunctionName"] == (
                "arn:aws:lambda:us-east-1:123456789012:function:invented-isolated-smoke"
            )
            assert request["Qualifier"] == "$LATEST"
            assert sdk.client.delivered == 1
        else:
            assert result["status"] == "INTERRUPTED"
    directory = consumer.directory(bundle)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    for data in before.values():
        assert all(secret.encode() not in data for secret in (KEY, SECRET, TOKEN))
    sends = sdk.client.calls
    with pytest.raises(consumer.op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        consumer.invoke(bundle)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}
    assert sdk.sessions == len(sdk.calls) == 1 and sdk.client.calls == sends
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


def test_no_cli_or_accepted_code_changes():
    source = Path(factory.__file__).read_text()
    assert "__main__" not in source and "load_dotenv" not in source
    assert "simulation_only" not in source
    assert not hasattr(factory, "main")


def test_missing_sdk_import_fixed_code(monkeypatch):
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "boto3":
            raise ModuleNotFoundError("invented-sensitive-module-path")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(adapter.AdapterError, match="^CLIENT_CONFIG_INVALID$"):
        factory._load_sdk()


def test_expected_local_sdk_read_failure_consumes_attempt():
    sdk = RecordingSDK()
    sdk.session_error = OSError("invented-private-path")
    value = prepared(sdk)
    with pytest.raises(adapter.AdapterError, match="^CLIENT_CONFIG_INVALID$"):
        value()
    assert sdk.sessions == 1 and not sdk.calls
    fail_again(value)
