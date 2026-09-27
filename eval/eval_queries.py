"""Labeled evaluation dataset.

Every case carries explicit labels so metrics no longer depend on what the
router happened to do:

- expected_route: the route the router *should* choose, per the taxonomy in
  RouterAgent's system prompt ("qa" = specific fact/figure; "summarize" =
  overview, narrative, risks, themes, strategy).
- route_label_status: "clear" labels are gated; "needs_review" labels are
  reported but not gated until a human adjudicates them.
- expected_behavior: "answer" (the filings contain the answer), "abstain" (they
  do not; the system should say so), or "either" (not scored for abstention).
- companies: tickers whose filing should supply the retrieved context. Used for
  the deterministic cross-company contamination metric.
- reference_answer / reference_source: ground truth checked against the local
  PDFs in ../data (file, page). Used for answer correctness.
- forbidden_facts: strings that must not appear in the answer (case-insensitive).
  Used for out-of-corpus questions whose nearest in-corpus neighbour could leak
  its figures, e.g. Visa's numbers in an answer about Mastercard.
- replaces: id of the historical case this one superseded, if any.

CORPUS (2026-09-27): the fifth company is Visa Inc. Its FY2025 10-K (EDGAR
accession 0001403161-25-000089, fiscal year ended September 30, 2025) was
originally uploaded as docs/mastercard-10k-fy2025.pdf and is being renamed to
docs/visa-10k-fy2025.pdf. Mastercard is NOT in the corpus: Mastercard questions
are out-of-corpus and the correct behavior is to abstain.

History: the original 20 queries (June 2026) are kept in LEGACY_QUERIES_2026_06.
Two of them (L11, L16) asked for Mastercard summaries and were replaced by Visa
equivalents (V01, V02). Archived results for the original set are in
eval/results/legacy/.
"""
from dataclasses import dataclass, field
from typing import Literal

Route = Literal["qa", "summarize"]
Behavior = Literal["answer", "abstain", "either"]
LabelStatus = Literal["clear", "needs_review"]


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    category: str
    expected_route: Route
    route_label_status: LabelStatus
    expected_behavior: Behavior
    companies: tuple[str, ...] = ()
    reference_answer: str | None = None
    reference_source: str | None = None
    legacy: bool = False
    notes: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    forbidden_facts: tuple[str, ...] = ()
    replaces: str | None = None

    @property
    def gated_for_retrieval(self) -> bool:
        """Population for the enforced context-relevance and faithfulness gates."""
        return (
            self.expected_route == "qa"
            and self.expected_behavior == "answer"
            and self.route_label_status == "clear"
        )


JPM = "jpmorgan-chase-10k-fy2025.pdf"
GS = "goldman-sachs-10k-fy2025.pdf"
BAC = "bank-of-america-10k-fy2025.pdf"
BLK = "blackrock-10k-fy2025.pdf"
VISA = "visa-10k-fy2025.pdf"

MASTERCARD_OUT_OF_CORPUS_NOTE = (
    "Mastercard is not in the corpus (Visa is the fifth company). Retrieval will "
    "likely return Visa chunks; answering with Visa's figures is a failure."
)

EVAL_CASES: list[EvalCase] = [
    # --- Legacy set (original 20 queries, verbatim) --------------------------
    EvalCase("L01", "What was JPMorgan Chase's total net revenue for fiscal year 2025?",
             "numeric_qa", "qa", "clear", "answer", ("JPM",),
             "Total net revenue was $182,447 million (about $182.4 billion) for 2025.",
             f"{JPM} p46, p49", legacy=True),
    EvalCase("L02", "What was Goldman Sachs net earnings for fiscal year 2025?",
             "numeric_qa", "qa", "clear", "answer", ("GS",),
             "Net earnings were $17.18 billion for 2025 (vs $14.28 billion in 2024).",
             f"{GS} p67", legacy=True),
    EvalCase("L03", "What is Mastercard's total net revenue for fiscal year 2025?",
             "out_of_corpus", "qa", "clear", "abstain", (),
             legacy=True, notes=MASTERCARD_OUT_OF_CORPUS_NOTE, tags=("mastercard",),
             forbidden_facts=("40,000", "40.0 billion", "40 billion")),
    EvalCase("L04", "What was BlackRock's total assets under management in 2025?",
             "numeric_qa", "qa", "clear", "answer", ("BLK",),
             "AUM was $14,041,518 million (about $14.04 trillion) at December 31, 2025.",
             f"{BLK} p4, p43", legacy=True),
    EvalCase("L05", "What was Bank of America's net income for fiscal year 2025?",
             "numeric_qa", "qa", "clear", "answer", ("BAC",),
             "Net income was $30,509 million (about $30.5 billion) in 2025.",
             f"{BAC} p29", legacy=True),
    EvalCase("L06", "What was JPMorgan Chase's return on equity in 2025?",
             "metric_qa", "qa", "clear", "answer", ("JPM",),
             "Return on common equity (ROE) was 17% for 2025.",
             f"{JPM} p46, p49", legacy=True),
    EvalCase("L07", "How many employees did JPMorgan Chase have in 2025?",
             "metric_qa", "qa", "clear", "answer", ("JPM",),
             "318,512 employees as of December 31, 2025.",
             f"{JPM} p9, p46", legacy=True),
    EvalCase("L08", "What was Mastercard's net income margin in 2025?",
             "out_of_corpus", "qa", "clear", "abstain", (),
             legacy=True, notes=MASTERCARD_OUT_OF_CORPUS_NOTE, tags=("mastercard",),
             forbidden_facts=("20,058", "50.1%", "50.1 %")),
    EvalCase("L09", "What dividends did Goldman Sachs pay in fiscal year 2025?",
             "metric_qa", "qa", "clear", "answer", ("GS",),
             "Common stock dividends declared were $14.00 per common share for 2025 "
             "(vs $11.50 in 2024).",
             f"{GS} p212", legacy=True,
             notes="Filing reports dividends declared; answers citing preferred dividends "
                   "in addition are acceptable if the common figure is correct."),
    EvalCase("L10", "Which had higher net revenue in 2025, JPMorgan Chase or Goldman Sachs?",
             "cross_company", "qa", "clear", "answer", ("JPM", "GS"),
             "JPMorgan Chase: total net revenue $182,447 million; Goldman Sachs: net revenues "
             "$58.28 billion. JPMorgan Chase was higher.",
             f"{JPM} p49; {GS} p67", legacy=True),
    EvalCase("L12", "Summarize the key risks in Goldman Sachs 2025 annual report.",
             "summarize", "summarize", "clear", "answer", ("GS",), legacy=True),
    EvalCase("L13", "What are the main business segments of JPMorgan Chase?",
             "summarize", "summarize", "needs_review", "answer", ("JPM",),
             "Three reportable business segments: Consumer & Community Banking (CCB), "
             "Commercial & Investment Bank (CIB), and Asset & Wealth Management (AWM), "
             "plus Corporate.",
             f"{JPM} p9 (LOB breakdown)", legacy=True,
             notes="Taxonomy says 'overview' -> summarize, but this is a factual list; the "
                   "summarize path is ungrounded. Needs a product decision."),
    EvalCase("L14", "Summarize BlackRock's investment strategy as described in their 2025 10-K.",
             "summarize", "summarize", "clear", "answer", ("BLK",), legacy=True),
    EvalCase("L15", "What is Bank of America's approach to managing credit risk?",
             "summarize", "summarize", "clear", "answer", ("BAC",), legacy=True),
    EvalCase("L17", "What is a financial statement?",
             "boundary", "qa", "needs_review", "either", (),
             legacy=True, notes="General-knowledge question outside the filings. Is a generic "
                                "definition acceptable, or should the system decline?"),
    EvalCase("L18", "What was Apple's revenue in 2025?",
             "out_of_corpus", "qa", "clear", "abstain", (), legacy=True),
    EvalCase("L19", "Goldman Sachs 2025",
             "boundary", "qa", "needs_review", "either", ("GS",),
             legacy=True, notes="Underspecified. Labeled qa because qa is the grounded fallback."),
    EvalCase("L20", "What was JPMorgan Chase's revenue and also summarize their risk factors?",
             "boundary", "qa", "needs_review", "answer", ("JPM",),
             "Total net revenue was $182,447 million for 2025 (risk-factor portion not "
             "reference-graded).",
             f"{JPM} p49", legacy=True,
             notes="Multi-intent. Only one route is possible today."),

    # --- Added in Phase 0: more gated QA cases with verified references ------
    EvalCase("N01", "What was JPMorgan Chase's net income in 2025?",
             "numeric_qa", "qa", "clear", "answer", ("JPM",),
             "Net income was $57,048 million for 2025.", f"{JPM} p46, p49"),
    EvalCase("N02", "What were JPMorgan Chase's diluted earnings per share for 2025?",
             "metric_qa", "qa", "clear", "answer", ("JPM",),
             "Diluted EPS was $20.02 for 2025.", f"{JPM} p46, p49"),
    EvalCase("N03", "What was Bank of America's total revenue, net of interest expense, in 2025?",
             "numeric_qa", "qa", "clear", "answer", ("BAC",),
             "Total revenue, net of interest expense, was $113,097 million for 2025.", f"{BAC} p29"),
    EvalCase("N04", "What was Bank of America's return on average common shareholders' equity in 2025?",
             "metric_qa", "qa", "clear", "answer", ("BAC",),
             "Return on average common shareholders' equity was 10.59% for 2025.", f"{BAC} p29"),
    EvalCase("N05", "How many employees did Bank of America have at the end of 2025?",
             "metric_qa", "qa", "clear", "answer", ("BAC",),
             "Approximately 213,000 employees at December 31, 2025.", f"{BAC} p5, p29"),
    EvalCase("N06", "What was Goldman Sachs' return on equity for 2025?",
             "metric_qa", "qa", "clear", "answer", ("GS",),
             "ROE was 15.0% for 2025.", f"{GS} p67"),
    EvalCase("N07", "What were Goldman Sachs' net revenues in 2025?",
             "numeric_qa", "qa", "clear", "answer", ("GS",),
             "Net revenues were $58.28 billion for 2025.", f"{GS} p67"),
    EvalCase("N08", "What was BlackRock's total revenue in 2025?",
             "numeric_qa", "qa", "clear", "answer", ("BLK",),
             "Total revenue was $24,216 million for 2025.", f"{BLK} p4, p43"),
    EvalCase("N09", "What was BlackRock's GAAP net income attributable to BlackRock in 2025?",
             "numeric_qa", "qa", "clear", "answer", ("BLK",),
             "GAAP net income attributable to BlackRock was $5,553 million for 2025 "
             "(as adjusted: $7,736 million).", f"{BLK} p43"),
    EvalCase("N10", "What was Visa's net revenue for fiscal year 2025?",
             "numeric_qa", "qa", "clear", "answer", ("V",),
             "Net revenue was $40,000 million for fiscal 2025 (year ended September 30, 2025).",
             f"{VISA} p41, p46"),

    # --- Added in Phase 0: abstention and summarize coverage ------------------
    EvalCase("N11", "What was Wells Fargo's net income in 2025?",
             "out_of_corpus", "qa", "clear", "abstain", ()),
    EvalCase("N13", "Summarize JPMorgan Chase's key risk factors in its 2025 10-K.",
             "summarize", "summarize", "clear", "answer", ("JPM",)),
    EvalCase("N14", "Give an overview of Bank of America's 2025 business performance.",
             "summarize", "summarize", "clear", "answer", ("BAC",)),

    # --- Visa as the fifth company (replaces the Mastercard summarize cases) ---
    EvalCase("V01", "Compare the risk factors of BlackRock and Visa in 2025.",
             "summarize", "summarize", "clear", "answer", ("BLK", "V"), replaces="L11"),
    EvalCase("V02", "Describe Visa's competitive position in the payments industry.",
             "summarize", "summarize", "clear", "answer", ("V",), replaces="L16"),
    EvalCase("V03", "What were Visa's diluted earnings per share for fiscal year 2025?",
             "metric_qa", "qa", "clear", "answer", ("V",),
             "GAAP diluted EPS was $10.20 for fiscal 2025 (non-GAAP: $11.47).",
             f"{VISA} p41", replaces="N12",
             notes="Replaced N12 (Morgan Stanley, out-of-corpus) to keep 34 cases; "
                   "out-of-corpus coverage remains in L03, L08, L18, N11."),
]

CASES_BY_ID = {case.id: case for case in EVAL_CASES}

# The original 20 queries (June 2026), in order, for historical reference. L11 and
# L16 were retired when Visa replaced Mastercard; the other 18 are still active.
LEGACY_QUERIES_2026_06: tuple[str, ...] = (
    "What was JPMorgan Chase's total net revenue for fiscal year 2025?",
    "What was Goldman Sachs net earnings for fiscal year 2025?",
    "What is Mastercard's total net revenue for fiscal year 2025?",
    "What was BlackRock's total assets under management in 2025?",
    "What was Bank of America's net income for fiscal year 2025?",
    "What was JPMorgan Chase's return on equity in 2025?",
    "How many employees did JPMorgan Chase have in 2025?",
    "What was Mastercard's net income margin in 2025?",
    "What dividends did Goldman Sachs pay in fiscal year 2025?",
    "Which had higher net revenue in 2025, JPMorgan Chase or Goldman Sachs?",
    "Compare the risk factors of BlackRock and Mastercard in 2025.",
    "Summarize the key risks in Goldman Sachs 2025 annual report.",
    "What are the main business segments of JPMorgan Chase?",
    "Summarize BlackRock's investment strategy as described in their 2025 10-K.",
    "What is Bank of America's approach to managing credit risk?",
    "Describe Mastercard's competitive position in the payments industry.",
    "What is a financial statement?",
    "What was Apple's revenue in 2025?",
    "Goldman Sachs 2025",
    "What was JPMorgan Chase's revenue and also summarize their risk factors?",
)
RETIRED_LEGACY_IDS = {"L11": "V01", "L16": "V02"}

# Backward-compatible exports: the still-active legacy queries (18 of the original 20).
EVAL_QUERIES = [case.query for case in EVAL_CASES if case.legacy]
BOUNDARY_QUERIES = [
    case.query for case in EVAL_CASES
    if case.legacy and case.id in {"L17", "L18", "L19", "L20"}
]
