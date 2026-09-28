"""Unit tests for failure classification and sanitization (app/errors.py)."""
import pytest
from botocore.exceptions import (
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    ReadTimeoutError,
)

from app.errors import HTTP_STATUS, ServiceFailure, classify, failure_from, http_status_for, sanitize_message
from tests.conftest import ACCESS_DENIED_MESSAGE, aws_error

URL = "https://bedrock-runtime.us-east-1.amazonaws.com"


@pytest.mark.parametrize("exc, kind", [
    (aws_error("AccessDeniedException"), "access_denied"),
    (aws_error("AccessDenied", operation="GetObject", status=403), "access_denied"),
    (aws_error("UnrecognizedClientException"), "access_denied"),
    (aws_error("ExpiredTokenException"), "access_denied"),
    (aws_error("ThrottlingException"), "throttled"),
    (aws_error("ServiceQuotaExceededException"), "throttled"),
    (aws_error("ServiceUnavailableException", status=503), "unavailable"),
    (aws_error("InternalServerException", status=500), "unavailable"),
    (aws_error("ModelNotReadyException"), "unavailable"),
    (aws_error("ModelErrorException"), "model_error"),
    (aws_error("ModelTimeoutException", status=408), "timeout"),
    (aws_error("ValidationException"), "configuration"),
    (aws_error("ResourceNotFoundException", status=404), "configuration"),
    (aws_error("NoSuchKey", operation="GetObject", status=404), "configuration"),
    (aws_error("BrandNewServerError", status=502), "unavailable"),
    (aws_error("BrandNewClientError", status=400), "internal"),
    (ReadTimeoutError(endpoint_url=URL), "timeout"),
    (ConnectTimeoutError(endpoint_url=URL), "timeout"),
    (EndpointConnectionError(endpoint_url=URL), "unavailable"),
    (NoCredentialsError(), "access_denied"),
])
def test_classify(exc, kind):
    assert classify(exc)[0] == kind


def test_classify_unknown_exception():
    assert classify(ValueError("x")) == (None, None)


def test_failure_from_uses_default_kind_and_class_name():
    failure = failure_from("qa", ValueError("bad"))
    assert (failure.kind, failure.code) == ("internal", "ValueError")


def test_failure_from_passes_existing_failures_through():
    original = ServiceFailure("retrieval.embed", "throttled", "ThrottlingException")
    assert failure_from("qa", original) is original


def test_sanitize_removes_arns_account_ids_and_access_keys():
    text = sanitize_message(ACCESS_DENIED_MESSAGE + " key AKIAABCDEFGHIJKLMNOP account 210987654321", limit=1000)
    for secret in ("arn:aws", "123456789012", "210987654321", "AKIAABCDEFGHIJKLMNOP"):
        assert secret not in text
    assert "<arn>" in text and "<access-key>" in text and "<account>" in text


def test_sanitize_truncates():
    assert len(sanitize_message("x" * 1000)) == 200


def test_public_view_never_contains_the_raw_message():
    failure = failure_from("retrieval.embed", aws_error("AccessDeniedException", ACCESS_DENIED_MESSAGE))
    assert failure.to_public() == {"stage": "retrieval.embed", "kind": "access_denied",
                                   "code": "AccessDeniedException", "retryable": False}
    assert "verified" not in failure.public_message()
    assert "retrieval.embed" in failure.public_message()
    assert "verified" in failure.to_log()["detail"]  # kept, sanitized, for logs
    assert "123456789012" not in failure.to_log()["detail"]
    assert str(failure) == "access_denied at retrieval.embed"


def test_unknown_kind_is_coerced_to_internal():
    assert ServiceFailure("x", "made_up").kind == "internal"


@pytest.mark.parametrize("result, status", [
    ({"task_type": "qa", "result": {}}, 200),
    ({"error": "e", "error_detail": {"kind": "access_denied"}}, 503),
    ({"error": "e", "error_detail": {"kind": "timeout"}}, 504),
    ({"error": "e", "error_detail": {"kind": "invalid_model_output"}}, 502),
    ({"error": "e"}, 500),
])
def test_http_status_for(result, status):
    assert http_status_for(result) == status


def test_every_kind_has_a_5xx_status():
    assert all(500 <= status <= 599 for status in HTTP_STATUS.values())
