# Isolated Lambda parent transport adapter

Codex implementation and self-review, **pending independent Claude review**.
Offline implementation only: no actual SDK client/session construction,
credential/environment-file access, service/network call or live execution.

## Exact source and accepted inputs

- Direct source base: `db9aa768eb9cb4c00cc6c72f6c0ce28580e5b90b`.
- Isolated branch: `phase0/jev-rag-smoke-live-adapter`.
- Worktree: `C:\Projects\AWS Project\worktrees\jev-rag-smoke-live-adapter`.
- Only three additions: `scripts/jev_rag_smoke_live_adapter.py`,
  `tests/test_jev_rag_smoke_live_adapter.py`, and this handoff.
- Separate preflight subject: `e894e2155b1d0728615600b1f65438028acf2ea6`;
  committed/raw document hash
  `1610df8ea67f6c5c5ffc30d43c4ef4e6d6895d5d583b11f55b935fa862765ace`;
  acceptance report
  `b4bc155fe5a6093819dd5520e4a28f0bdf26e0c830f003f6a166c000c1532f21`.
- Separate artifact acceptance report
  `3d9a00862e0b09dda32eaf1d8533ec11916eb1a57c022cfd82062a168476596d`
  accepts `e6ab512b4aa79d6c4ee32c3d6c8e98fa264446f9` only within its
  artifact/local-native scope. Its artifact and evidence were not rerun or changed.

Reports, document hashes and verdicts were read and verified before worktree
creation. Component acceptance does not extend to this new adapter increment.
No owner query, data consent, token bound, price record, budget or run was chosen.

## API and transport boundary

`ParentTransport(client, target, settings, payload, *, errors=None)` accepts an
already supplied client. There is no factory, Session, credential loader, CLI,
dotenv call or environment read. Module import uses standard-library definitions
only. Exception classes are imported lazily on explicit construction, or injected.

`target` has the accepted operator's exact four fields: account (12 digits),
region (`us-east-1`), function_name (1–64 ASCII name characters) and qualifier
(`$LATEST` or a positive numeric version of at most 20 digits). `settings` has
the P0 exact fields: max_attempts = builtin integer 1; connect_seconds and
read_seconds = builtin integers 1–120. These bounds are inherited, not owner
choices. Supplied payload must be nonempty canonical object JSON within 131,072
bytes: sorted keys, compact separators, ASCII escapes, finite numbers and one LF.
Duplicate keys, bad UTF-8, alternate encodings and noncanonical bytes reject.
This is byte validation, not full invocation/policy validation or authorization.

Before hook registration, the injected client's metadata must match the official
regional HTTPS endpoint, region, supplied timeouts and exactly
`{"total_max_attempts":1,"mode":"standard"}`. Callable invoke, close and event
registration are required. Actual client provenance and credential-provider
activity remain external prerequisites; a fake object's metadata cannot prove them.

`invoke_once()` sends only Invoke/RequestResponse with LogType None and the exact
canonical bytes. FunctionName is a **full regional account-bound function ARN**;
Qualifier is a separate SDK argument. The request property returns a copy.
The installed SDK serializer was exercised without a client: URI encoding, query,
body and headers match the gate. No discovery, polling, fallback or second Invoke
exists. No SDK client is created by the module. No Lambda application files change.

Wildcard parameter/send hooks fail closed on any other operation, changed target,
qualifier, body, method, URL or invocation/log header. One parameter callback and
one approved send callback are required. A second send raises before the injected
transport's send and is separately counted as blocked. A lock makes local entry
and counter updates atomic. The same adapter instance cannot be entered again,
including after failure. These are reviewed checks on an owned client, not a
sandbox, cross-process claim, or authenticated delivery observer. A callback is
not proof of delivery; SDK RetryAttempts does not manufacture a delivered count.

## Results, failures and private evidence

The returned `Attempt` retains private `body` bytes, selected `metadata`, fixed
primary code, all fixed failure codes and dispatch/parameter/approved/blocked
callback counts. The repr contains only code and byte count. `summary()` excludes
body, request identifiers, provider messages, headers, query/answer and paths.
Its version is `jev-rag-smoke-parent-transport-result-v1`; it hashes body bytes
and the metadata projection (sorted compact ASCII JSON, finite values, one LF).
No filesystem publication occurs in this adapter.

The metadata projection preserves bounded SDK RequestId, RetryAttempts,
HTTPStatusCode, and normal-response StatusCode, ExecutedVersion and optional
FunctionError. Missing versus null ResponseMetadata is explicit; invalid values
are rejected and not copied into diagnostics. FunctionError omission versus null
is preserved. SDK headers/Error.Message are deliberately outside this projection.
Provenance is `SELECTED_FIELDS_OF_INJECTED_SDK_RESPONSE`, never a verbatim or
authenticated AWS capture. Service exceptions use the same bounded projection.

The accepted parent response limit is **131,072 bytes**, not the Jev HTTP
adapter's separate 65,536-byte limit. Reads request at most 8,192 bytes and probe
one byte beyond an exact-limit prefix. Overflow retains exactly the permitted
prefix and stops reading. Read-returned chunks are preserved before subsequent
read/close failures. EOF, body close and client close are separate flags. A failed
close prevents a clean returned result even if all bytes reached EOF.

This bounds bytes retained for later interpretation. It does not bound allocations
inside the SDK/transport or an oversized chunk already delivered by a fake or
transport. Bytes hidden inside a failed read cannot be recovered. Timeouts are
client settings, not an absolute wall-clock deadline. No JSON/handler assessment
is performed on incomplete or complete response bytes here; the unchanged consumer
must perform its existing structural/accounting validation before downstream use.

Real installed botocore ClientError, connection/read/endpoint/proxy/TLS/HTTP errors,
ResponseStreamingError and IncompleteReadError are mapped to fixed sanitized
service-error/unknown outcomes. Parameter/credential exception definitions are
also handled conservatively without accessing a provider. OSError/interruption
remain unknown after possible entry. ValueError handling is local to stream/client
closure and stream reading (e.g. a closed stream); invoke ValueError and unrelated
RuntimeError propagate as programming defects. There is no global catch-all.
Already received prefixes survive propagated read defects in `transport.result`;
the local use marker remains set. A future console boundary must not print raw
programming tracebacks into public evidence.

Nonzero, missing or malformed retry metadata, bad status/version/request IDs,
missing hooks and all read/close failures prevent a clean result. Returned bytes
and valid metadata remain available. No reservation is released. `delivery` and
authenticated observation remain unestablished; known usage is left for the
unchanged handler-result consumer, not erased or inferred by this adapter.
`RETURNED` means transport return only: FunctionError and handler failure may
still be present, and it does not mean a successful experiment.

LogResult is **not supported** in this increment: request LogType is None and an
unexpected LogResult rejects without logging its value. No tail parser, REPORT
producer, CloudWatch discovery or polling is added. SDK ResponseMetadata.RequestId
is not assumed to be the Lambda execution/REPORT ID. REPORT evidence remains
`INCOMPLETE_NOT_CAPTURED` even for clean transport return.

## Not integrated: exact minimal future consumer seam

The unchanged operator's `validate` accepts only SIMULATED_OFFLINE; `bind` requires
simulation_only=True and an injected account attribute. This adapter advertises
neither. An explicit regression confirms a non-simulation client is rejected by
the current bind path. **simulate cannot reach this adapter or AWS.** No operator,
P0, producer, policy, contract, application, pin or package byte was modified.

A separately authorized integration would need a distinct explicit live entry
and validated mode, retaining simulate unchanged; its claim/attempt publication
must precede the live factory exactly as in the accepted P0/operator. After the
reviewed factory it would construct this adapter and consume invoke_once rather
than operator.bind/raw invoke/read_response. The request record and send binding
must use the adapter's account-bound full ARN instead of the simulated bare name.
Its consumer must publish preserved body/metadata/failure/counter evidence before
interpreting any clean response, and keep all uncertain parent holds. It must not
pass the projection off as a raw SDK response or bypass inspect_handler. This
grant implements none of that seam and grants no new live mode or authorization.

The existing inspect_logs join must also not assume the SDK request ID is the
execution ID. A future reviewed execution/REPORT provenance source and explicit
join are required; this is not resolved by supplying an invented fixture or hash.
No schema change or general recovery/authorization framework is proposed here.

## Validation and self-review

Final suites: **374 passed per interpreter**, no skips: adapter 90, unchanged
operator 201, P0 83. Both report zero outbound attempts with the existing guard
active. Invented NumPy/FAISS substitutes were read before use; no native modules
were exercised. Actual exception definitions and installed Config/Invoke serializer
were used, **without client/session construction or credential resolution**.

- Python 3.11.15 (Anaconda legal-agent), boto3/botocore **1.43.14**: compatibility
  validation only, not a claim to use the artifact SDK pin.
- Python 3.13.12 (main .venv), boto3/botocore **1.42.96**: actual pinned exception
  and serializer validation. Existing installation reused; nothing installed.
- Ruff 0.15.14: scoped check and format check pass; staged whitespace check passes.
- One inherited warning per pytest run: unknown asyncio_mode with plugin autoload
  disabled. No async cases or live tests were selected.

The SDK_PIN constant documents the reviewed SDK. The adapter does not authenticate
or reconfigure a supplied client's version; the future factory/environment binding
must establish the exact reviewed pin. The two host environments are not conflated.

Coverage includes canonical input/configuration rejection before dispatch; exact
full-ARN serialization; parameter/send substitutions; duplicate entry and blocked
second send; service errors and all named transport/stream classes; partial UTF-8
bytes; exact limit/overflow/oversized chunks and early termination; close failures;
malformed/missing/null metadata; nonzero retry metadata; version mismatch;
FunctionError; deliberate programming-error propagation; pure import and explicit
exception injection. Existing P0 and operator invariants remain intact.

Initial sandbox integrated run: 168 passed/198 failed at existing claim-root
checks. A local diagnostic reproduced PermissionError on strict Path.resolve for
the new pytest directory. Guarded final runs outside that process filesystem
restriction passed. No guard, permission or validator was changed. An initial
payload-derived long fixture ID was shortened; a scratch Ruff launcher initially
pointed at the prior worktree and found neither new file, then was corrected only
in task scratch. The unused test import flagged by lint was removed. Failed logs
are retained; none is presented as a passing validation. An exclusive scratch-log
collision retained its previous receipt; final run names are distinct.

Exact final commands (both select the same three suites):

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-live-adapter-20261008-63f49ca1\validate.py' test-candidate-311
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-live-adapter-20261008-63f49ca1\validate.py' test-candidate-313
# validate.py invokes inspected run_offline.py with:
# tests/test_jev_rag_smoke_live_adapter.py tests/test_jev_rag_smoke_operator.py
# tests/test_jev_rag_smoke_preinvoke.py -q -p no:cacheprovider --tb=short
# Fresh --basetemp and --junitxml are recorded in each command receipt.
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-live-adapter-20261008-63f49ca1\validate.py' lint-v4
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-live-adapter-20261008-63f49ca1\validate.py' format-check-v4
```

## Preservation and independent-review scope

Task receipts: `C:\Projects\AWS Project\dependency-acquisition\rag-live-adapter-20261008-63f49ca1`.
Before/after snapshots cover all sixteen prior worktrees and readable changed/
untracked bytes, ten protected artifacts, sixteen fixed inputs, current artifact
ZIP/manifest/index, fifteen supplemental-research files and 133 readable sealed
files. A further 1,084 sealed paths are inaccessible and not certified; no ACLs
were changed. All prior bindings are compared unchanged. No historical inventory
is rewritten. Commit receipt records direct ancestry and separate raw Git blob
versus working-copy hashes; the three staged paths must match validated bytes.

Claude should review the standalone boundary, full-ARN wire binding and exact
hooks; targeted exception mapping; prefix/closure preservation; retry uncertainty;
bounded projection and missing/null states; programming-error escape; pinned versus
compatibility SDK validation; and the documented minimal future integration seam.

O1 has a standalone transport implementation but is not integrated. O2 REPORT/
observation provenance, O3 confirmed publication/parent completion and O4 operational
assessment remain gated. Also unresolved: exact-run owner authorization, approved
data/object/query/source conditions, price/token bounds/ceilings/infrastructure
allowance, P0 sufficiency and durable claim, permitted credential/provider/endpoint
flow, private retention, independently reviewed factory/consumer integration,
current exact artifact/configuration evidence, semantic assessment and qualification.
Existing public-price/artifact acceptances do not settle these prerequisites.

Stop for independent review. No integration, main merge, push, account/network
calls, actual credentials/.env reads, native execution, builds, uploads, resource
changes, inference, deployment or Reviewer Protocol v2 changes occurred.
