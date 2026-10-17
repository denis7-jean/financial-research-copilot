The `select_pilot.py.source` file is a byte-identical source-only copy of the
historical `heldout-external/pilot-v1/select_pilot.py` selector, SHA-256
`752a65fa744f04ae6854b2c8429fad9c43d3fc365fe763fb5d6600e64d7586a4`.
It contains no population, questions or execution outputs. Tests read and hash
these bytes but never import or execute this file. Its historical paths remain
unchanged and are not runtime destinations.

This supplies the synthetic fixtures in a standalone checkout. Production
Reviewer evidence remains external and must satisfy its original content and
origin checks. An explicit `REVIEWER_TEST_EVIDENCE_ROOT` still selects external
source bytes under the same mandatory hash; it does not override that hash.
