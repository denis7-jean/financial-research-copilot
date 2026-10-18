"""Guards for the unit-test harness itself."""
import os

import boto3
import pytest

from tests.conftest import NetworkBlockedError


def test_real_boto3_calls_are_blocked():
    client = boto3.client("s3", region_name="us-east-1")
    with pytest.raises(NetworkBlockedError):
        client.list_buckets()


def test_bedrock_runtime_calls_are_blocked():
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    with pytest.raises(NetworkBlockedError):
        client.converse(modelId="m", messages=[{"role": "user", "content": [{"text": "hi"}]}])


def test_fake_credentials_override_dotenv():
    assert os.environ["AWS_ACCESS_KEY_ID"] == "unit-test-fake-key"
