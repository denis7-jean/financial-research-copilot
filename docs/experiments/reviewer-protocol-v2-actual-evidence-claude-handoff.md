# Focused handoff: actual assembled evidence subjects

Prepared 2026-10-03; not sent and no Claude invocation performed.
Code baseline remains `25bde9388d41bd476984aecad6c66ac6e48b2c92`.
The cleanup is independently accepted; those reports approve no future wrappers.
This handoff requests independent subject review, not operational adoption/readiness.

Private root:
`C:/Projects/AWS Project/heldout-external/reviewer-v2-evidence-assembly/2026-10-03-25bde93/`.
All paths below are relative to that root. Inspect exact bytes before issuing review.

## Precise subjects

| File | SHA-256 |
|---|---|
| assembly-index.json | 16cc736f6dea8672c920777f8365b4c4562d47abdfd61a9858e749d307ac1f3d |
| rules/eligibility_specification/rule-specification.json | d64cca70fff13c34459f66e643557179470edaf6fbf6523e08f7306c84daf8b1 |
| rules/exposure_specification/rule-specification.json | 365221ba6b4c995a7fdbb185071e7bb4a49aa52519467bd944760bdfe3bdff79 |
| rules/grouping_similarity_specification/rule-specification.json | cc1c9a4daceda978374afcd864f6d4e25f46d291b53517783b687a3265eb8dbe |
| historical-ledger-reconciliation-subject.json | 20252b1f3c161feaf2103597a8b28b0c899b1871f8545048cc9ac7018b01cf7f |

Each RuleSpecification contains the precise source/algorithm/decision FBs. In the
same role directory, inspect `current-normative-text.json`,
`current-normative-algorithm.json`, `original-s576-text.json`,
`original-proposed-sections-1-3.json`, the owner excerpt wrappers and
`rule-applicability.draft.json`. All member hashes and transcription fragments
are in the index; its `rules` objects give each required semantic-review join.

Also inspect `current-owner-decisions.json`, `historical-generating-bundle.json`,
`historical-sources/` (sixteen unchanged Git blobs), and
`current-verification-bundle.json`. Reused originals are explicitly referenced in
the index under `source_provenance`, `fixed_subjects` and `historical`.
No raw original or assembled subject should be rewritten to create acceptance.

## Semantic review requested for all three roles

Compare the captured text and algorithm transcripts with their actual original
records, the unchanged normative document and applicable mechanical contracts:

- Normative document: `4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7`.
- Eligibility contract: `91d73119ae0f3474c350def0ef87a5850ab98e7d8489c44e09ba436f65614fa4`.
- Exposure contract: `b0ca037ec36dd84f214286c281dfc162cfd2fbb593ea86833579a8b1671c507c`.
- Grouping/similarity contract: `181913badd890b7050ef2d4d23e1ea61c712569130eaaf2f7223c5b8eee8a795`.

Address faithful transcription, scope/applicability and superseding owner decisions
(particularly historical E01 disposition versus current metadata-only and D8 E03c).
Current-decision enums are transcriptions of O-b6e lines 10,12,14, not new approvals.
The proposed original sections are lineage; current owner resolutions are separate.
Mechanical constants encode the accepted consistency target and supply no authority.

For each common origin, explicitly decide whether the normative document supports
both text and algorithm roles. The index supplies exact **sorted unique**
`source_sections` and `algorithm_sections` sets. Those sets must be copied exactly
into any resulting `shared_origin_reviews`; acceptance is not predeclared.
Confirm raw-record/document identity is separate from each locator.

For S-576, original raw JSONL SHA-256 is
`7e481873256e5e1e3684d19fc36199baf093202cf23404338b90bcbf625b4a3f`;
one-based excerpt locators, including E05 283-329, name the **derived extraction**
SHA-256 `539541e3a3f28885a4be3c1e3d27171ca45bb6a30980cdad3b818933c7e49373`.
Its exact JSON-text-fields/LF extraction recipe was replayed. Retain complete:false
with unestablished flag meaning and the 37 supplementary-check registration and
historical-execution limitations. No reconstructed evidence substitutes for originals.

Required outputs are **three ReviewEvidence v4 records** with actual raw review
records, if supported by your independent findings. `subject_sha256` is the exact
applicable RuleSpecification byte hash above; `contract_sha256` is the applicable
contract; `normative_document` must equal the index's identical FB. Reviewer identity,
strict UTC, note and raw-record reference/path/hash must come from the actual review.
Do not generate a successful declaration if the subjects do not support one.

## Subject-bound reconciliation review requested

Inspect the exact `historical-ledger-reconciliation-subject.json` and its bound
manifest, ledger hash, historical/current sources, full current bundle, lemma and
existing counts receipt. No candidate text/IDs or rows should be printed.

The required **ReconciliationReview v1** joins are:

- subject_sha256: `20252b1f3c161feaf2103597a8b28b0c899b1871f8545048cc9ac7018b01cf7f`.
- contract_sha256: `fd1dfc6109428f6dc5651ee28996358f69514842b4a19efd18f2410292d8860e`.
- lemma_sha256: `febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef`.
- counts_sha256: `584d43ad6a02f7cdffa345a1fd92da04f9eef0ec72bc2b82dafed89ba82c417b`.

The stored subject is exactly the defined canonical preimage, with no
`independent_review` field and the prescribed subject schema. Current verification
digest remains `ece125e0466cd89b280221bb89b9d38389fe060c7fb19a4a35d506ff41828a28`;
historical generating digest remains
`105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`.
Their roles are distinct. Review raw provenance, the identified source transition,
lemma premises and counts binding separately from assertions of past execution.
Existing reports reviewed the lemma/code; they are not this new subject-bound record.

The raw record of this independent review, reviewer, strict UTC and note are still
missing. Do not invent them or perform operational adoption to complete a record.
Subject acceptance authenticates no owner approval or past execution and certifies
no overall Freeze 1 readiness. Original runtime evidence contains only CPython
3.13.12 / Unicode 15.1.0; no proposed runtime/dependency lock was assembled.

## Completed checks and boundaries

The assembly receipt records exact commands: sixteen check categories and a
filesystem replay passed for 52 bound artifacts, three specification components,
fourteen copy equalities and 61 protected files. Actual source hashes, canonical
records, transcription fragments, shared-origin section sets, version pin and the
existing counts receipt were checked. No full test rerun was needed.

Final RuleApplicability v3 and HistoricalLedgerReconciliation v1 wrappers remain
unassembled until these four reviews exist. Drafts are expressly not accepted-schema
records. Full provenance/compatibility, input/runtime/dependency and Freeze 1 evidence
are not claimed; no dummy FreezeManifest or actual InputBinding was constructed.
Future final-wrapper assembly/validation requires its own bounded authorization.

Preserve all six reports, private originals and assembled subjects. The reviewed R4
non-normative limitation remains; do not classify source changes by hash inequality.
Static source checks remain hash-bound reviewed checks, not a sandbox. No screening,
ranking/sampling, packets, adoption/sealing, freezes, labeling, operational tools,
AWS/external API calls or model/router execution is authorized by this handoff.
The handoff is prepared only; dispatch to Claude has not occurred.
**Freeze 1 readiness remains unestablished.**
