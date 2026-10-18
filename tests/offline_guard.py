"""Offline guard for pytest: no real credentials and no outbound network I/O.

The repository-root conftest.py installs it when pytest starts, before any test
module (and so any `app.*` or `eval.*` module) is imported, whichever directory,
file or test id pytest is given. Importing the `tests` package installs it too,
so the offline suite stays guarded even if that conftest is bypassed.

While installed it:
- forces fake AWS credentials and test configuration, removes other credential
  sources (profiles, session and bearer tokens, container and web-identity
  credentials, the TypeSafe API key) and points the shared credentials/config
  files at a path that does not exist;
- disables `.env` loading (python-dotenv honours PYTHON_DOTENV_DISABLED), so the
  `load_dotenv()` calls in application and eval modules cannot pick up real
  credentials;
- replaces botocore's HTTP transport with one that records the URL and raises
  NetworkBlockedError;
- blocks every other outbound path to a non-loopback host, whatever the client
  library: httpx transports (sync and async), DNS lookups and socket connects.
  This keeps ordinary tests from ever contacting TypeSafe (api.typesafe.ai) or
  any other service. Loopback (localhost, 127.0.0.0/8, ::1) stays allowed.

Blocked attempts are recorded as scheme://host/path or socket:host:port, never
with headers or query strings, so credentials cannot leak into the record.

Only the root conftest lifts it, and only for an explicitly authorized live run
(`pytest --run-live-eval`).
"""
import ipaddress
import os
import socket

import botocore.httpsession
import httpx

_MISSING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_offline_guard_no_such_file")

FORCED_ENV = {
    "AWS_ACCESS_KEY_ID": "unit-test-fake-key",
    "AWS_SECRET_ACCESS_KEY": "unit-test-fake-secret",
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_MAX_ATTEMPTS": "1",
    "AWS_SHARED_CREDENTIALS_FILE": _MISSING_FILE,
    "AWS_CONFIG_FILE": _MISSING_FILE,
    "AWS_EC2_METADATA_DISABLED": "true",
    "PYTHON_DOTENV_DISABLED": "1",
    "BEDROCK_MODEL_ID": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "JUDGE_MODEL_ID": "us.anthropic.claude-sonnet-4-6",
    "S3_BUCKET_NAME": "unit-test-bucket",
    "FAISS_INDEX_S3_KEY": "index/unit-test.faiss",
    "FAISS_META_S3_KEY": "index/unit-test.json",
    "COPILOT_CW_REQUEST_LOG": "false",
}
REMOVED_ENV = (
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
    "AWS_BEARER_TOKEN_BEDROCK",
    "AWS_ROLE_ARN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN",
    "TYPESAFE_API_KEY",
    "ENABLE_EVALUATE_ENDPOINT",
    "EVALUATE_ENDPOINT_TOKEN",
)

_ORIGINALS = {
    (botocore.httpsession.URLLib3Session, "send"): botocore.httpsession.URLLib3Session.send,
    (httpx.HTTPTransport, "handle_request"): httpx.HTTPTransport.handle_request,
    (httpx.AsyncHTTPTransport, "handle_async_request"): httpx.AsyncHTTPTransport.handle_async_request,
    (socket.socket, "connect"): socket.socket.connect,
    (socket.socket, "connect_ex"): socket.socket.connect_ex,
    (socket, "getaddrinfo"): socket.getaddrinfo,
}
_saved_env: dict[str, str | None] | None = None

# Every outbound attempt intercepted in this process (reported at session end).
blocked_requests: list[str] = []


class NetworkBlockedError(RuntimeError):
    """Raised instead of any outbound network call while the offline guard is installed."""


def _is_loopback(host) -> bool:
    if host is None:
        return True  # passive lookup (bind), not a destination
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    host = str(host).strip("[]").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _block(target: str, message: str):
    blocked_requests.append(target)
    raise NetworkBlockedError(f"{message}: {target}")


def _blocked_botocore_send(self, request):
    _block(request.url.split("?", 1)[0], "Live AWS call attempted in unit tests")


def _url_target(request: httpx.Request) -> str:
    return f"{request.url.scheme}://{request.url.host}{request.url.path}"


def _guarded_httpx(self, request):
    if not _is_loopback(request.url.host):
        _block(_url_target(request), "Network call attempted in offline tests")
    return _ORIGINALS[(httpx.HTTPTransport, "handle_request")](self, request)


async def _guarded_httpx_async(self, request):
    if not _is_loopback(request.url.host):
        _block(_url_target(request), "Network call attempted in offline tests")
    return await _ORIGINALS[(httpx.AsyncHTTPTransport, "handle_async_request")](self, request)


def _socket_target(address) -> str | None:
    """socket:host:port for a non-loopback IP address; None for loopback or AF_UNIX."""
    if isinstance(address, tuple) and address and not _is_loopback(address[0]):
        return f"socket:{address[0]}:{address[1] if len(address) > 1 else ''}"
    return None


def _guarded_connect(self, address):
    target = _socket_target(address)
    if target:
        _block(target, "Network call attempted in offline tests")
    return _ORIGINALS[(socket.socket, "connect")](self, address)


def _guarded_connect_ex(self, address):
    target = _socket_target(address)
    if target:
        _block(target, "Network call attempted in offline tests")
    return _ORIGINALS[(socket.socket, "connect_ex")](self, address)


def _guarded_getaddrinfo(host, *args, **kwargs):
    if not _is_loopback(host):
        _block(f"dns:{host}", "DNS lookup attempted in offline tests")
    return _ORIGINALS[(socket, "getaddrinfo")](host, *args, **kwargs)


_REPLACEMENTS = {
    (botocore.httpsession.URLLib3Session, "send"): _blocked_botocore_send,
    (httpx.HTTPTransport, "handle_request"): _guarded_httpx,
    (httpx.AsyncHTTPTransport, "handle_async_request"): _guarded_httpx_async,
    (socket.socket, "connect"): _guarded_connect,
    (socket.socket, "connect_ex"): _guarded_connect_ex,
    (socket, "getaddrinfo"): _guarded_getaddrinfo,
}


def install() -> None:
    """Force the offline environment and block outbound network. Idempotent."""
    global _saved_env
    if _saved_env is None:
        _saved_env = {name: os.environ.get(name) for name in (*FORCED_ENV, *REMOVED_ENV)}
    os.environ.update(FORCED_ENV)
    for name in REMOVED_ENV:
        os.environ.pop(name, None)
    for (owner, attribute), replacement in _REPLACEMENTS.items():
        setattr(owner, attribute, replacement)


def is_installed() -> bool:
    return all(getattr(owner, attribute) is replacement for (owner, attribute), replacement in _REPLACEMENTS.items())


def lift() -> None:
    """Restore the original environment and network paths. Authorized live runs only."""
    global _saved_env
    if _saved_env is not None:
        for name, value in _saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        _saved_env = None
    for (owner, attribute), original in _ORIGINALS.items():
        setattr(owner, attribute, original)
