"""Offline unit tests.

Importing this package installs the offline guard (see offline_guard.py), so
these tests cannot reach AWS even if the root conftest.py is bypassed (for
example with `pytest --noconftest`).
"""
from tests import offline_guard

offline_guard.install()
