"""Unit-test harness: guarantees no live AWS calls.

This module runs before any `app.*` import. It forces fake AWS credentials (so
`load_dotenv()` cannot pick up real ones from `.env`, because python-dotenv never
overrides variables that are already set) and replaces botocore's HTTP transport
with a function that raises. Any test that forgets to mock a client fails loudly
instead of reaching AWS.
"""
import io
import json
import os

_FORCED_ENV = {
    "AWS_ACCESS_KEY_ID": "unit-test-fake-key",
    "AWS_SECRET_ACCESS_KEY": "unit-test-fake-secret",
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_MAX_ATTEMPTS": "1",
    "BEDROCK_MODEL_ID": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "JUDGE_MODEL_ID": "us.anthropic.claude-sonnet-4-6",
    "S3_BUCKET_NAME": "unit-test-bucket",
    "FAISS_INDEX_S3_KEY": "index/unit-test.faiss",
    "FAISS_META_S3_KEY": "index/unit-test.json",
    "COPILOT_CW_REQUEST_LOG": "false",
}
os.environ.update(_FORCED_ENV)
for _name in ("AWS_SESSION_TOKEN", "AWS_PROFILE", "ENABLE_EVALUATE_ENDPOINT", "EVALUATE_ENDPOINT_TOKEN"):
    os.environ.pop(_name, None)

import botocore.httpsession  # noqa: E402
import pytest  # noqa: E402


class NetworkBlockedError(RuntimeError):
    pass


def _blocked_send(self, request):
    raise NetworkBlockedError(f"Live AWS call attempted in unit tests: {request.url}")


botocore.httpsession.URLLib3Session.send = _blocked_send

from app import observability  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_process_state():
    observability.reset_cold_start()
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
