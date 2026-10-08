"""Opt-in, single-run RAG controls. Evidence hashes bind inputs, not authority.

The SDK hooks check reviewed client requests/sends; this is not a sandbox.
Credentials, live authorization and the correctness of price/capacity evidence
remain external prerequisites. No caller-side timeout implies remote cancellation.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from app.errors import ServiceFailure

HAIKU = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
TITAN = "amazon.titan-embed-text-v2:0"
_ACTIVE = ContextVar("rag_smoke_policy", default=None)
_ORDER = ("router", "index", "metadata", "embedding", "generation")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_MONEY = re.compile(r"(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,12})?\Z")


class SmokeStop(ServiceFailure):
    """Fixed codes only; never wrap provider text or request values."""

    def __init__(self, code):
        super().__init__("rag_smoke", "internal", code)
        self.args = (code,)


def check(condition, code):
    if not condition:
        raise SmokeStop(code) from None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            check(key not in result, "JSON_INVALID")
            result[key] = value
        return result

    def nonfinite(_):
        raise SmokeStop("JSON_INVALID")

    def finite_float(text):
        value = float(text)
        check(math.isfinite(value), "JSON_INVALID")
        return value

    try:
        return json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=nonfinite,
            parse_float=finite_float,
        )
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise SmokeStop("JSON_INVALID") from None


def exact(value, keys):
    check(type(value) is dict and set(value) == set(keys), "POLICY_INVALID")


def integer(value, minimum=1, maximum=1_000_000):
    check(type(value) is int and minimum <= value <= maximum, "POLICY_INVALID")


def money(value):
    check(type(value) is str and _MONEY.fullmatch(value), "POLICY_INVALID")
    return Decimal(value)


def charge(incoming, outgoing, evidence):
    # Validated bounded decimal inputs; precision exceeds the full product size.
    with localcontext() as ctx:
        ctx.prec = max(80, len(str(incoming)) + len(str(outgoing)) + 50)
        return (
            incoming * money(evidence["input_usd_per_million"])
            + outgoing * money(evidence["output_usd_per_million"])
        ) / Decimal(1_000_000)


def money_total(values):
    """Exact addition also for valid, unclamped charges far above the bound."""
    values = list(values)
    with localcontext() as ctx:
        ctx.prec = max(
            80,
            max(v.adjusted() for v in values)
            - min(v.as_tuple().exponent for v in values)
            + len(str(len(values)))
            + 3,
        )
        return sum(values, Decimal(0))


def current_policy():
    return _ACTIVE.get()


class SmokePolicy:
    def __init__(
        self,
        configuration,
        *,
        evidence,
        trusted_evidence_hashes,
        claim_directory,
        native,
    ):
        """Validate everything before claims, client construction or requests.

        ``evidence`` holds the two supplied raw price/capacity records. Expected
        hashes arrive separately; neither hashes nor the record's dated sources
        authenticate the owner's grant or independently verify published prices.
        ``native`` is the FAISS/NumPy adapter (invented fakes in offline tests).
        """
        try:
            config = strict_json(canonical(configuration))
            exact(
                config,
                (
                    "schema",
                    "run_id",
                    "scenario",
                    "query_sha256",
                    "region",
                    "models",
                    "max_attempts",
                    "output_tokens",
                    "ceilings_usd",
                    "timeouts",
                    "objects",
                    "metadata",
                    "expected_source",
                    "embedding_response_bytes",
                ),
            )
            check(config["schema"] == "rag-smoke-policy-v2", "POLICY_INVALID")
            check(
                type(config["run_id"]) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", config["run_id"]),
                "POLICY_INVALID",
            )
            check(
                type(config["scenario"]) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", config["scenario"]),
                "POLICY_INVALID",
            )
            check(
                type(config["query_sha256"]) is str
                and _HASH.fullmatch(config["query_sha256"]),
                "POLICY_INVALID",
            )
            check(
                config["region"] == "us-east-1"
                and config["models"] == {"haiku": HAIKU, "titan": TITAN},
                "MODEL_BINDING_INVALID",
            )
            check(
                config["max_attempts"]
                == {"router": 1, "embedding": 1, "generation": 1, "object_reads": 2}
                and all(type(v) is int for v in config["max_attempts"].values()),
                "POLICY_INVALID",
            )
            exact(config["output_tokens"], ("router", "generation"))
            for value in config["output_tokens"].values():
                integer(value, maximum=64_000)
            exact(config["ceilings_usd"], ("haiku", "titan", "total"))
            self.caps = {
                key: money(value) for key, value in config["ceilings_usd"].items()
            }
            check(all(value > 0 for value in self.caps.values()), "POLICY_INVALID")
            exact(config["timeouts"], ("connect_seconds", "read_seconds"))
            for value in config["timeouts"].values():
                integer(value, maximum=120)
            integer(config["embedding_response_bytes"], maximum=1_048_576)
            exact(config["objects"], ("index", "metadata"))
            for obj in config["objects"].values():
                exact(
                    obj,
                    (
                        "bucket",
                        "key",
                        "owner",
                        "etag",
                        "version_id",
                        "size_bytes",
                        "sha256",
                    ),
                )
                check(
                    type(obj["bucket"]) is str
                    and re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", obj["bucket"])
                    and ".." not in obj["bucket"],
                    "POLICY_INVALID",
                )
                check(
                    type(obj["key"]) is str
                    and obj["key"]
                    and all(
                        part not in ("", ".", "..") for part in obj["key"].split("/")
                    )
                    and not any(c in obj["key"] for c in "\\\x00\r\n"),
                    "POLICY_INVALID",
                )
                check(
                    type(obj["owner"]) is str
                    and re.fullmatch(r"[0-9]{12}", obj["owner"]),
                    "POLICY_INVALID",
                )
                check(
                    type(obj["etag"]) is str
                    and re.fullmatch(r'"[0-9a-f]+(?:-[0-9]+)?"', obj["etag"]),
                    "POLICY_INVALID",
                )
                check(
                    obj["version_id"] is None
                    or type(obj["version_id"]) is str
                    and re.fullmatch(r"[A-Za-z0-9_.-]{1,256}", obj["version_id"]),
                    "POLICY_INVALID",
                )
                integer(obj["size_bytes"], maximum=250 * 1024 * 1024)
                check(
                    type(obj["sha256"]) is str and _HASH.fullmatch(obj["sha256"]),
                    "POLICY_INVALID",
                )
            index, metadata = config["objects"].values()
            check(
                index["bucket"] == metadata["bucket"]
                and index["owner"] == metadata["owner"]
                and index["key"] != metadata["key"],
                "POLICY_INVALID",
            )
            exact(config["metadata"], ("rows", "source_counts", "max_text_bytes"))
            integer(config["metadata"]["rows"])
            integer(config["metadata"]["max_text_bytes"], maximum=1_048_576)
            sources = config["metadata"]["source_counts"]
            check(type(sources) is dict and bool(sources), "POLICY_INVALID")
            for source, count in sources.items():
                check(
                    type(source) is str
                    and source.startswith("s3://" + index["bucket"] + "/docs/")
                    and not any(c in source for c in "\r\n\x00\\")
                    and ".." not in source.split("/"),
                    "POLICY_INVALID",
                )
                integer(count)
            check(sum(sources.values()) == config["metadata"]["rows"], "POLICY_INVALID")
            exact(config["expected_source"], ("source", "minimum_hits"))
            expected = config["expected_source"]
            check(
                type(expected["source"]) is str and expected["source"] in sources,
                "POLICY_INVALID",
            )
            integer(expected["minimum_hits"], maximum=5)
            check(
                set(evidence) == set(trusted_evidence_hashes) == {"haiku", "titan"},
                "EVIDENCE_INVALID",
            )
            self.prices = {}
            for provider in ("haiku", "titan"):
                check(
                    type(evidence[provider]) is bytes
                    and type(trusted_evidence_hashes[provider]) is str
                    and _HASH.fullmatch(trusted_evidence_hashes[provider]),
                    "EVIDENCE_INVALID",
                )
                check(
                    digest(evidence[provider]) == trusted_evidence_hashes[provider],
                    "EVIDENCE_HASH_MISMATCH",
                )
                record = strict_json(evidence[provider])
                exact(
                    record,
                    (
                        "schema",
                        "model_id",
                        "region",
                        "tier",
                        "input_token_bound",
                        "max_supported_output_tokens",
                        "input_usd_per_million",
                        "output_usd_per_million",
                        "source_urls",
                        "verified_utc",
                    ),
                )
                check(
                    record["schema"] == "rag-smoke-price-bound-v1"
                    and record["model_id"] == config["models"][provider]
                    and record["region"] == config["region"]
                    and record["tier"] == "standard",
                    "EVIDENCE_BINDING_INVALID",
                )
                integer(
                    record["input_token_bound"],
                    maximum=200_000 if provider == "haiku" else 1_000_000,
                )
                integer(
                    record["max_supported_output_tokens"], minimum=0, maximum=64_000
                )
                money(record["input_usd_per_million"])
                money(record["output_usd_per_million"])
                check(money(record["input_usd_per_million"]) > 0, "EVIDENCE_INVALID")
                check(
                    type(record["source_urls"]) is list
                    and bool(record["source_urls"])
                    and all(
                        type(url) is str
                        and urlsplit(url).scheme == "https"
                        and urlsplit(url).netloc
                        in (
                            "aws.amazon.com",
                            "docs.aws.amazon.com",
                            "platform.claude.com",
                        )
                        for url in record["source_urls"]
                    ),
                    "EVIDENCE_INVALID",
                )
                stamp = datetime.fromisoformat(
                    record["verified_utc"].replace("Z", "+00:00")
                )
                check(
                    stamp.utcoffset() is not None
                    and stamp.utcoffset().total_seconds() == 0,
                    "EVIDENCE_INVALID",
                )
                self.prices[provider] = record
            check(
                all(
                    cap <= self.prices["haiku"]["max_supported_output_tokens"]
                    for cap in config["output_tokens"].values()
                ),
                "OUTPUT_BOUND_INVALID",
            )
            check(
                self.prices["titan"]["max_supported_output_tokens"] == 0
                and money(self.prices["titan"]["output_usd_per_million"]) == 0,
                "EVIDENCE_BINDING_INVALID",
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            RecursionError,
            OverflowError,
        ):
            raise SmokeStop("POLICY_INVALID") from None
        self.config, self.native = config, native
        self.evidence_hashes = dict(trusted_evidence_hashes)
        self.directory = Path(claim_directory)
        self.clients = {}
        self.position = 0
        self.halted = False
        self.used = False
        self.permit = None
        self.exposure = {"haiku": Decimal(0), "titan": Decimal(0)}
        self.attempts = {}
        self.sequence = 0
        self.metadata = None
        self.index = None
        self.extra_requests = []
        self.extra_evidence = set()
        self.unestablished_stages = set()
        self.coverage_violated = False

    def accounting(self, *, compact=False):
        """Model-only local evidence, never a task-wide or invoiced cost bound.

        Unattributed response charges add to retained holds conservatively; the
        hold may overlap that charge. Unknown extra exposure is not assigned a
        fabricated amount. Hashes do not authenticate the supplied observations.
        """
        holds = {key: Decimal(0) for key in self.exposure}
        known = dict(holds)
        for stage, attempt in self.attempts.items():
            provider = "titan" if stage == "embedding" else "haiku"
            if stage in ("index", "metadata"):
                continue
            holds[provider] = money_total(
                (holds[provider], Decimal(attempt["hold_usd"]))
            )
            known[provider] = money_total(
                (known[provider], Decimal(attempt.get("charge_usd", "0")))
            )
        for extra in self.extra_requests:
            if extra["charge_usd"] is not None:
                known[extra["provider"]] = money_total(
                    (known[extra["provider"]], Decimal(extra["charge_usd"]))
                )
        result = {
            "scope": "LOCAL_MODEL_ACCOUNTING_NOT_TASK_TOTAL",
            "known_charges_usd": {k: str(v) for k, v in known.items()},
            "retained_holds_usd": {k: str(v) for k, v in holds.items()},
            "exposure_bound_established": not self.unestablished_stages,
            "ceiling_established": (
                not self.unestablished_stages
                and not self.coverage_violated
                and all(self.exposure[k] <= self.caps[k] for k in self.exposure)
                and money_total(self.exposure.values()) <= self.caps["total"]
            ),
            "reservation_coverage": (
                "VIOLATED"
                if self.coverage_violated
                else "UNESTABLISHED"
                if self.unestablished_stages
                else "WITHIN_RECORDED_RESERVATIONS"
            ),
            "unestablished_stages": sorted(self.unestablished_stages),
            "extra_request_count": len(self.extra_requests),
            "extra_requests_sha256": digest(canonical(self.extra_requests)),
        }
        if not compact:
            result["extra_requests"] = self.extra_requests
        return result

    def _usage(self, provider, payload):
        check(type(payload) is dict, "USAGE_INVALID")
        usage = (
            payload.get("usage")
            if provider == "haiku"
            else {
                "inputTokens": payload.get("inputTextTokenCount"),
                "outputTokens": 0,
            }
        )
        check(
            type(usage) is dict
            and all(
                type(usage.get(key)) is int and usage[key] >= 0
                for key in ("inputTokens", "outputTokens")
            ),
            "USAGE_INVALID",
        )
        if "totalTokens" in usage:
            check(
                type(usage["totalTokens"]) is int
                and usage["totalTokens"]
                == usage["inputTokens"] + usage["outputTokens"],
                "USAGE_INVALID",
            )
        # Do not retain arbitrary provider fields or text as usage evidence.
        return {key: usage[key] for key in ("inputTokens", "outputTokens")}

    def record_extra_request(
        self,
        stage,
        *,
        delivery,
        request_evidence_sha256,
        model_id,
        region,
        tier,
        usage=None,
    ):
        """Record an independently identified *already observed* model request.

        This local evidence seam cannot send or authorize anything. The caller
        must establish a distinct request and its own usage; a digest alone is
        not proof. Retry metadata never calls this method or supplies counts.
        Multiple observations may be recorded after abort, but no dispatch may.
        """
        check(current_policy() is self, "EXTRA_EVIDENCE_INVALID")
        self.halted = True
        valid_reference = (
            stage in ("router", "embedding", "generation")
            and delivery in ("YES", "UNKNOWN")
            and type(request_evidence_sha256) is str
            and _HASH.fullmatch(request_evidence_sha256)
            and request_evidence_sha256 not in self.extra_evidence
        )
        if not valid_reference:
            self.unestablished_stages.add("unidentified_model_request")
            self.fail("EXTRA_EVIDENCE_INVALID")
        self.extra_evidence.add(request_evidence_sha256)
        provider = "titan" if stage == "embedding" else "haiku"
        priced_binding = (
            model_id == self.config["models"][provider]
            and region == self.config["region"]
            and tier == "standard"
        )
        actual, valid = None, None
        if usage is not None:
            try:
                valid = self._usage("haiku", {"usage": usage})
                check(
                    provider != "titan" or valid["outputTokens"] == 0, "USAGE_INVALID"
                )
                if priced_binding:
                    actual = charge(
                        valid["inputTokens"],
                        valid["outputTokens"],
                        self.prices[provider],
                    )
            except SmokeStop:
                valid = None
        extra = {
            "request": f"{stage}-extra-{len(self.extra_requests) + 1}",
            "stage": stage,
            "provider": provider,
            "approved": False,
            "delivery": delivery,
            "reservation_usd": "0",
            "settled": False,
            "request_evidence_sha256": request_evidence_sha256,
            "pricing_binding": "PINNED_MODEL_REGION_STANDARD"
            if priced_binding
            else "UNESTABLISHED",
            "usage": valid,
            "usage_scope": "THIS_EXTRA_REQUEST_ONLY",
            "usage_status": "VALID_UNPRICED"
            if valid is not None and not priced_binding
            else "VALID"
            if valid is not None
            else "MISSING"
            if usage is None
            else "INVALID",
            "charge_usd": str(actual) if actual is not None else None,
            "over_approved_token_bound": valid is not None
            and (
                valid["inputTokens"] > self.prices[provider]["input_token_bound"]
                or valid["outputTokens"]
                > (0 if provider == "titan" else self.config["output_tokens"][stage])
            ),
        }
        self.extra_requests.append(extra)
        # Actual charges never become retroactively authorized or clamped.
        if actual is not None:
            self.exposure[provider] = money_total((self.exposure[provider], actual))
            if actual > 0:
                self.coverage_violated = True
        if actual is None or delivery == "UNKNOWN":
            self.unestablished_stages.add(stage)
        self._journal("extra-request", **extra)

    def _returned_usage(self, stage, provider, usage, amount, attributable):
        actual = charge(
            usage["inputTokens"], usage["outputTokens"], self.prices[provider]
        )
        exceeded = (
            usage["inputTokens"] > self.prices[provider]["input_token_bound"]
            or usage["outputTokens"]
            > (0 if provider == "titan" else self.config["output_tokens"][stage])
            or actual > amount
        )
        entry = self.attempts[stage]
        entry.update(
            usage=usage,
            usage_scope="RETURNED_RESPONSE_ONLY",
            usage_attribution="AUTHORIZED_REQUEST"
            if attributable
            else "UNATTRIBUTED_RESPONSE",
            charge_usd=str(actual),
            settled=attributable,
            hold_usd="0" if attributable else str(amount),
        )
        self.exposure[provider] = (
            money_total((self.exposure[provider], actual, amount.copy_negate()))
            if attributable
            else money_total((self.exposure[provider], actual))
        )
        if exceeded:
            self.coverage_violated = True
        self._journal(
            "usage",
            stage=stage,
            input_tokens=usage["inputTokens"],
            output_tokens=usage["outputTokens"],
            charge_usd=str(actual),
            reservation_usd=str(amount),
            overrun=exceeded,
            usage_scope=entry["usage_scope"],
            usage_attribution=entry["usage_attribution"],
            settled=attributable,
            hold_usd=entry["hold_usd"],
        )
        return exceeded

    def fail(self, code):
        self.halted = True
        raise SmokeStop(code) from None

    def validate_query(self, query):
        try:
            valid = (
                type(query) is str
                and digest(query.encode()) == self.config["query_sha256"]
            )
        except UnicodeError:
            valid = False
        check(valid, "INPUT_BINDING_MISMATCH")

    def _journal(self, kind, **fields):
        self.sequence += 1
        value = {
            "schema": "rag-smoke-event-v1",
            "sequence": self.sequence,
            "kind": kind,
            **fields,
        }
        try:
            with (self.directory / f"{self.sequence:02d}-{kind}.json").open(
                "xb"
            ) as stream:
                stream.write(canonical(value))
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            self.fail("EVIDENCE_PUBLICATION_FAILED")

    @contextmanager
    def activate(self, query):
        check(not self.used and current_policy() is None, "RUN_ALREADY_CLAIMED")
        self.validate_query(query)
        check(0 < len(query) <= 300, "INPUT_BINDING_MISMATCH")
        # Neither a parent traversal nor a link may redirect the durable claim.
        parent = self.directory.parent
        check(
            self.directory.is_absolute()
            and parent.is_dir()
            and parent.resolve() == parent
            and self.directory.name == self.config["run_id"],
            "CLAIM_PATH_INVALID",
        )
        for path in (parent, *parent.parents):
            check(
                not path.is_symlink()
                and not (
                    path.stat().st_file_attributes
                    if hasattr(path.stat(), "st_file_attributes")
                    else 0
                )
                & 0x400
                and not (path / ".git").exists(),
                "CLAIM_PATH_INVALID",
            )
        self.used = True
        try:
            self.directory.mkdir()
        except FileExistsError:
            self.fail("RUN_ALREADY_CLAIMED")
        except OSError:
            self.fail("CLAIM_UNAVAILABLE")
        token = _ACTIVE.set(self)
        self.query = query
        try:
            self._journal(
                "claim",
                policy_sha256=digest(canonical(self.config)),
                input_sha256=self.config["query_sha256"],
                evidence_hashes=self.evidence_hashes,
                scope="STRUCTURAL_SMOKE_NOT_QUALIFICATION",
            )
            yield self
            check(not self.halted and self.position == len(_ORDER), "CHAIN_INCOMPLETE")
            self._journal(
                "complete",
                status="STRUCTURAL_SMOKE_COMPLETE_NOT_QUALIFICATION",
                exposure_usd={k: str(v) for k, v in self.exposure.items()},
            )
        except SmokeStop as error:
            self.halted = True
            self._journal(
                "stopped",
                code=error.args[0],
                exposure_usd={k: str(v) for k, v in self.exposure.items()},
            )
            raise
        except Exception:
            self.halted = True
            self._journal(
                "stopped",
                code="LOCAL_OR_UNCERTAIN_FAILURE",
                exposure_usd={k: str(v) for k, v in self.exposure.items()},
            )
            raise SmokeStop("LOCAL_OR_UNCERTAIN_FAILURE") from None
        finally:
            self.permit = None
            self.query = None
            _ACTIVE.reset(token)

    def bind_clients(self, *, bedrock, s3):
        """Only inspected SDK config plus actual event evidence counts as bounded."""
        check(not self.used and not self.clients, "CLIENT_BINDING_INVALID")
        for service, client in (("bedrock-runtime", bedrock), ("s3", s3)):
            try:
                cfg = client.meta.config
                valid = (
                    cfg.region_name == "us-east-1"
                    and cfg.connect_timeout
                    == self.config["timeouts"]["connect_seconds"]
                    and cfg.read_timeout == self.config["timeouts"]["read_seconds"]
                    and cfg.retries == {"total_max_attempts": 1, "mode": "standard"}
                    and client.meta.endpoint_url
                    == f"https://{service}.us-east-1.amazonaws.com"
                )
                check(valid, "CLIENT_CONFIG_INVALID")
                client.meta.events.register(
                    "before-parameter-build.*.*", self._parameters
                )
                client.meta.events.register("before-send.*.*", self._send)
            except (AttributeError, TypeError):
                self.fail("CLIENT_CONFIG_INVALID")
            self.clients[service] = client

    def _parameters(self, params, model, **_):
        permit = self.permit
        check(
            permit is not None
            and model.name == permit["operation"]
            and params == permit["request"],
            "UNEXPECTED_REQUEST",
        )
        permit["parameter_checks"] += 1
        check(permit["parameter_checks"] == 1, "EXTRA_ATTEMPT")

    def _send(self, request, **_):
        permit = self.permit
        check(permit is not None and not self.halted, "UNEXPECTED_SEND")
        permit["sends"] += 1
        if permit["sends"] != 1 or permit["parameter_checks"] != 1:
            # before-send raises before transport delivery; this callback is not
            # evidence that a second request was delivered or billed.
            permit["blocked_sends"] += 1
            self.extra_requests.append(
                {
                    "request": f"{permit['stage']}-blocked-{permit['sends']}",
                    "stage": permit["stage"],
                    "provider": None
                    if permit["stage"] in ("index", "metadata")
                    else "titan"
                    if permit["stage"] == "embedding"
                    else "haiku",
                    "approved": False,
                    "delivery": "NO",
                    "reservation_usd": "0",
                    "settled": False,
                    "usage": None,
                    "usage_scope": None,
                    "charge_usd": None,
                    "usage_status": "NOT_DELIVERED",
                }
            )
            self._journal("blocked-send", **self.extra_requests[-1])
            self.fail("EXTRA_SEND")
        url = urlsplit(request.url)
        if permit["operation"] == "GetObject":
            obj = self.config["objects"][permit["stage"]]
            allowed = (
                (f"{obj['bucket']}.s3.us-east-1.amazonaws.com", "/" + obj["key"]),
                ("s3.us-east-1.amazonaws.com", "/" + obj["bucket"] + "/" + obj["key"]),
            )
            check(
                (url.netloc, unquote(url.path)) in allowed and request.method == "GET",
                "ENDPOINT_INVALID",
            )
        else:
            suffix = "converse" if permit["operation"] == "Converse" else "invoke"
            check(
                url.netloc == "bedrock-runtime.us-east-1.amazonaws.com"
                and unquote(url.path)
                == "/model/" + permit["request"]["modelId"] + "/" + suffix
                and request.method == "POST",
                "ENDPOINT_INVALID",
            )
        check(url.scheme == "https", "ENDPOINT_INVALID")
        permit["approved_sends"] += 1

    def invoke(self, stage, operation, request, *, decode=None):
        check(
            current_policy() is self
            and not self.halted
            and self.position < len(_ORDER)
            and _ORDER[self.position] == stage,
            "CHAIN_ORDER_INVALID",
        )
        service = "s3" if stage in ("index", "metadata") else "bedrock-runtime"
        check(service in self.clients, "CLIENTS_MISSING")
        expected_operation = (
            "GetObject"
            if service == "s3"
            else "InvokeModel"
            if stage == "embedding"
            else "Converse"
        )
        check(operation == expected_operation, "OPERATION_INVALID")
        provider = (
            None if service == "s3" else "titan" if stage == "embedding" else "haiku"
        )
        amount = Decimal(0)
        if provider:
            check(
                request["modelId"] == self.config["models"][provider],
                "MODEL_BINDING_INVALID",
            )
            if operation == "Converse":
                check(
                    set(request)
                    == {"modelId", "system", "messages", "inferenceConfig"},
                    "REQUEST_INVALID",
                )
                check(
                    request["inferenceConfig"]
                    == {"maxTokens": self.config["output_tokens"][stage]},
                    "OUTPUT_BOUND_INVALID",
                )
            else:
                check(
                    set(request) == {"modelId", "body", "contentType", "accept"}
                    and request["contentType"]
                    == request["accept"]
                    == "application/json",
                    "REQUEST_INVALID",
                )
                check(
                    strict_json(request["body"])
                    == {"inputText": self.query, "dimensions": 1024, "normalize": True},
                    "INPUT_BINDING_MISMATCH",
                )
            amount = charge(
                self.prices[provider]["input_token_bound"],
                0 if provider == "titan" else self.config["output_tokens"][stage],
                self.prices[provider],
            )
            check(
                money_total((self.exposure[provider], amount)) <= self.caps[provider]
                and money_total((*self.exposure.values(), amount))
                <= self.caps["total"],
                "RESERVATION_EXHAUSTED",
            )
            self.exposure[provider] = money_total((self.exposure[provider], amount))
        self.attempts[stage] = {
            "reservation_usd": str(amount),
            "settled": False,
            "hold_usd": str(amount),
            "delivery": "UNKNOWN",
        }
        # Exclusive durable record precedes every SDK call, including uncertain ones.
        self._journal(
            "attempt",
            stage=stage,
            operation=operation,
            request_sha256=digest(canonical(request)),
            reservation_usd=str(amount),
            status="CLAIMED_NO_RESEND",
        )
        self.permit = {
            "stage": stage,
            "operation": operation,
            "request": request,
            "parameter_checks": 0,
            "sends": 0,
            "approved_sends": 0,
            "blocked_sends": 0,
        }
        try:
            client = self.clients[service]
            response = getattr(
                client,
                {
                    "Converse": "converse",
                    "InvokeModel": "invoke_model",
                    "GetObject": "get_object",
                }[operation],
            )(**request)
            metadata = (
                response.get("ResponseMetadata") if type(response) is dict else None
            )
            retries = metadata.get("RetryAttempts") if type(metadata) is dict else None
            count_valid = (
                type(retries) is int
                and retries == 0
                and self.permit["sends"] == self.permit["parameter_checks"] == 1
                and self.permit["approved_sends"] == 1
            )
            self.attempts[stage]["retry_attempts"] = (
                retries if type(retries) is int and retries >= 0 else None
            )
            self.attempts[stage]["delivery"] = "YES" if count_valid else "UNKNOWN"
            if not count_valid:
                # Signals an inconsistency, not an exact delivered-request count.
                self.unestablished_stages.add(stage)
            if decode is not None:
                response, payload = decode(response)
            else:
                payload = response
            if provider:
                usage = self._usage(provider, payload)
                exceeded = self._returned_usage(
                    stage, provider, usage, amount, count_valid
                )
            check(count_valid, "ATTEMPT_COUNT_INVALID")
            check(not self.halted, "EXTRA_REQUEST_OBSERVED")
            if provider:
                check(not exceeded, "USAGE_OVERRUN")
                if provider == "haiku":
                    output = payload.get("output")
                    message = output.get("message") if type(output) is dict else None
                    content = message.get("content") if type(message) is dict else None
                    check(
                        type(message) is dict
                        and message.get("role") == "assistant"
                        and type(content) is list
                        and len(content) == 1
                        and type(content[0]) is dict
                        and set(content[0]) == {"text"}
                        and type(content[0]["text"]) is str
                        and bool(content[0]["text"].strip())
                        and payload.get("stopReason") in ("end_turn", "max_tokens"),
                        "MODEL_OUTPUT_INVALID",
                    )
            self.position += 1
            return payload
        except SmokeStop:
            self.halted = True
            raise
        except Exception:
            self.fail("UNCERTAIN_PROVIDER_OUTCOME")
        finally:
            self.attempts[stage]["send_checks"] = {
                "callbacks": self.permit["sends"],
                "approved_before_send": self.permit["approved_sends"],
                "blocked_before_send": self.permit["blocked_sends"],
            }
            self.permit = None

    def read_body(self, response, limit):
        body = response.get("Body", response.get("body"))
        check(body is not None, "BODY_MISSING")
        raw = bytearray()
        try:
            while True:
                part = body.read(min(65536, limit - len(raw) + 1))
                check(type(part) is bytes, "BODY_INVALID")
                if not part:
                    return bytes(raw)
                check(len(raw) + len(part) <= limit, "BODY_TOO_LARGE")
                raw.extend(part)
        finally:
            body.close()

    def object_bytes(self, role):
        obj = self.config["objects"][role]
        request = {
            "Bucket": obj["bucket"],
            "Key": obj["key"],
            "ExpectedBucketOwner": obj["owner"],
            "IfMatch": obj["etag"],
        }
        if obj["version_id"] is not None:
            request["VersionId"] = obj["version_id"]

        def decode(response):
            raw = self.read_body(response, obj["size_bytes"])
            check(
                response.get("ETag") == obj["etag"]
                and response.get("VersionId") == obj["version_id"]
                and type(response.get("ContentLength")) is int
                and response["ContentLength"] == len(raw) == obj["size_bytes"]
                and digest(raw) == obj["sha256"],
                "OBJECT_BINDING_MISMATCH",
            )
            return response, raw

        return self.invoke(role, "GetObject", request, decode=decode)

    def validate_metadata(self, raw):
        metadata = strict_json(raw)
        config = self.config["metadata"]
        check(
            type(metadata) is list and len(metadata) == config["rows"],
            "METADATA_INVALID",
        )
        counts = dict.fromkeys(config["source_counts"], 0)
        for ordinal, row in enumerate(metadata):
            check(
                type(row) is dict and set(row) == {"chunk_id", "source", "text"},
                "METADATA_INVALID",
            )
            check(
                type(row["chunk_id"]) is int
                and row["chunk_id"] == ordinal
                and type(row["source"]) is str
                and row["source"] in counts
                and type(row["text"]) is str
                and 0 < len(row["text"].encode()) <= config["max_text_bytes"],
                "METADATA_INVALID",
            )
            counts[row["source"]] += 1
        check(counts == config["source_counts"], "METADATA_SOURCE_MISMATCH")
        return metadata

    def validate_embedding(self, values):
        try:
            check(
                type(values) is list
                and len(values) == 1024
                and all(
                    type(value) in (float, int) and math.isfinite(value)
                    for value in values
                ),
                "EMBEDDING_INVALID",
            )
            norm = math.fsum(float(value) ** 2 for value in values)
        except (ValueError, TypeError, OverflowError):
            self.fail("EMBEDDING_INVALID")
        check(math.isfinite(norm) and abs(norm - 1) <= 0.01, "EMBEDDING_INVALID")
