# Reviewer Protocol v2: current normative rules v1

Identifier: `reviewer-protocol-v2-current-rules-v1`.
Date: 2026-10-02. Current consolidation under owner decisions D1-D8.

This separate document consolidates accepted proposed sections 1-3 and the owner
resolutions. It does not rewrite the original proposal or claim retrospective
finalization, past execution, corrected population audit or Freeze 1 readiness.
Claude's independent semantic/code review of this consolidation remains pending.
No semantic-approval declaration is made on Claude's behalf.

Normative sources: unchanged proposed-rule-specification sections 1-3, S-576 and
owner records O-430/O-051/O-526/O-b6e; applicability is resolved by the current
D1-D8 owner record (raw SHA-256
78e34cedfb33e6deb3d328c2373f251bd94bc0b4ed714738678f646dfdfd8920).
S-576 retains complete:false; its meaning is unestablished. Its independently
verified content is accepted for this current consolidation without asserting
that flag is erroneous or that missing history has been recovered.

Finite vocabularies, grammar, boundaries, normalization, algorithms and matching
behavior are normative. Implementation pattern bytes follow the deterministic
construction convention and remain separately hash-bound. Reason codes, field
names, subrule IDs and serialization are versioned implementation formats; they
do not redefine rule semantics. All original evidence and decision-chain bytes
remain preserved separately. No code-derived pattern is authoritative evidence.

## 1. Common matching contract

### 1.1 Original question

The question is an unchanged Unicode string. Its question hash is SHA-256 of the strict
UTF-8 encoding, with no newline added.

- **Source:** S-576 §1, input views (lines 15–17).
- **Owner:** O-526 §1: "Questions remain verbatim".

### 1.2 Eligibility view `q`

`q = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", question).casefold()).strip()`

- **Source:** S-576 §1, lines 18–22.

### 1.3 Separate historical similarity view

This view is defined in section 3.3. It is never `q`.

- **Source:** S-576 §1, line 23 and §6.
- **Owner:** O-526: "matcher normalization and historical similarity preprocessing are
  separate registered views".

### 1.4 Runtime pin

CPython 3.13.12 with Unicode data 15.1.0. Any runtime change requires validation and a
new implementation digest.

- **Source:** S-576 §1, line 25.
- **Owner:** O-b6e §3 additionally retains the exact nine-field runtime contract for
  bindings.

### 1.5 Regex conventions (E01–E04 and the E03 subrules)

These come from S-576 §1, matching conventions (lines 27–49):

- Use Python `re` on `str` patterns.
- Set none of `IGNORECASE`, `ASCII`, `LOCALE`, `MULTILINE` or `DOTALL`. Case handling
  comes only from `casefold()`.
- The left word boundary is `(?<!\w)` and the right is `(?!\w)`.
- `\w` uses pinned-Python Unicode semantics, and the underscore is a word character.
- A space in a grammar means exactly one ASCII space in `q`.
- Punctuation is not removed. It breaks an internal phrase unless the grammar permits it.
- There is no stemming, synonym expansion, language model or semantic parser.
- For finite alternatives, escape each literal and order alternatives by descending
  length, then Unicode lexicographic order.
- Use `re.finditer` and retain its non-overlapping matches per registered pattern.
  Different patterns are evaluated independently.
- All spans are offsets into the normalized `q`.

## 2. Rules

### E01 — material-mention matcher (metadata only)

**Vocabulary (12):** `table, tables, chart, charts, graph, graphs, diagram, diagrams,
screenshot, screenshots, image, images`.

- `figure` and `figures` are deliberately absent.
- No other inflections are registered.

**Matcher, as displayed in S-576:**
`(?<!\w)(?:table|tables|chart|charts|graph|graphs|diagram|diagrams|screenshot|screenshots|image|images)(?!\w)`
The source says its line breaks are formatting only.

**Derived order under §1.5:**
`screenshots|screenshot|diagrams|diagram|charts|graphs|images|tables|chart|graph|image|table`.
Both orders produce identical matches. Under D2, vocabulary, grammar and behavior
are normative; deterministic implementation bytes use the derived order in section
1.5. Alternative order or escaped/literal spaces with identical behavior are not
separate amendments. No general regex-equivalence engine is specified.

**Behavior:**
- There are no intervening tokens.
- Apostrophe and hyphen act as boundaries (`table’s` and `table-based` match).
- `datatable`, `tablespoon` and `table_name` do not match.

**Disposition: none. E01 is a metadata flag with no eligibility effect.**
- Every E01 match is preserved in the ledger.
- If E01 is the only match, the record remains SCREEN_PASS.
- E01 never gates E02 or E03.
- E01 prevalence is reported separately.

**Sources:**
- Vocabulary and matcher: S-576 §2, E01 (lines 53–83).
- Disposition: O-051, "OWNER DECISION — E01" (lines 9–45), superseding S-576 line 80
  ("Disposition: DEPENDENCE_EXCLUDED").
- Reaffirmed by O-526 §1 and O-b6e item 1.

### E02 — deictic material references (DEPENDENCE_EXCLUDED)

**Sets:**
- **R (11):** `this, that, these, those, following, above, below, attached, provided,
  shown, given`.
- **A (6):** `financial, annual, quarterly, consolidated, summary, detailed`.
- **M (26):** `table, tables, chart, charts, figure, figures, graph, graphs, diagram,
  diagrams, document, documents, report, reports, passage, passages, excerpt, excerpts,
  statement, statements, data, information, result, results, value, values`.

**Grammar:** `WB R (" " A){0,2} " " M WB`.
Derived form: `(?<!\w)(?:R)(?: (?:A)){0,2} (?:M)(?!\w)`.

**Behavior:**
- At most two intervening tokens, and each must be a member of A.
- Modifier order and repetition are free.
- No determiner, arbitrary adjective or punctuation may intervene.
- No other inflections.

**Source:** S-576 §2, E02 (lines 85–136).

**Owner:** O-051: "E02/E03 continue to produce DEPENDENCE_EXCLUDED". O-526: "finalized
finite definitions".

### E03 — navigation and indexed references (DEPENDENCE_EXCLUDED)

E03 matches when any subrule matches. Record E03, every matching subrule, and any
overlapping E01 or E02 matches. A bare `above` or `below` does not match.

**Sets:**
- `M` and `A` as in E02.
- **P:** `above, below, following, preceding`.
- **L:** `above, below`.
- **V:** `shown, reported, presented, listed, indicated, displayed`.
- **D:** `directly, immediately`.
- **T:** `attached, provided`.
- **PREP:** `in, from, according to`.

**E03a — positional material (separate E03a_pre / E03a_post patterns):**
- Form 1: `WB P (" " A){0,2} " " M WB`.
- Form 2 (postpositive): `WB M " " L WB`.

**E03b — displayed or reported navigation (E03b_location / E03b_material):**
- Form 1: `WB V [" " D] " " L WB`. This matches inside `as shown above` without
  consuming `as`.
- Form 2: `WB V " in " ["the "] (P ∪ T) (" " A){0,2} " " M WB`.

**E03c — attached or provided material (D8 correction):**
- `WB PREP " " ["the "] T (" " A){0,2} " " M WB`.
- PREP is exactly in, from and the literal two-word phrase according to.
- Do not split according to into according and to. Neither standalone form is
  registered as an E03c preposition. E02 may independently match the same tail.
- No other prepositions are accepted.

**E03d–g — indexed references.**

Primitives:
- **N** is `(?:0|[1-9][0-9]*)`. These are lexical identifiers, so leading-zero forms are
  not recognized.
- **RLETTER** is one ASCII `a–z`.
- **CLETTER** is one to three ASCII `a–z`.
- **ADDRESS** is CLETTER immediately followed by N.

Post-number rule: after any numeric portion, reject an immediately following ASCII
digit [0-9], or a comma or period followed by an ASCII digit [0-9] (D5).

Wrappers: `ID`, `#ID`, `# ID` and `(ID)`. There is exactly one space between the noun and
the wrapper, and the common boundaries apply around the whole noun-plus-wrapper.

| Subrule | Nouns | ID |
|---|---|---|
| E03d | `row, rows` | N or RLETTER |
| E03e | `column, columns` | N or CLETTER |
| E03f | `cell, cells` | ADDRESS, N or RLETTER |
| E03g | `table, tables, chart, charts, graph, graphs, diagram, diagrams, figure, figures, image, images, screenshot, screenshots` | N or RLETTER |

There is no grammar for ranges, ordinal words, Roman numerals or descriptive row names.
A range matches its first reference.

**Source:** S-576 §2, E03 (lines 138–249).

### E04 — previous-interaction references (DEPENDENCE_EXCLUDED)

**Sets:**
- **FIRST:** `previous, preceding, earlier, last`.
- **SECOND:** `question, questions, answer, answers, response, responses, discussion,
  discussions`.

**Grammar:** `WB FIRST " " SECOND WB`. No intervening token and no other inflections.
`previous owner answer` is not registered.

**Source:** S-576 §2, E04 (lines 251–276).

### E05 — bare unresolved requests (DIAGNOSTIC_ONLY)

**P05 has exactly 42 whole-question phrases:**
- `what {does,did} {this,that,it} mean`
- `what {is,was} {this,that,it}`
- `what {are,were} {these,those,they}`
- `how {do,did} {these,those,they} compare`
- `how {does,did} {this,that,it} compare`
- `{explain,summarize} {this,that,these,those,it,them}`

The brace form above summarizes S-576's normative literal list below
(S-576 lines 283-329), independently verified against that literal source. Count is 42:

- `explain it`
- `explain that`
- `explain them`
- `explain these`
- `explain this`
- `explain those`
- `how did it compare`
- `how did that compare`
- `how did these compare`
- `how did they compare`
- `how did this compare`
- `how did those compare`
- `how do these compare`
- `how do they compare`
- `how do those compare`
- `how does it compare`
- `how does that compare`
- `how does this compare`
- `summarize it`
- `summarize that`
- `summarize them`
- `summarize these`
- `summarize this`
- `summarize those`
- `what are these`
- `what are they`
- `what are those`
- `what did it mean`
- `what did that mean`
- `what did this mean`
- `what does it mean`
- `what does that mean`
- `what does this mean`
- `what is it`
- `what is that`
- `what is this`
- `what was it`
- `what was that`
- `what was this`
- `what were these`
- `what were they`
- `what were those`

**Algorithm:**
`match = q in P05 or (q.endswith(("?", ".")) and q[:-1] in P05)`

- The whole normalized question must match. The E05 normalized span covers all
  of q, including its permitted final punctuation (D5).
- No prefix, suffix or extra punctuation is allowed, and at most one final `?` or `.`.
- Quotes are not removed.
- Possessive references are not registered.
- A higher-precedence rule can win.

**Source:** S-576 §2, E05 (lines 278–354).

**Owner:** O-430 §4 (conservative; possessives such as "its revenue" are not
unresolved). O-526 (finalized). O-051 Phase 1 lists "E05 whole-question matching" for
fixture verification.

### E06 — explicit template defects (DIAGNOSTIC_ONLY)

**E06a — placeholders.**
- **H (15):** `company, period, year, date, table, chart, figure, document, context,
  question, amount, value, placeholder, todo, tbd`.
- **Delimiter pairs:** `[ ]`, `< >`, `{ }`, `{{ }}` and `${ }`.
- Zero or one normalized ASCII space is independently allowed immediately inside
  each delimiter; the two sides need not be symmetric (D3).
- The payload must spell a member of H exactly.
- No other variable name, expression, dotted path or delimiter is recognized.

**E06b — insertion markers.**
- **I (12):** H without `placeholder`, `todo` and `tbd`.
- **Payload:** `insert " " I` or `insert " " I " here"`.
- **Delimiters:** square or angle brackets only, with zero or one space inside each
  delimiter.
- Delimiters must pair: square with square, angle with angle. Independent inner
  spaces are permitted on each side (D3).
- A bare insertion command is not recognized.

**E06c — standalone wrapped tokens.**
- The tokens are `__placeholder__`, `__todo__` and `__tbd__`, with the common
  boundaries.
- Bare `TODO`, `TBD` and `placeholder` are not E06 defects.

**E06d — trailing ellipsis.**
- The matcher is `(?<!\.)\.{3}$` on `q`.
- NFKC turns a single U+2026 into three periods, so it matches. Two U+2026 become six
  periods and do not match.
- An internal ellipsis does not match.

**Evaluation rules:**
- Bracketed forms are recognized anywhere in `q`, with no outer word boundaries.
- Each delimiter form is evaluated independently, and nested registered forms may yield
  several spans.
- All subrule matches are preserved.

**Source:** S-576 §2, E06 (lines 356–435).

**Owner:** O-430 §5. O-051 Phase 1 ("E06 Unicode ellipsis behavior"). O-526.

### E07 — invalid record or source binding (INPUT_INVALID)

**Inputs:**
- The original fields and an immutable reference index derived from the hash-verified
  frozen pilot.
- Metadata is not case-folded or normalized.
- **Index fields:** `cand_id`, original question SHA-256, `source`, `sampling_stratum`,
  `source_revision`, `context_group`.
- **Required record fields:** those six, with the actual `question` string in place of
  the hash.

**E07 matches if any of these holds:**
1. The record is not a JSON object with unique keys.
2. A required field is missing or is not a string.
3. `cand_id` fails a full match of `c_[0-9a-f]{10}`, or is absent from the index.
4. The source and stratum are not one of these exact pairs: `tatqa/T1_qa`,
   `finqa/T1_qa`, `finlfqa/num`, `finlfqa/interp`, `finlfqa/other`, `finlfqa/mixed`.
5. The metadata differs from the index.
6. The question is not strictly UTF-8 encodable.
7. The eligibility view is empty.
8. The original-question hash differs from the index.

**Consequences:**
- Text is evaluable when a uniquely parsed valid JSON object has a string question
  that is strictly UTF-8 encodable and has a nonempty eligibility view. Metadata
  failures, unknown IDs and question-hash mismatches alone do not prevent E01-E06
  evaluation (D4).
- Invalid JSON, duplicate keys, a missing/nonstring question, invalid UTF-8, or an
  empty eligibility view prevent text-rule evaluation. Extra fields are allowed.
  NaN/Infinity constants are rejected. INPUT_INVALID retains precedence (D4).
- If no safely usable question exists, mark the text rules NOT_EVALUABLE; do not infer
  them. Reason strings and evidence serialization are implementation formats, not
  amendments to these semantics (D5).
- A population-file hash mismatch, or a duplicate index ID, aborts the audit. Neither
  is converted to per-record dispositions.
- Routing labels, source answers and provisional labels are never inputs.

**Source:** S-576 §2, E07 (lines 437–477).

**Owner:** O-051 Phase 1 ("E07 invalid-record behavior"). O-526.

### Precedence and ledger

**Winning disposition:**
`INPUT_INVALID > DEPENDENCE_EXCLUDED > DIAGNOSTIC_ONLY > SCREEN_PASS`.
E01 contributes no disposition.

**Ledger:**
- Evaluate every safely evaluable rule.
- Preserve all matched rule IDs in ascending order, the subrule identifiers, the
  normalized spans and the E07 reasons.
- The winning disposition never erases a lower-precedence finding.

**Exposure flags** are kept separate from eligibility:
`eligibility_disposition`, `direct_known_exposure`, `exposed_native_context_group` and
`direct_near_duplicate_exposure`.

**Final eligibility** is `disposition == SCREEN_PASS` with no exposure flag. Reports
distinguish raw SCREEN_PASS from final unexposed SCREEN_PASS.

**Sources:**
- S-576 §4 (lines 501–535).
- O-430 §6.
- O-051 ("allow a matched rule with no exclusion effect"; "E01-only matches remain
  SCREEN_PASS").
- O-526 §1.

## 3. Exposure and direct-pair similarity (rule roles: exposure and grouping/similarity)

### 3.1 Known exposure inventory

- **Scope:** every v1.1/v1.2 packet item; the removed control and the original
  historical packet; documented planning, handoff, owner-audit and reviewer-request
  disclosures; and other documented exposure.
- **Categories (7):** `historical_trial_packet`, `removed_control`,
  `planning_document_disclosure`, `work_history_disclosure`, `owner_audit`,
  `reviewer_request` and `other_documented_exposure`.
- **Identity:** resolved by candidate ID, then exact original text, then equality of the
  registered normalized text. All exact-text matches are kept. Partial quotations are
  never guessed. An unresolved entry blocks Freeze 1.
- Questions outside the pool are kept with a null candidate ID and their hash.
- Derived (context or similarity) exclusions are **never** promoted to direct seeds.
- The inventory is *known* exposure only.

**Sources:** S-576 §5 (lines 537–611). O-430 §7. O-051 Phase 2. O-526 §1: authoritative
inventory accepted (15 / 48 / 63 / 1,480 / 0). The inventory was not inspected for this consolidation.

### 3.2 Native context group

- The key is `(source, context_group)`.
- A candidate is excluded when it shares a group with a directly exposed pilot candidate.
- This exclusion stays separate from the similarity exclusion.

**Sources:** S-576 §8 (line 738). O-430 ("Context-group exclusions remain separate").
O-526 §1.

### 3.3 Historical similarity view and functions

This is the pinned `select_pilot.py` (SHA-256 `752a65fa…`), functions `grams(s, n=4)`
and `cos(a, b)`:

- `s.lower()`, not casefold.
- Collapse `\s+` to one space.
- No strip and no NFKC.
- Overlapping code-point 4-grams. A string shorter than 4 characters becomes one gram
  of the whole string; an empty string gives the empty gram.
- A zero norm gives 0.0.
- Integer sums, with the historical float square root and division.
- No epsilon or rounding.
- Arithmetic or runtime errors abort the analysis.

**Source:** S-576 §6 (lines 613–653).

**Owner:** O-430 §8. O-526 ("faithfully isolate the frozen historical pure grams/cos
implementation").

### 3.4 Exposure exclusion

- Compare each candidate (argument `a`) with every directly exposed reference
  (argument `b`).
- Exclude **iff any score ≥ 0.90**, compared unrounded with the binary literal `0.90`.
- Record every pair that reaches the threshold. In the deduplicated computational
  register, use deterministic question SHA-256 ordering for references; preserve
  all provenance, matched rules and normalized spans (D5).
- There is no transitive propagation.
- A directly exposed candidate may also match itself; report that overlap.

**Sources:** S-576 §6, exposure exclusion (lines 655–665). O-430 decision. O-526.

### 3.5 Selection diversity

- Under the separately frozen ranking, accept a candidate only if its context group has
  not already been accepted, **and** every direct similarity to an already-accepted
  external item is **< 0.90**.
- Compare in acceptance order. Skip conflicts and continue.
- Anchors and diagnostics are excluded from this comparison.

**Sources:** S-576 §6, selected-packet diversity (lines 667–677). O-430. O-526 §1.

### 3.6 Similarity evidence fields

Record:
- the IDs and hashes;
- the algorithm and runtime digests;
- the unrounded score with round-trip precision, plus `float.hex()`;
- the threshold and the Boolean result;
- the purpose;
- the pairs and their order.

**Source:** S-576 §6 (lines 679–689).

## 4. Registration and implementation-format decisions

D6 treats mismatched revision and mismatched group as separate E07 fixtures:
89 text-rule fixtures plus 11 E07 fixtures = 100 registered fixtures (50 positive,
50 negative). The 37 supplementary implementation checks introduce no normative
rules. Recovered audit summaries report their result; registration details and
historical execution authenticity are not established by hash agreement.

Retain reviewed subrule IDs (E03a_pre, E03a_post, E03b_location, E03b_material,
E03c, E03d-E03g, E06a_0-E06a_4, E06b_0-E06b_1, E06c, E06d) and all independent
matches/spans. These IDs, ledger field names, reason strings and evidence bytes are
separately versioned implementation contracts. E03c correction changes provenance
matches/spans; it does not justify rewriting or automatically adopting old ledgers.

The future semantic review must cite this document hash and applicable mechanical
contract hash, compare every transcription and shared-origin section, and review
historical-ledger implications separately. No actual RuleSpecification/InputBinding
bundle is constructed here.
