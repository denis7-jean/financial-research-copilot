"""Isolated router benchmark: Haiku 4.5 (RouterAgent, unchanged) vs rules vs TypeSafe Jev.

Design: docs/experiments/router-benchmark-design.md (v2). Offline by default; see cli.py.
This package never imports QA, summarization or retrieval code (enforced by
safety.DownstreamTripwire and tests).
"""
