EVAL_QUERIES = [
    # Numeric QA — one per company
    "What was JPMorgan Chase's total net revenue for fiscal year 2025?",
    "What was Goldman Sachs net earnings for fiscal year 2025?",
    "What is Mastercard's total net revenue for fiscal year 2025?",
    "What was BlackRock's total assets under management in 2025?",
    "What was Bank of America's net income for fiscal year 2025?",

    # Specific metrics
    "What was JPMorgan Chase's return on equity in 2025?",
    "How many employees did JPMorgan Chase have in 2025?",
    "What was Mastercard's net income margin in 2025?",
    "What dividends did Goldman Sachs pay in fiscal year 2025?",

    # Cross-company
    "Which had higher net revenue in 2025, JPMorgan Chase or Goldman Sachs?",
    "Compare the risk factors of BlackRock and Mastercard in 2025.",

    # Summarize
    "Summarize the key risks in Goldman Sachs 2025 annual report.",
    "What are the main business segments of JPMorgan Chase?",
    "Summarize BlackRock's investment strategy as described in their 2025 10-K.",
    "What is Bank of America's approach to managing credit risk?",
    "Describe Mastercard's competitive position in the payments industry.",

    # Boundary
    "What is a financial statement?",
    "What was Apple's revenue in 2025?",
    "Goldman Sachs 2025",
    "What was JPMorgan Chase's revenue and also summarize their risk factors?",
]

BOUNDARY_QUERIES = [
    "What is a financial statement?",
    "What was Apple's revenue in 2025?",
    "Goldman Sachs 2025",
    "What was JPMorgan Chase's revenue and also summarize their risk factors?",
]
