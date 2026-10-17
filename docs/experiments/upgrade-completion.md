# Scoped Upgrade completion

The owner accepted completion of the agreed three-item Upgrade scope on
2026-10-17, following independent review of the final isolated RAG smoke.
Earlier accepted items are not reopened by this documentation/source integration.
This note records completed work; it creates no execution or release authority.

## Implemented and observed

- Haiku remains the application router default. The experimental Jev adapter and
  synthetic comparison tooling exist, but Jev application live/shadow operation
  and production qualification are not established by this smoke.
- The metadata validator accepts the two reviewed schemas: `chunk_id`, `source`
  and `text`, optionally with a string `chunk_preview`. Required-field, row-order,
  source-count and object-integrity gates remain unchanged. Preview text is not
  used as model context.
- The repaired self-contained Linux/Python 3.11 artifact was deployed to an
  isolated smoke function, published as numeric Version 1 and independently
  checked through accepted deployment/freshness evidence.
- One qualified Version 1 Invoke returned HTTP 200, no function error and
  `STRUCTURAL_SUCCESS`. Routing selected QA at confidence 0.95; all five retrieval
  hits were the expected JPMorgan corpus source. Generation returned a substantive,
  non-abstaining answer.

## Answer and accounting

For the question about JPMorgan Chase's FY2025 total net revenue, the answer was
**$182.447 billion**, comprising $87.004 billion noninterest revenue and
$95.443 billion net interest income. Independent review found the period,
reported metric, units and arithmetic supported by the hash-bound test corpus.
This is not authentication of an external filing or current financial truth.

There was one parent Invoke and five conditional inner calls, including three
model inferences, with no recorded retry or extra request. Returned-usage sample
model accounting was USD 0.00625386. Task, infrastructure and invoice cost are not
established. Parent reservations remain retained; no release or cleanup occurred.

## Evidence limits

The accepted handler retains answer, source citations and retrieval source/score
pairs, not chunk IDs, passage text or the generation prompt. Exact top-five
passage attribution and answer-to-actual-context grounding remain unestablished.
The review explicitly found this compatible with the accepted scoped objective,
rather than a new missing gate. Corpus rows supporting the answer must not be
represented as proved actual retrieved passages.

Object-integrity, embedding and native-index/search gates are source-enforced
rather than separately exported runtime arrays. Structural vector/row checks do
not establish semantic alignment. Tail/REPORT telemetry is unauthenticated.
The supervisor's own OS exit and external shell context remain owner-reported;
the actual collector, driver, nine stages and children returned zero with joined
captures. All attempts are consumed; this note authorizes no repeat.

One sample does not establish quality qualification, a latency distribution,
general managed-runtime compatibility, Jev readiness or production rollout.
The ordinary production routing and isolated smoke deployment remain distinct.

## Durable provenance

Full captures, authority records and artifact packages remain in the owner's
retained evidence store outside Git. They are intentionally not copied into this
repository. These raw SHA-256 identifiers join this note to those exact subjects:

| Subject | Raw SHA-256 |
|---|---|
| Final independent runtime/semantic review | `2bcc3e11cd12c1db7044b18e37efe05b4cb247ba5bb074ee0ad85369855c1e03` |
| Repaired candidate ZIP | `75ff49c05495007fa8830ae532ea5239c13bd032f2ba1b485723b09d340c0a31` |
| External repair source manifest | `2e9373e234495f0be05c48b32d04359fe5ef74895342f522a08ab44b96331a8e` |
| External artifact entry manifest | `a943871356ec4b53b79f654e45f001015f98a1aa23a11bbb57974b549eead9be` |
| Accepted shipped metadata validator | `a907f7d5d85e8d2682db08db2e36c552b38d9e71bfe59eac51467d2bd774217d` |

The embedded build manifest was intentionally preserved and still describes the
old validator. The external manifests and accepted reviews bind the repaired
artifact. Do not treat the embedded manifest as a current repaired-source map.

## Repository reconciliation

The historical execution branch had retained the old validator even while the
accepted artifact used the repaired one. Newly authorized post-completion
integration copies the exact accepted shipped validator bytes into the repository
and retains portable schema regressions from its accepted tests. Other shipped
application files match after accounting for checkout line endings. No deployed
artifact, evidence record, data, dependency pin or production configuration is
changed by this reconciliation.

The original Git/preservation gates remain historical records. README and source
edits made after completion are separately recorded integration work, not a
rebaseline of the completed experiment. See the
[smoke acceptance contract](jev-rag-smoke-acceptance.md) for the scope distinctions.
