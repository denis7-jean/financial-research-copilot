"""Safety primitives: live authorization, secrets, budgets, downstream tripwire, artifact checks.

Lessons from docs/incidents/2026-09-28-unguarded-live-eval-test-run.md:
- Offline by default: a real client can be built only with a LiveAuthorization,
  created by the CLI from explicit --live flags. Nothing else creates one.
- Independent budgets: a request-count cap and an estimated-cost cap per
  provider, plus a total cost cap, all checked before every call.
- Secrets never leave memory: SecretValue redacts itself, and every artifact
  and outgoing payload is scanned for registered secret values.
"""
import json
import os
import sys
from dataclasses import dataclass, field

PROVIDERS = ("bedrock", "typesafe")


class LiveCallNotAuthorized(RuntimeError):
    """A real (billable) client was requested without a LiveAuthorization for its provider."""


class BudgetExhausted(RuntimeError):
    """A request-count or cost cap would be exceeded by the next call."""


class DownstreamCalled(RuntimeError):
    """Benchmark code touched QA, summarization or retrieval code."""


class ArtifactSafetyError(RuntimeError):
    """An artifact or outgoing payload would contain a secret, headers or document text."""


# --- Live authorization ------------------------------------------------------------------------

class LiveAuthorization:
    """Explicit, per-provider permission for billable calls. Built only by the CLI (--live)."""

    def __init__(self, providers, *, allow_under_pytest: bool = False):
        providers = frozenset(providers)
        unknown = providers - set(PROVIDERS)
        if unknown:
            raise ValueError(f"unknown provider(s): {sorted(unknown)}")
        if not providers:
            raise ValueError("a LiveAuthorization needs at least one provider")
        if "PYTEST_CURRENT_TEST" in os.environ and not allow_under_pytest:
            raise LiveCallNotAuthorized("live calls are never authorized inside pytest")
        self.providers = providers

    def allows(self, provider: str) -> bool:
        return provider in self.providers

    def require(self, provider: str) -> None:
        if not self.allows(provider):
            raise LiveCallNotAuthorized(f"no live authorization for {provider}")

    def __repr__(self) -> str:
        return f"LiveAuthorization({sorted(self.providers)})"


def require_live(authorization: "LiveAuthorization | None", provider: str) -> None:
    if authorization is None:
        raise LiveCallNotAuthorized(f"no live authorization for {provider} (dry run is the default)")
    authorization.require(provider)


class OfflineFakeClient:
    """Marker base class for explicitly controlled offline fakes of a provider client.

    Dependency injection is allowed only for instances of this class (Bedrock) or an
    httpx.MockTransport (TypeSafe). Anything else injected is treated as a real client
    and needs a LiveAuthorization, so injection cannot bypass the live opt-in.
    """


def require_offline_fake(client, provider: str) -> None:
    from botocore.client import BaseClient

    if isinstance(client, BaseClient) or not isinstance(client, OfflineFakeClient):
        raise LiveCallNotAuthorized(
            f"{provider}: an injected client must be an OfflineFakeClient; real clients are built only "
            "by the benchmark itself, behind a LiveAuthorization")


# --- Secrets -------------------------------------------------------------------------------------

_REGISTERED_SECRETS: list[str] = []


class SecretValue:
    """Holds a credential. repr/str are redacted; the value is registered for leak scans."""

    __slots__ = ("_value",)

    def __init__(self, value: str):
        if not value:
            raise ValueError("empty secret")
        self._value = value
        if value not in _REGISTERED_SECRETS:
            _REGISTERED_SECRETS.append(value)

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SecretValue([REDACTED])"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("SecretValue cannot be serialized")


def contains_registered_secret(text: str) -> bool:
    return any(secret in text for secret in _REGISTERED_SECRETS)


# --- Budgets -------------------------------------------------------------------------------------

@dataclass
class Reservation:
    provider: str
    amount_usd: float
    settled: bool = False


@dataclass
class _Account:
    max_requests: int | None
    max_cost_usd: float
    requests: int = 0
    committed_usd: float = 0.0
    reserved_usd: float = 0.0
    worst_case_charges: int = 0
    reservations_exceeded: int = 0


@dataclass
class Ledger:
    """Per-provider request and cost caps plus a total cost cap.

    Accounting uses a temporary per-call reservation: before a call, its worst-case
    cost is reserved and the request counted; after it, the reservation is replaced
    by the cost of the recorded usage (or kept at worst case when usage is unknown,
    e.g. a failed call). So the caps bound committed spend plus at most one
    outstanding worst-case reservation. The theoretical "every call at worst case"
    total is informational only and never blocks a plan.
    """

    request_caps: dict[str, int]
    cost_caps: dict[str, float]
    accounts: dict[str, _Account] = field(init=False)

    def __post_init__(self):
        self.accounts = {p: _Account(self.request_caps.get(p), self.cost_caps[p]) for p in PROVIDERS}
        self.total_cap = self.cost_caps["total"]

    def _total_exposure(self) -> float:
        return sum(a.committed_usd + a.reserved_usd for a in self.accounts.values())

    def reserve(self, provider: str, worst_case_usd: float) -> Reservation:
        account = self.accounts[provider]
        if account.max_requests is not None and account.requests >= account.max_requests:
            raise BudgetExhausted(f"{provider}: request cap {account.max_requests} reached")
        if account.committed_usd + account.reserved_usd + worst_case_usd > account.max_cost_usd + 1e-12:
            raise BudgetExhausted(f"{provider}: cost cap ${account.max_cost_usd:.4f} would be exceeded "
                                  f"(committed ${account.committed_usd:.6f} + worst case ${worst_case_usd:.6f})")
        if self._total_exposure() + worst_case_usd > self.total_cap + 1e-12:
            raise BudgetExhausted(f"total cost cap ${self.total_cap:.4f} would be exceeded")
        account.requests += 1
        account.reserved_usd += worst_case_usd
        return Reservation(provider, worst_case_usd)

    def settle(self, reservation: Reservation, actual_usd: float | None) -> tuple[float, bool]:
        """Replace the reservation with the actual cost. Returns (charged, exceeded_reservation)."""
        if reservation.settled:
            raise RuntimeError("reservation already settled")
        account = self.accounts[reservation.provider]
        account.reserved_usd -= reservation.amount_usd
        if actual_usd is None:
            charged = reservation.amount_usd
            account.worst_case_charges += 1
        else:
            charged = actual_usd
        exceeded = actual_usd is not None and actual_usd > reservation.amount_usd + 1e-12
        account.reservations_exceeded += int(exceeded)
        account.committed_usd += charged
        reservation.settled = True
        return charged, exceeded

    def summary(self) -> dict:
        return {
            "providers": {p: {"requests": a.requests, "request_cap": a.max_requests,
                              "committed_usd": round(a.committed_usd, 6), "cost_cap_usd": a.max_cost_usd,
                              "outstanding_reservations_usd": round(a.reserved_usd, 6),
                              "charged_at_worst_case": a.worst_case_charges,
                              "reservations_exceeded": a.reservations_exceeded}
                          for p, a in self.accounts.items()},
            "total_committed_usd": round(sum(a.committed_usd for a in self.accounts.values()), 6),
            "total_cap_usd": self.total_cap,
        }


# --- Downstream tripwire -------------------------------------------------------------------------

DOWNSTREAM = {
    "app.agents.orchestrator": ("CopilotOrchestrator.process", "CopilotOrchestrator.process_direct"),
    "app.agents.qa_agent": ("QAAgent.run",),
    "app.agents.summarizer_agent": ("SummarizerAgent.run",),
    "app.services.retriever": ("retrieve_chunks", "embed_query", "_load_index_if_needed"),
    "app.services.bedrock_client": ("retrieve_and_generate",),
    "app.services.build_index": (),
}


class DownstreamTripwire:
    """Proves the benchmark touches no QA, summarization or retrieval code.

    Downstream modules not yet imported must stay unimported (then nothing in them
    can run). Modules already imported (e.g. by other tests) have their entry points
    replaced by functions that record the call and raise DownstreamCalled.
    """

    def __init__(self):
        self.calls: list[str] = []
        self._patched: list[tuple[object, str, object]] = []
        self._preloaded: set[str] = set()
        self.newly_imported: list[str] = []

    def _tripwire(self, name: str):
        def fire(*args, **kwargs):
            self.calls.append(name)
            raise DownstreamCalled(f"downstream code called during the router benchmark: {name}")
        return fire

    def __enter__(self):
        self._preloaded = {m for m in DOWNSTREAM if m in sys.modules}
        for module_name in self._preloaded:
            module = sys.modules[module_name]
            for dotted in DOWNSTREAM[module_name]:
                owner_name, _, attr = dotted.rpartition(".")
                owner = getattr(module, owner_name) if owner_name else module
                self._patched.append((owner, attr, getattr(owner, attr)))
                setattr(owner, attr, self._tripwire(f"{module_name}.{dotted}"))
        return self

    def __exit__(self, *exc):
        for owner, attr, original in reversed(self._patched):
            setattr(owner, attr, original)
        self.newly_imported = sorted(m for m in DOWNSTREAM if m in sys.modules and m not in self._preloaded)
        return False

    def report(self) -> dict:
        return {
            "clean": not self.calls and not self.newly_imported,
            "downstream_calls": list(self.calls),
            "downstream_modules_imported_during_run": list(self.newly_imported),
            "downstream_modules_guarded": sorted(DOWNSTREAM),
        }


# --- Artifact and payload checks -----------------------------------------------------------------

FORBIDDEN_KEYS = frozenset({
    "authorization", "headers", "request_headers", "api_key", "apikey", "secret", "password",
    "retrieved_context", "retrieved_chunks", "chunks", "context", "documents", "source_text", "evidence_text",
})
MAX_STRING_CHARS = 600  # longer strings look like document text (chunks are ~1,500 chars)


def _walk(value, path="$"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key, None
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            yield from _walk(item, f"{path}[{i}]")
    else:
        yield path, None, value


def assert_safe_for_output(obj, *, what: str) -> str:
    """Serialize obj, refusing secrets, auth headers, forbidden keys and document-length text."""
    for path, key, leaf in _walk(obj):
        if key is not None and str(key).lower() in FORBIDDEN_KEYS:
            raise ArtifactSafetyError(f"{what}: forbidden key {key!r} at {path}")
        if isinstance(leaf, str) and len(leaf) > MAX_STRING_CHARS:
            raise ArtifactSafetyError(f"{what}: string of {len(leaf)} chars at {path} (document text?)")
    text = json.dumps(obj, sort_keys=True, default=str)
    if contains_registered_secret(text):
        raise ArtifactSafetyError(f"{what}: contains a registered secret value")
    if "bearer " in text.lower():
        raise ArtifactSafetyError(f"{what}: contains an authorization header value")
    return text
