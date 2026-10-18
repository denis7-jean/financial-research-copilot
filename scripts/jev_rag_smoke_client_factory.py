"""One-use host-side Lambda factory. No SDK import, I/O or credential discovery.

Preparing the callable grants no authority. consume_adapter owns the persistent
claim before calling it. SDK construction is lazy and separately gated for live
use; tests replace constructors, never instantiate real sessions or clients.
"""

from threading import Lock
from types import SimpleNamespace

SDK_PIN = "1.42.96"
REGION = "us-east-1"
ENDPOINT = "https://lambda.us-east-1.amazonaws.com"


class FactoryError(ValueError):
    """Preparation failures contain only this fixed code."""

    def __init__(self):
        super().__init__("CLIENT_CONFIG_INVALID")


def _valid_signing(value):
    return (
        type(value) is str
        and 0 < len(value) <= 4096
        and value.isascii()
        and all(33 <= ord(c) <= 126 for c in value)
    )


def _session_type(sdk):
    """Pinned SDK extension points, with no ambient configuration providers.

    Kept separate so recording base classes can exercise these controls without
    instantiating a real SDK session. Not a general-purpose boto3 session.
    """

    class StaticSession(sdk.Session):
        @property
        def full_config(self):
            return {"profiles": {}, "services": {}}

        def get_scoped_config(self):
            return {}

        def _add_configured_endpoint_provider(self, client_name, config_store):
            config_store.set_config_variable("endpoint_url", None)

        def _register_config_store(self):
            # Preserve pinned scalar SDK defaults, not their environment/profile
            # chains. Unknown settings resolve to None, never to ambient values.
            defaults = {k: v[2] for k, v in self.SESSION_VARIABLES.items()}
            defaults.update(region=REGION, csm_enabled=False, defaults_mode="legacy")
            self._components.register_component(
                "config_store",
                sdk.ConfigValueStore(
                    mapping={k: sdk.ConstantProvider(v) for k, v in defaults.items()}
                ),
            )

        def _register_credential_provider(self):
            pass

        def _register_token_provider(self):
            pass

        def get_credentials(self):
            # create_client must receive both explicit keys. No fallback exists.
            raise sdk.errors.PartialCredentialsError(
                provider="explicit", cred_var="explicit"
            )

        def get_auth_token(self, **kwargs):
            return None

        def _register_data_loader(self):
            self._components.lazy_register_component(
                "data_loader",
                lambda: sdk.Loader(
                    extra_search_paths=[sdk.Loader.BUILTIN_DATA_PATH],
                    include_default_search_paths=False,
                ),
            )

        def _register_user_agent_creator(self):
            self._components.register_component(
                "user_agent_creator",
                sdk.UserAgentString(
                    platform_name="host",
                    platform_version="unspecified",
                    platform_machine="unspecified",
                    python_version="unspecified",
                    python_implementation="Python",
                    execution_env=None,
                ),
            )

        def user_agent(self):
            return "Botocore/" + SDK_PIN

        def _register_client_plugins(self, client):
            pass

    return StaticSession


def _load_sdk():
    """Import/version checks occur only after the factory's one-use claim."""
    from scripts import jev_rag_smoke_live_adapter as adapter

    try:
        import boto3
        import botocore
    except ModuleNotFoundError:
        raise adapter.AdapterError("CLIENT_CONFIG_INVALID") from None

    if boto3.__version__ != SDK_PIN or botocore.__version__ != SDK_PIN:
        raise adapter.AdapterError("CLIENT_CONFIG_INVALID") from None
    # Session.__init__ invokes process-global initializers. Do not execute any.
    # This private guard, like the overrides below, belongs to this exact pin.
    if botocore._INITIALIZERS:
        raise adapter.AdapterError("CLIENT_CONFIG_INVALID") from None

    from botocore import exceptions
    from botocore.config import Config
    from botocore.configprovider import ConfigValueStore, ConstantProvider
    from botocore.loaders import Loader
    from botocore.session import Session
    from botocore.useragent import UserAgentString

    return SimpleNamespace(
        boto3_version=boto3.__version__,
        botocore_version=botocore.__version__,
        Session=_session_type(
            SimpleNamespace(
                Session=Session,
                ConfigValueStore=ConfigValueStore,
                ConstantProvider=ConstantProvider,
                Loader=Loader,
                UserAgentString=UserAgentString,
                errors=exceptions,
            )
        ),
        Config=Config,
        expected_errors=(
            OSError,
            exceptions.PartialCredentialsError,
            exceptions.NoRegionError,
            exceptions.DataNotFoundError,
            exceptions.InvalidConfigError,
            exceptions.InvalidRegionError,
            exceptions.InvalidRetryConfigurationError,
            exceptions.InvalidProxiesConfigError,
            exceptions.InvalidEndpointConfigurationError,
        ),
    )


def _config_args(settings):
    return {
        "region_name": REGION,
        "signature_version": "v4",
        "connect_timeout": settings["connect_seconds"],
        "read_timeout": settings["read_seconds"],
        "retries": {"total_max_attempts": 1, "mode": "standard"},
        "proxies": {},
        "proxies_config": {},
        "ignore_configured_endpoint_urls": True,
        "endpoint_discovery_enabled": False,
        "use_fips_endpoint": False,
        "use_dualstack_endpoint": False,
        "defaults_mode": "legacy",
        "parameter_validation": True,
        "inject_host_prefix": False,
    }


def _validate_client(client, settings):
    from scripts import jev_rag_smoke_live_adapter as adapter

    meta = getattr(client, "meta", None)
    config = getattr(meta, "config", None)
    retries = getattr(config, "retries", None)
    adapter.require(
        getattr(meta, "endpoint_url", None) == ENDPOINT
        and getattr(config, "region_name", None) == REGION
        and getattr(config, "connect_timeout", None) == settings["connect_seconds"]
        and getattr(config, "read_timeout", None) == settings["read_seconds"]
        and type(retries) is dict
        and type(retries.get("total_max_attempts")) is int
        and retries == {"total_max_attempts": 1, "mode": "standard"}
        and callable(getattr(client, "invoke", None))
        and callable(getattr(client, "close", None))
        and callable(getattr(getattr(meta, "events", None), "register", None)),
        "CLIENT_CONFIG_INVALID",
    )


def _close_rejected(client):
    # Called only while an existing construction/validation error is escaping.
    # Secondary cleanup defects cannot replace its original traceback.
    try:
        if client is not None and callable(getattr(client, "close", None)):
            client.close()
    except BaseException:
        pass


class _Factory:
    __slots__ = ("_settings", "_key", "_secret", "_token", "_loader", "_lock", "_used")

    def __init__(self, settings, key, secret, token, loader):
        self._settings = dict(settings)
        self._key, self._secret, self._token = key, secret, token
        self._loader = loader
        self._lock = Lock()
        self._used = False

    def __repr__(self):
        return "LambdaClientFactory(single_use=True)"

    def __call__(self):
        from scripts import jev_rag_smoke_live_adapter as adapter

        with self._lock:
            adapter.require(not self._used, "PARENT_ALREADY_ATTEMPTED")
            self._used = True
        # Refusal-only access, after the one-use claim and before SDK loading.
        # Conservative even under -E: never configure a TLS key-log sink here.
        import os

        adapter.require(not os.environ.get("SSLKEYLOGFILE"), "CLIENT_CONFIG_INVALID")
        sdk = self._loader()
        adapter.require(
            sdk.boto3_version == SDK_PIN and sdk.botocore_version == SDK_PIN,
            "CLIENT_CONFIG_INVALID",
        )
        client = None
        try:
            config = sdk.Config(**_config_args(self._settings))
            session = sdk.Session()
            client = session.create_client(
                "lambda",
                region_name=REGION,
                api_version="2015-03-31",
                endpoint_url=ENDPOINT,
                use_ssl=True,
                verify=True,
                config=config,
                aws_access_key_id=self._key,
                aws_secret_access_key=self._secret,
                aws_session_token=self._token,
            )
            _validate_client(client, self._settings)
            return client
        except sdk.expected_errors:
            _close_rejected(client)
            raise adapter.AdapterError("CLIENT_CONFIG_INVALID") from None
        except BaseException:
            _close_rejected(client)
            raise


def prepare(settings, *, access_key_id, secret_access_key, session_token=None):
    """Return a zero-argument, one-use callable; no I/O or SDK imports here.

    Static material is kept only in memory, including an explicitly supplied
    session token. No loader, credential source, target discovery or live CLI.
    """
    if not (
        type(settings) is dict
        and set(settings) == {"max_attempts", "connect_seconds", "read_seconds"}
        and type(settings["max_attempts"]) is int
        and settings["max_attempts"] == 1
        and all(
            type(settings[k]) is int and 1 <= settings[k] <= 120
            for k in ("connect_seconds", "read_seconds")
        )
        and _valid_signing(access_key_id)
        and _valid_signing(secret_access_key)
        and (session_token is None or _valid_signing(session_token))
    ):
        raise FactoryError() from None
    return _Factory(
        settings, access_key_id, secret_access_key, session_token, _load_sdk
    )
