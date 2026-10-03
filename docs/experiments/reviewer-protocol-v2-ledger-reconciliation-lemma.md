# Identified historical ledger: eligibility-object reconciliation lemma v1

This is a proposed lemma requiring independent review. It is not a review record,
execution receipt, adoption, approval or Freeze 1 readiness declaration.

## Subjects and provenance

- Original final-1 manifest raw SHA-256:
  `057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4`.
- Its unchanged population_ledger.jsonl raw SHA-256:
  `6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2`.
- Historical eligibility.py raw SHA-256:
  `d3030b229c498db254ba936352d40262a24ad2df5a114fa2c0432d69f8811e37`.
  The bytes at 182f131 and 34a3edd agree. The sixteen generating files at
  182f131 reproduce the manifest's implementation digest using SHA-256 of the
  canonical filename-to-raw-file-SHA-256 map, including its terminal LF:
  `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`.
- Current eligibility.py at bf8295b raw SHA-256:
  `04e36326c5445419a5e9ec0e6517c4d9623c52f6688c27b095005da597c3cc92`.
  It remains a separately bound member of current verification and selection
  bundles. Neither current bundle replaces the historical generating digest.

The original manifest and Git blobs were read and hashed without executing the
historical sources. Hash agreement establishes byte relationships, not who
approved them, historical execution, or rule authority. This claim assumes the
historical ledger records the old classifier's outputs for the original inputs
and reference index; counts and source hashes alone do not prove that assumption.
The unchanged normalization, reference bindings and pinned runtime remain required.

## Complete source diff

There are three diff hunks, implementing exactly two semantic corrections:

1. alternatives(words) now assigns literals = words.split() for string arguments,
   otherwise literals = words, and sorts set(literals). Previously it always
   sorted set(words.split()). All other call sites still pass the identical
   strings, so their alternatives are byte-identical.
2. E03c alone passes the tuple ("in", "from", "according to") instead of the
   whitespace-split string "in from according to". The old finite alternatives
   were according, from, in, to; the corrected ones are according to, from, in.
3. In classify, only the empty-view branch additionally assigns usable = False
   before appending normalized_empty_question. No reason, normalized view,
   disposition, match, precedence, reference or other operation changes there.

No other source lines change. Other eligibility source code, patterns, sorting,
textual traversal, E05, E06, E07 and return-object construction are unchanged.

## Containment and row-object equality

Consider the same original question, reference index and pinned runtime. Both
sources produce the same normalized q. A corrected E03c occurrence beginning with
in or from is also an old E03c occurrence with the same boundary-valid start and
tail. A corrected according to occurrence contains an old occurrence beginning
at to: its preceding ASCII space satisfies (?<!\\w), and the identical remaining
suffix and end satisfy the old tail and (?!\\w). The optional the and the
attached/provided, zero-to-two adjectives, material suffix are identical.

The implication concerns existence of a match on the same record, not identical
spans. Python finditer's non-overlapping traversal cannot turn existence of a
valid old occurrence into an empty old match list: if a preceding old match
suppresses that occurrence, that preceding match already witnesses old E03c.
Thus any corrected E03c match implies at least one old E03c match.

If an old row has no E03 rule and no E03c match, its old E03c match list is empty;
containment makes its corrected E03c match list empty too. All other pattern
matches and their traversal order are unchanged. Excluding any old E03 rule is
a conservative stronger prerequisite than excluding E03c alone. If the row also
has no normalized_empty_question reason, the changed usable assignment cannot
affect it: any execution of that empty-view branch appends that very reason in
both versions. Every returned field (rules, matches, invalid, disposition,
text_evaluable, normalized) therefore agrees, including list ordering. The
unchanged canonical serializer yields byte-identical eligibility objects.

## Population premises and distinct capacity argument

The verified counts-only check found 104 rows, zero rows with E03 in rules, zero
with E03c in matches, zero in their union, and zero with normalized_empty_question
in invalid. They must be bound to the exact ledger bytes and independently
reviewed alongside this lemma. A declared aggregate or provenance flag cannot
substitute for a captured-byte recount. Nonzero affected counts or a wrong total
fail this specific reconciliation contract; no re-screening is performed by it.

The broader disposition argument is separate: E03c tails also match E02, and the
empty-view flag correction concerns already-invalid rows. Disposition/capacity
invariance alone does not establish equality of match spans, rule IDs or flags.
The lemma above establishes row-object equality only under its stronger premises.

Synthetic probes are supporting illustrations, not an exhaustive proof or
historical execution evidence. This document does not discharge independent
review, historical input/runtime provenance, actual wrapper review or any other
compatibility prerequisite. Future operational selection tools must enforce
applicable adoption/reconciliation checks; the pure selector API is unchanged.
