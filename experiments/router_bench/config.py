"""Frozen parameters of the router benchmark (docs/experiments/router-benchmark-design.md v2)."""

DATASET_VERSION = "v2"

# TypeSafe Jev. Only the official endpoint; the model is pinned (jev-latest / jev-preview can move).
JEV_MODEL = "jev-1.13.0"
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_CONNECT_TIMEOUT_S = 2.0
JEV_READ_TIMEOUT_S = 5.0
JEV_PRICE_PER_MTOK_INPUT = 0.042  # documented; output documented as free
JEV_MAX_TOKENS_PER_REQUEST = 64_000  # documented request limit: the worst-case reservation
JEV_EXPECTED_INPUT_TOKENS = 250  # ASSUMPTION (150-250); checked by the verification calls
JEV_MIN_SECONDS_BETWEEN_CALLS = 1.0  # at most 60 requests/min (documented limit 1,200/min)

# Haiku 4.5 router on Bedrock (RouterAgent, unchanged).
HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
HAIKU_EXPECTED_TOKENS = (214, 52)  # measured per call in baseline run 6a13ffb1
# Worst-case reservation per call. ASSUMPTION: RouterAgent sets no maxTokens (app unchanged),
# so output is not hard-capped by us; 1,000 output tokens is ~19x the measured mean. A call
# that exceeds its reservation stops the run (see runner).
HAIKU_WORST_CASE_TOKENS = (2_000, 1_000)

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
DEFAULT_COST_CAPS = {"bedrock": 0.50, "typesafe": 0.05, "total": 1.00}

# Which provider each router calls (None: local, free).
ROUTER_PROVIDERS = {"haiku": "bedrock", "rules": None, "jev": "typesafe"}
ALL_ROUTERS = ("haiku", "rules", "jev")

# Jev verification (design §7): exactly these cases, in this order.
VERIFICATION_CASE_IDS = ("L01", "L12")
VERIFICATION_COST_CAP = 0.01
