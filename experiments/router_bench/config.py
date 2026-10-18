"""Frozen parameters of the router benchmark (docs/experiments/router-benchmark-design.md v2)."""

DATASET_VERSION = "v2"

# TypeSafe Jev. Only the official endpoint; the model is pinned (jev-latest / jev-preview can move).
JEV_MODEL = "jev-1.13.0"
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_CONNECT_TIMEOUT_S = 2.0
JEV_READ_TIMEOUT_S = 5.0
JEV_PRICE_PER_MTOK_INPUT = 0.042  # documented; output documented as free
JEV_MAX_TOKENS_PER_REQUEST = 64_000  # documented request limit: the worst-case reservation
# Calibrated from the live verification (eval/results/experiments/2026-09-28-jev-verification/):
# reported input tokens were 410 (L01) and 408 (L12), ~2.4x a bytes/4 estimate of the request, so
# TypeSafe adds its own overhead. Output tokens were reported (33, 35) but are documented as free.
JEV_EXPECTED_INPUT_TOKENS = 410  # the larger observed value
JEV_OBSERVED_OUTPUT_TOKENS = 35  # reported, not priced (documented free; not verified against a bill)
JEV_MIN_SECONDS_BETWEEN_CALLS = 1.0  # at most 60 requests/min (documented limit 1,200/min)

# Haiku 4.5 router on Bedrock (RouterAgent, unchanged).
HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
HAIKU_EXPECTED_TOKENS = (214, 52)  # measured per call in baseline run 6a13ffb1
# Bounds on one routing call. Input: RouterAgent's prompt (~150 tokens) plus one approved
# question (<= 300 chars) is < 500 tokens. Output: RouterAgent sets no maxTokens (production
# behavior, deliberately unchanged), so the only bound is the model's own output limit.
HAIKU_MAX_INPUT_TOKENS = 2_000
HAIKU_MAX_OUTPUT_TOKENS = 64_000  # ASSUMPTION: Claude Haiku 4.5's documented maximum output (not verified offline)
# Per-call reservation modes (see docs/experiments/router-benchmark-design.md §13):
#   strict    reserves the maximum possible call, so committed spend never exceeds a cap;
#   practical reserves ~19x the measured mean output, so one call may overshoot a cap by up to
#             (maximum possible call - reservation), after which the run stops.
HAIKU_RESERVATIONS = {"strict": (HAIKU_MAX_INPUT_TOKENS, HAIKU_MAX_OUTPUT_TOKENS),
                      "practical": (HAIKU_MAX_INPUT_TOKENS, 1_000)}
DEFAULT_HAIKU_RESERVATION = "strict"
# Failed Haiku calls (RouterAgent records the error code). Cost is 0 only when the request cannot
# have been processed; anything else is charged the full reservation.
HAIKU_NOT_SENT_CODES = frozenset({"EndpointConnectionError", "ConnectTimeoutError", "NetworkBlockedError",
                                  "NoCredentialsError", "PartialCredentialsError"})
# ASSUMPTION: Bedrock does not bill requests it rejects before inference with these codes.
HAIKU_REJECTED_CODES = frozenset({"ThrottlingException", "TooManyRequestsException", "ServiceQuotaExceededException",
                                  "AccessDeniedException", "UnrecognizedClientException", "ExpiredTokenException",
                                  "ValidationException", "ResourceNotFoundException", "ServiceUnavailableException"})

# Production-equivalent final-decision rule (RouterAgent): no raw label or score < 0.6 -> qa.
FINAL_DECISION_THRESHOLD = 0.6
FALLBACK_ROUTE = "qa"

DEFAULT_REPETITIONS = 10
MIN_REPETITIONS = 6
WARMUP_CALLS = 3
DEFAULT_SEED = 20260928
BOOTSTRAP_DRAWS = 10_000
CONSECUTIVE_INFRA_ERROR_LIMIT = 3
INFRA_ERROR_RATE_LIMIT = 0.01

# Hard ceilings (USD, estimated from recorded usage; worst case when usage is unknown).
# Bedrock $0.60 is PROPOSED (2026-09-28) for strict mode, which reserves $0.322 per Haiku call:
# at $0.50 the headroom was only $0.0154. It is pending final approval. TypeSafe and total unchanged.
DEFAULT_COST_CAPS = {"bedrock": 0.60, "typesafe": 0.05, "total": 1.00}
COST_CAPS_STATUS = "Bedrock $0.60 proposed 2026-09-28, pending final approval; TypeSafe $0.05 and total $1.00 unchanged"

# Which provider each router calls (None: local, free).
ROUTER_PROVIDERS = {"haiku": "bedrock", "rules": None, "jev": "typesafe"}
ALL_ROUTERS = ("haiku", "rules", "jev")

# Jev verification (design §7): exactly these cases, in this order.
VERIFICATION_CASE_IDS = ("L01", "L12")
VERIFICATION_COST_CAP = 0.01
