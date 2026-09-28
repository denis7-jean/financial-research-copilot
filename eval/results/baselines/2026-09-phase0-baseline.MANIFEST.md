# Phase 0 baseline — record manifest

This is the first trustworthy baseline for the copilot. **Do not edit the result files.** The
hashes below make any change detectable.

| Item | Value |
|---|---|
| Results | `2026-09-phase0-baseline.json` — SHA-256 `b24cb18514a824cf844baf697006c93543ef5d778f8e361a89d68572ea7ad442` |
| Console log | `2026-09-phase0-baseline.console.log` — SHA-256 `4c403ddaae39850e70986336f0333ecd491a803a61b20729820419ad1c5fe7dc` |
| Run ID | `6a13ffb1634e40258f283838935ff339` |
| Run window | 2026-09-28 02:32:03 → 02:37:47 UTC (one run; no retries) |
| Code under test | `a9906097e97fe7279c8b612bd691e909707af5ae` (clean tree), local and in-process — **not** the deployed June Lambda build |
| Dataset | 34 cases (19 gated); SHA-256 `f1d0da26f767b4025dd15a511e8aff1eefafae433ed0c438e4f542d46a554d9d` |
| Corpus | 2,220 vectors; metadata SHA-256 `f771ba6c…` (post-Visa-migration); FAISS index SHA-256 `3d2b3ebd…` |
| Models | System `us.anthropic.claude-haiku-4-5-20251001-v1:0` (default inference parameters). Judge `us.anthropic.claude-sonnet-4-6` (temperature 0, maxTokens 400) |
| Validity | `valid_for_baseline: true`: 34/34 cases; no infrastructure, judge or harness failures |
| Enforced gates | Context relevance 100% (19/19), faithfulness 94.7% (18/19): **pass** |
| Cost ceiling | $5.00; estimated spend $1.11 at list prices |

## Process exit code

`python -m eval.llm_judge` ended with **exit code 1**, from a `TypeError` in the final
`print("Gates: ...")` line of the `__main__` block. That line indexes a `Gate` dataclass like a
dict.

- It ran **after** `run_evaluation()` had written the results file and printed the summary.
- The results are complete and consistent: same `run_id`, 34 rows.
- The traceback appears mid-log only because stderr is unbuffered while stdout was buffered.
- Not fixed in this run, to keep the code unchanged.

## Interpretation caveats

- **Single run** of a system that uses default (non-zero) temperature.
- **Evidence-rank misses are a lower bound.** L06 and N06 were answered from retrieved chunks
  that phrase the figure differently from the markers.
- **Two of the summary-grounding passes are refusals.** L19 and N14 make no claims, so they
  score 5.
- **Latency was measured in-process.** It excludes Lambda initialization and HTTP.
