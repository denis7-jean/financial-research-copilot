"""Unit-test fixtures and fakes.

The offline guard (fake credentials, no `.env`, blocked botocore transport) is
installed by the repository-root conftest.py and by importing the `tests`
package; see tests/offline_guard.py. Any test that forgets to mock a client
fails loudly with NetworkBlockedError instead of reaching AWS.
"""
import io
import json
from contextlib import contextmanager

import pytest

from tests.offline_guard import NetworkBlockedError  # noqa: F401  (re-exported for tests)
from tests import offline_guard

from app import observability


@contextmanager
def isolated_blocked_requests():
    """Give each test its own attempt log, retaining every entry for the summary."""
    session_attempts = offline_guard.blocked_requests
    test_attempts = []
    offline_guard.blocked_requests = test_attempts
    try:
        yield
    finally:
        session_attempts.extend(test_attempts)
        offline_guard.blocked_requests = session_attempts


@pytest.fixture(autouse=True)
def _fresh_process_state():
    observability.reset_cold_start()
    with isolated_blocked_requests():
        yield


class FakeBedrock:
    """Stand-in for a boto3 bedrock-runtime client.

    Queue responses (dicts) or exceptions; each converse()/invoke_model() call
    pops the next one. Calls are recorded for assertions.
    """

    def __init__(self, converse_responses=None, invoke_responses=None):
        self.converse_responses = list(converse_responses or [])
        self.invoke_responses = list(invoke_responses or [])
        self.converse_calls: list[dict] = []
        self.invoke_calls: list[dict] = []

    def converse(self, **kwargs):
        self.converse_calls.append(kwargs)
        item = self.converse_responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def invoke_model(self, **kwargs):
        self.invoke_calls.append(kwargs)
        item = self.invoke_responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return {"body": io.BytesIO(json.dumps(item).encode("utf-8"))}


def converse_text(text: str, input_tokens: int = 100, output_tokens: int = 20, latency_ms: int = 250) -> dict:
    """Build a Bedrock Converse response shaped like the real API."""
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "usage": {"inputTokens": input_tokens, "outputTokens": output_tokens, "totalTokens": input_tokens + output_tokens},
        "metrics": {"latencyMs": latency_ms},
        "stopReason": "end_turn",
    }


# The production AccessDenied text, plus an ARN/account ID to prove they never leak.
ACCESS_DENIED_MESSAGE = (
    "Your account is currently being verified. Verification normally takes less than 2 hours. "
    "Until your account is verified, you may not have access to this operation. "
    "Caller: arn:aws:iam::123456789012:role/financial-copilot-lambda-role"
)


def aws_error(code: str, message: str = "", operation: str = "Converse", status: int = 400):
    """A real botocore ClientError, as boto3 raises it."""
    from botocore.exceptions import ClientError

    return ClientError(
        {"Error": {"Code": code, "Message": message}, "ResponseMetadata": {"HTTPStatusCode": status}},
        operation,
    )
