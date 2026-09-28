"""Crash-resistant persistence: journal, interrupts, unsafe records, artifact refusal. Offline only."""
import json

import httpx
import pytest

from eval.routing_datasets import routing_dataset
from experiments.router_bench import cli
from experiments.router_bench import metrics as bench_metrics
from experiments.router_bench.config import JEV_MODEL
from experiments.router_bench.payload import ApprovedQuestions
from experiments.router_bench.persistence import JOURNAL_SUFFIX, RunJournal, read_journal
from experiments.router_bench.routers import JevClient, JevRouter, RouteRecord, RulesRouter
from experiments.router_bench.runner import build_plan, run

V2 = routing_dataset("v2")


def _ok(request):
    return httpx.Response(200, json={
        "model": JEV_MODEL, "answers": {"route": {"choice": "qa", "probabilities": {"qa": 0.9, "summarize": 0.1},
                                                  "confidence": 0.8}},
        "usage": {"input_tokens": 180, "output_tokens": 1}})


def _jev(plan, handler=_ok):
    return JevRouter(JevClient(transport=httpx.MockTransport(handler)), ApprovedQuestions(V2, plan.allowed_ids))


def test_every_paid_call_is_announced_then_recorded(tmp_path):
    plan = build_plan(("rules", "jev"), 1, 1, 3, allowed_ids=["L01", "L12", "N01"])
    journal = RunJournal(str(tmp_path / "run.journal.jsonl"))
    result = run(plan, {"rules": RulesRouter(), "jev": _jev(plan)}, pace=False, journal=journal)
    journal.close()
    lines = read_journal(journal.path)
    types = [line["type"] for line in lines]
    assert types[0] == "run_started" and types[-1] == "run_finished"
    assert types.count("record") == result["executed_calls"] == 7  # 1 warm-up + 3 jev + 3 rules
    assert types.count("call_started") == 4  # paid (jev) calls only
    for i, line in enumerate(lines):
        if line["type"] == "record" and line["router"] == "jev":
            assert lines[i - 1]["type"] == "call_started" and lines[i - 1]["case_id"] == line["case_id"]


def test_an_interrupt_keeps_the_records_of_completed_paid_calls(tmp_path):
    class Interrupted(JevRouter):
        calls = 0

        def route(self, case):
            Interrupted.calls += 1
            if Interrupted.calls == 4:
                raise KeyboardInterrupt
            return super().route(case)

    plan = build_plan(("jev",), 1, 0, 3)
    base = _jev(plan)
    journal = RunJournal(str(tmp_path / "run.journal.jsonl"))
    with pytest.raises(KeyboardInterrupt):
        run(plan, {"jev": Interrupted(base.client, base.approved)}, pace=False, journal=journal)
    journal.close()
    lines = read_journal(journal.path)
    assert [line["type"] for line in lines].count("record") == 3
    assert [line["type"] for line in lines].count("call_started") == 4  # the 4th may have been billed
    last = lines[-1]
    assert last["type"] == "run_interrupted" and last["error_type"] == "KeyboardInterrupt"
    assert last["executed_calls"] == 3
    assert last["ledger"]["providers"]["typesafe"]["requests"] == 4
    assert last["ledger"]["providers"]["typesafe"]["outstanding_reservations_usd"] > 0


def test_an_unsafe_record_is_replaced_by_a_minimal_diagnostic(tmp_path):
    class Leaky(RulesRouter):
        def route(self, case):
            record = super().route(case)
            record.extra = {"note": "document text " * 100, "context": "chunk"}
            return record

    plan = build_plan(("rules",), 1, 0, 3, allowed_ids=["L01"])
    journal = RunJournal(str(tmp_path / "run.journal.jsonl"))
    run(plan, {"rules": Leaky()}, pace=False, journal=journal)
    journal.close()
    record = next(line for line in read_journal(journal.path) if line["type"] == "record")
    assert record["redacted"] is True and record["reason"] in {"forbidden_key", "document_length_text"}
    assert (record["router"], record["case_id"], record["final_label"], record["cost_usd"]) == ("rules", "L01", "qa", 0.0)
    assert "document text" not in json.dumps(record) and "chunk" not in json.dumps(record)
    assert journal.redacted_records == 1


def test_the_journal_never_overwrites_evidence(tmp_path):
    path = str(tmp_path / "run.journal.jsonl")
    RunJournal(path).close()
    with pytest.raises(FileExistsError):
        RunJournal(path)


def test_a_refused_artifact_leaves_a_minimal_diagnostic_and_the_journal(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bench_metrics, "compute", lambda *a, **k: {"note": "x" * 700})
    output = tmp_path / "bench.json"
    assert cli.main(["--repetitions", "1", "--output", str(output)]) == 3
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["artifact_rejected"] is True and artifact["rejection_category"] == "document_length_text"
    assert artifact["execution"]["executed_calls"] == artifact["execution"]["scheduled_calls"] == 108
    assert "records" not in artifact and "x" * 50 not in output.read_text(encoding="utf-8")
    journal = read_journal(str(output) + JOURNAL_SUFFIX)
    assert sum(line["type"] == "record" for line in journal) == 108
    assert "REFUSED by the safety check (document_length_text)" in capsys.readouterr().out


def test_a_metrics_failure_still_writes_the_records(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("bug")

    monkeypatch.setattr(bench_metrics, "compute", broken)
    output = tmp_path / "bench.json"
    assert cli.main(["--repetitions", "1", "--output", str(output)]) == 3
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["metrics"] == {"error": "metrics failed: ValueError"}
    assert len(artifact["records"]) == 108


def test_an_interrupted_cli_run_keeps_its_journal(tmp_path, monkeypatch):
    original = RulesRouter.route
    calls = {"n": 0}

    def interrupt_on_fifth(self, case):
        calls["n"] += 1
        if calls["n"] == 5:
            raise KeyboardInterrupt
        return original(self, case)

    monkeypatch.setattr(RulesRouter, "route", interrupt_on_fifth)
    output = tmp_path / "bench.json"
    with pytest.raises(KeyboardInterrupt):
        cli.main(["--routers", "rules,jev", "--repetitions", "1", "--output", str(output)])
    assert not output.exists()  # no artifact, but the journal has everything completed so far
    journal = read_journal(str(output) + JOURNAL_SUFFIX)
    assert journal[0]["type"] == "provenance" and journal[-1]["type"] == "run_interrupted"
    assert sum(line["type"] == "record" and line["router"] == "rules" for line in journal) == 4


def test_verification_dry_run_journals_both_calls(tmp_path):
    output = tmp_path / "verify.json"
    assert cli.main(["verify-jev", "--output", str(output)]) == 0
    journal = read_journal(str(output) + JOURNAL_SUFFIX)
    assert [line["case_id"] for line in journal if line["type"] == "record"] == ["L01", "L12"]
    assert [line["case_id"] for line in journal if line["type"] == "call_started"] == ["L01", "L12"]


def test_route_records_carry_no_forbidden_fields():
    fields = set(RouteRecord.__dataclass_fields__)
    assert not fields & {"query", "headers", "authorization", "context", "chunks", "retrieved_context"}
