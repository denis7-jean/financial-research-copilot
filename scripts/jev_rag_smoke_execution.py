"""Callable-only dedicated-process launcher; no credential source or live CLI.

External authorization and its trusted hash must come from the caller. Hashes
bind bytes, not authorship or permission. Preparation performs read-only input
and root validation, never SDK construction. This is not a process sandbox.
"""

from threading import Lock

AUTH_SCHEMA = "jev-rag-smoke-execution-authorization-v1"
SCOPE = "ONE_SYNCHRONOUS_TAIL_INVOKE_NO_OTHER_SERVICE_CALLS"
RECEIPT_SCHEMA = "jev-rag-smoke-returned-status-v1"
RESULT_SCHEMA = "jev-rag-smoke-launcher-result-v1"
RECEIPT_FILE = "returned-status.json"
MAX_AUTH_BYTES = 16_384
MAX_RECEIPT_BYTES = 32_768


class ExecutionError(ValueError):
    """Fixed codes only; no signing values, private paths or provider messages."""

    def __init__(self, code):
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise ExecutionError(code) from None


def prepare(
    plan_raw,
    p0_raw,
    invocation_raw,
    policy_raw,
    *,
    evidence,
    hashes,
    root,
    authorization_raw,
    expected_authorization_sha256,
    client_settings,
    access_key_id,
    secret_access_key,
    session_token=None,
):
    """Validate explicit bindings; keep explicitly supplied signing in memory.

    Authorization must bind all six input hashes, target including qualifier,
    canonical resolved root and client settings, and assert dedicated-process
    prerequisites. That assertion is external, not independently authenticated
    here. No default inputs, prices, budget, output root or signing source exist.
    """
    from scripts import jev_rag_smoke_client_factory as factory
    from scripts import jev_rag_smoke_operator as operator

    plan, original, preflight, parent = operator.validate_adapter(
        plan_raw,
        p0_raw,
        invocation_raw,
        policy_raw,
        evidence=evidence,
        hashes=hashes,
        root=root,
    )
    _require(plan["schema"] == operator.TAIL_PLAN_SCHEMA, "TAIL_PLAN_REQUIRED")
    _require(
        operator.p0.hash_value(expected_authorization_sha256)
        and type(authorization_raw) is bytes
        and 0 < len(authorization_raw) <= MAX_AUTH_BYTES
        and operator.digest(authorization_raw) == expected_authorization_sha256,
        "AUTHORIZATION_BINDING_INVALID",
    )
    try:
        authority = operator.parse(authorization_raw, MAX_AUTH_BYTES, "INPUT_INVALID")
        canonical = operator.encode(authority)
    except operator.OperatorError:
        raise ExecutionError("AUTHORIZATION_INVALID") from None
    _require(
        type(authority) is dict
        and set(authority)
        == {
            "schema",
            "operational_authorized",
            "dedicated_process_confirmed",
            "execution_scope",
            "target",
            "inputs_sha256",
            "client_settings",
            "persistent_root",
        }
        and canonical == authorization_raw
        and authority["schema"] == AUTH_SCHEMA
        and authority["operational_authorized"] is True
        and authority["dedicated_process_confirmed"] is True
        and authority["execution_scope"] == SCOPE
        and authority["target"] == plan["target"]
        and authority["inputs_sha256"] == hashes
        and operator.encode(authority["client_settings"])
        == operator.encode(client_settings)
        and authority["persistent_root"] == str(parent),
        "AUTHORIZATION_INVALID",
    )
    _require(
        type(client_settings) is dict
        and operator.encode(client_settings)
        == operator.encode(original["parent_invocation"]),
        "CLIENT_SETTINGS_MISMATCH",
    )
    # The accepted factory does no SDK/provider work until the consumer calls it.
    client_factory = factory.prepare(
        dict(client_settings),
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        session_token=session_token,
    )
    return _Prepared(
        (plan_raw, p0_raw, invocation_raw, policy_raw),
        dict(evidence),
        dict(hashes),
        parent,
        preflight["execution_id"],
        expected_authorization_sha256,
        client_factory,
    )


def _publish_receipt(operator, directory, authority_hash, actual_return):
    """No retry/overwrite/delete, including partial writes and failed close."""
    try:
        raw = operator.encode(
            {
                "schema": RECEIPT_SCHEMA,
                "authorization_sha256": authority_hash,
                "consumer_return": actual_return,
            }
        )
        _require(len(raw) <= MAX_RECEIPT_BYTES, "RETURNED_STATUS_TOO_LARGE")
        operator._write(directory / RECEIPT_FILE, raw)
        _require(
            (directory / RECEIPT_FILE).read_bytes() == raw,
            "RETURNED_STATUS_UNCONFIRMED",
        )
    except operator.OperatorError:
        raise ExecutionError("RETURNED_STATUS_INVALID") from None
    except (OSError, KeyboardInterrupt):
        raise ExecutionError("RETURNED_STATUS_PUBLICATION_FAILED") from None
    return operator.digest(raw)


class _Prepared:
    def __init__(self, args, evidence, hashes, root, execution_id, authority, factory):
        self._args = args
        self._evidence = evidence
        self._hashes = hashes
        self._root = root
        self._execution_id = execution_id
        self._authority = authority
        self._factory = factory
        self._lock = Lock()
        self._used = False

    def __repr__(self):
        return "RagSmokeExecution(single_use=True)"

    def run(self, *, stdout=None, stderr=None):
        """Propagated defects are never reconstructed into returned completion.

        Consumer owns claim/marker, dispatch, partial evidence and finalization.
        No launcher publication is attempted when no consumer return exists, so
        an escaping primary defect cannot be masked by secondary launcher work.
        """
        from scripts import jev_rag_smoke_operator as operator

        with self._lock:
            _require(not self._used, "EXECUTION_ALREADY_ATTEMPTED")
            self._used = True
        actual = operator.consume_adapter(
            *self._args,
            evidence=self._evidence,
            hashes=self._hashes,
            root=self._root,
            client_factory=self._factory,
        )
        directory = self._root / self._execution_id
        receipt_hash = _publish_receipt(operator, directory, self._authority, actual)
        complete = actual["status"] == "COMPLETE"
        if complete:
            operator.confirm(actual, directory)
        console_exit = operator.emit_confirmation(actual, stdout, stderr)
        confirmed = complete and console_exit == 0
        return {
            "schema": RESULT_SCHEMA,
            "status": "COMPLETE" if confirmed else "UNCONFIRMED",
            "code": (
                "CONSOLE_CONFIRMATION_UNAVAILABLE"
                if console_exit == 3
                else actual["code"]
            ),
            "consumer_return": actual,
            "returned_status_sha256": receipt_hash,
            "publication_confirmed": confirmed,
            "console_exit_code": console_exit,
            "release_authorized": False,
        }
