"""Offline guard for pytest: no real AWS credentials and no AWS network I/O.

The repository-root conftest.py installs it when pytest starts, before any test
module (and so any `app.*` or `eval.*` module) is imported, whichever directory,
file or test id pytest is given. Importing the `tests` package installs it too,
so the offline suite stays guarded even if that conftest is bypassed.

While installed it:
- forces fake AWS credentials and test configuration, removes other credential
  sources (profiles, session and bearer tokens, container and web-identity
  credentials) and points the shared credentials/config files at a path that
  does not exist;
- disables `.env` loading (python-dotenv honours PYTHON_DOTENV_DISABLED), so the
  `load_dotenv()` calls in application and eval modules cannot pick up real
  credentials;
- replaces botocore's HTTP transport with one that records the URL and raises
  NetworkBlockedError, so no request can leave the process.

Only the root conftest lifts it, and only for an explicitly authorized live run
(`pytest --run-live-eval`).
"""
import os

import botocore.httpsession

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
    "ENABLE_EVALUATE_ENDPOINT",
    "EVALUATE_ENDPOINT_TOKEN",
)

_ORIGINAL_SEND = botocore.httpsession.URLLib3Session.send
_saved_env: dict[str, str | None] | None = None

# URLs of every AWS request intercepted in this process (reported at session end).
blocked_requests: list[str] = []


class NetworkBlockedError(RuntimeError):
    """Raised instead of sending a request to AWS while the offline guard is installed."""


def _blocked_send(self, request):
    blocked_requests.append(request.url)
    raise NetworkBlockedError(f"Live AWS call attempted in unit tests: {request.url}")


def install() -> None:
    """Force the offline environment and block the transport. Idempotent."""
    global _saved_env
    if _saved_env is None:
        _saved_env = {name: os.environ.get(name) for name in (*FORCED_ENV, *REMOVED_ENV)}
    os.environ.update(FORCED_ENV)
    for name in REMOVED_ENV:
        os.environ.pop(name, None)
    botocore.httpsession.URLLib3Session.send = _blocked_send


def is_installed() -> bool:
    return botocore.httpsession.URLLib3Session.send is _blocked_send


def lift() -> None:
    """Restore the original environment and transport. Authorized live runs only."""
    global _saved_env
    if _saved_env is not None:
        for name, value in _saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        _saved_env = None
    botocore.httpsession.URLLib3Session.send = _ORIGINAL_SEND
