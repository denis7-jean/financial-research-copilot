"""Crash-resistant, sanitized persistence for benchmark and verification runs.

The journal is a JSON-lines file written as the run proceeds: one line per event,
flushed and fsynced before the run continues, so completed paid calls survive a
crash, an interrupt or a later failure (metrics, artifact validation).

- run_started: plan fingerprints, caps and provenance.
- call_started: written before every paid call, after its budget reservation. A
  call_started without a matching record means the call may have been billed.
- record: the sanitized RouteRecord. If a record fails the artifact safety check,
  a minimal diagnostic record (typed, allowlisted fields only) is written instead.
- run_stopped / run_interrupted / run_finished: why and where the run ended, with
  the ledger.

Every line passes safety.assert_safe_for_output; nothing is ever overwritten.
"""
import json
import os
import re

from experiments.router_bench.safety import ArtifactSafetyError, assert_safe_for_output

JOURNAL_SUFFIX = ".journal.jsonl"
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_:.-]{1,64}$")


def _token(value) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) and _SAFE_TOKEN.match(value) else "<redacted>"


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def minimal_record(record: dict, reason: str) -> dict:
    """Typed, allowlisted fields of a record that failed the safety check. Never raises."""
    return {
        "type": "record", "redacted": True, "reason": _token(reason),
        "router": _token(record.get("router")), "case_id": _token(record.get("case_id")),
        "repetition": _number(record.get("repetition")), "warmup": bool(record.get("warmup")),
        "outcome": _token(record.get("outcome")), "final_label": _token(record.get("final_label")),
        "raw_label": _token(record.get("raw_label")), "infra_error": bool(record.get("infra_error")),
        "http_status": _number(record.get("http_status")), "latency_ms": _number(record.get("latency_ms")),
        "input_tokens": _number(record.get("input_tokens")), "output_tokens": _number(record.get("output_tokens")),
        "cost_usd": _number(record.get("cost_usd")), "cost_basis": _token(record.get("cost_basis")),
    }


class RunJournal:
    def __init__(self, path: str):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.path = path
        self._file = open(path, "x", encoding="utf-8", newline="\n")  # "x": never overwrite evidence
        self.lines = 0
        self.redacted_records = 0

    def _write(self, entry: dict) -> None:
        self._file.write(json.dumps(entry, sort_keys=True) + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())
        self.lines += 1

    def event(self, event_type: str, /, **fields) -> None:
        entry = {**fields, "type": event_type}
        try:
            assert_safe_for_output(entry, what=f"journal {event_type}")
        except ArtifactSafetyError as exc:
            entry = {"type": event_type, "redacted": True, "reason": exc.category}
        self._write(entry)

    def call_started(self, call, provider: str, reserved_usd: float) -> None:
        self.event("call_started", router=call.router, case_id=call.case_id, repetition=call.repetition,
                   warmup=call.warmup, provider=provider, reserved_usd=round(reserved_usd, 8))

    def record(self, record: dict) -> None:
        entry = {"type": "record", **record}
        try:
            assert_safe_for_output(entry, what="journal record")
        except ArtifactSafetyError as exc:
            self.redacted_records += 1
            entry = minimal_record(record, exc.category)
        self._write(entry)

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()


def read_journal(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
