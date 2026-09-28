"""Structured, sanitized failure information.

Separates infrastructure and model-invocation failures, which must surface as
HTTP errors, from legitimate outcomes such as an empty retrieval or an
evidence-based "not in the documents" answer, which remain HTTP 200.

Public responses carry only the stage, kind, error code and a retryable flag.
Raw provider messages can contain ARNs or account IDs, so they are sanitized
and kept for logs only.
"""
import re

HTTP_STATUS = {
    "access_denied": 503,
    "throttled": 503,
    "unavailable": 503,
    "timeout": 504,
    "model_error": 502,
    "invalid_model_output": 502,
    "configuration": 500,
    "internal": 500,
}

_RETRYABLE = frozenset({"throttled", "unavailable", "timeout", "model_error", "invalid_model_output"})

_PUBLIC_MESSAGES = {
    "access_denied": "An upstream AI or storage service denied access",
    "throttled": "An upstream AI or storage service is throttling requests",
    "unavailable": "An upstream AI or storage service is unavailable",
    "timeout": "An upstream AI or storage service timed out",
    "model_error": "The model failed to process the request",
    "invalid_model_output": "The model returned an unusable response",
    "configuration": "The service is misconfigured",
    "internal": "Internal error",
}

_CODE_KINDS = {
    **dict.fromkeys((
        "AccessDeniedException", "AccessDenied", "UnauthorizedException", "UnrecognizedClientException",
        "InvalidSignatureException", "ExpiredTokenException", "ExpiredToken", "InvalidAccessKeyId",
        "SignatureDoesNotMatch", "InvalidClientTokenId", "AllAccessDisabled",
    ), "access_denied"),
    **dict.fromkeys((
        "ThrottlingException", "TooManyRequestsException", "ServiceQuotaExceededException", "SlowDown",
        "RequestLimitExceeded", "ProvisionedThroughputExceededException",
    ), "throttled"),
    **dict.fromkeys((
        "ServiceUnavailableException", "ServiceUnavailable", "InternalServerException", "InternalFailure",
        "InternalError", "ModelNotReadyException",
    ), "unavailable"),
    **dict.fromkeys(("ModelErrorException", "ModelStreamErrorException"), "model_error"),
    "ModelTimeoutException": "timeout",
    **dict.fromkeys(("ValidationException", "ResourceNotFoundException", "NoSuchKey", "NoSuchBucket"),
                    "configuration"),
}

_ARN = re.compile(r"arn:aws[a-z-]*:[^\s\"',)]+")
_ACCOUNT_ID = re.compile(r"(?<!\d)\d{12}(?!\d)")
_ACCESS_KEY = re.compile(r"\b(?:AKIA|ASIA|A3T[A-Z0-9])[A-Z0-9]{12,}\b")


def sanitize_message(text: str, limit: int = 200) -> str:
    text = _ARN.sub("<arn>", str(text))
    text = _ACCESS_KEY.sub("<access-key>", text)
    text = _ACCOUNT_ID.sub("<account>", text)
    return text[:limit]


class ServiceFailure(Exception):
    """An infrastructure or model-invocation failure. Never an empty result."""

    def __init__(self, stage: str, kind: str, code: str | None = None, detail: str = ""):
        self.stage = stage
        self.kind = kind if kind in HTTP_STATUS else "internal"
        self.code = code
        self.retryable = self.kind in _RETRYABLE
        self.detail = sanitize_message(detail)
        super().__init__(f"{self.kind} at {stage}")

    @property
    def http_status(self) -> int:
        return HTTP_STATUS[self.kind]

    def public_message(self) -> str:
        return f"{_PUBLIC_MESSAGES[self.kind]} (stage: {self.stage})"

    def to_public(self) -> dict:
        return {"stage": self.stage, "kind": self.kind, "code": self.code, "retryable": self.retryable}

    def to_log(self) -> dict:
        return {**self.to_public(), "detail": self.detail}


def classify(exc: BaseException) -> tuple[str | None, str | None]:
    """Map a botocore/network exception to (kind, code). (None, None) if unknown."""
    from botocore.exceptions import (
        ClientError,
        ConnectionClosedError,
        ConnectTimeoutError,
        EndpointConnectionError,
        NoCredentialsError,
        PartialCredentialsError,
        ReadTimeoutError,
    )

    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code")
        kind = _CODE_KINDS.get(code)
        if kind is None:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") or 0
            kind = "unavailable" if status >= 500 else "internal"
        return kind, code
    if isinstance(exc, (ReadTimeoutError, ConnectTimeoutError)):
        return "timeout", type(exc).__name__
    if isinstance(exc, (EndpointConnectionError, ConnectionClosedError)):
        return "unavailable", type(exc).__name__
    if isinstance(exc, (NoCredentialsError, PartialCredentialsError)):
        return "access_denied", type(exc).__name__
    return None, None


def failure_from(stage: str, exc: BaseException, default_kind: str = "internal") -> ServiceFailure:
    if isinstance(exc, ServiceFailure):
        return exc
    kind, code = classify(exc)
    return ServiceFailure(stage, kind or default_kind, code or type(exc).__name__, str(exc))


def http_status_for(result: dict) -> int:
    """HTTP status for an orchestrator result dict."""
    if "error" not in result:
        return 200
    detail = result.get("error_detail") or {}
    return HTTP_STATUS.get(detail.get("kind"), 500)
