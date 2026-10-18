"""Repository-wide pytest safety: offline by default, live only on explicit opt-in.

This file is at the pytest rootdir, so pytest loads it for every invocation in
this repository: `pytest`, `pytest tests/`, `pytest eval/test_llm_judge.py` or a
single test id. It installs the offline guard (tests/offline_guard.py) at import,
before any test module is collected, so coverage never depends on which
directory is collected.

Live, billable tests are marked `llm`:
- Without --run-live-eval they are skipped. A selection made up only of `llm`
  tests is a usage error (exit code 4), so a live gate that lost its opt-in fails
  loudly instead of passing with every test skipped.
- With --run-live-eval the guard is lifted and every selected test must be an
  `llm` test, so the offline suite never runs with real credentials.
"""
import pytest

from tests import offline_guard

offline_guard.install()

LIVE_OPTION = "--run-live-eval"


def pytest_addoption(parser):
    parser.addoption(
        LIVE_OPTION, action="store_true", default=False, dest="run_live_eval",
        help="Authorize live, billable AWS/Bedrock calls for tests marked llm. Lifts the offline "
             "guard; only llm tests may be selected.",
    )


def pytest_configure(config):
    if config.getoption("run_live_eval"):
        offline_guard.lift()


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    live_items = [item for item in items if item.get_closest_marker("llm")]
    if config.getoption("run_live_eval"):
        offline_items = [item.nodeid for item in items if not item.get_closest_marker("llm")]
        if offline_items or not live_items:
            raise pytest.UsageError(
                f"{LIVE_OPTION} runs live tests only (marked llm), but the selection "
                f"{'contains offline tests: ' + ', '.join(offline_items[:3]) if offline_items else 'has no llm tests'}. "
                "Run the offline suite separately, without the option."
            )
        return
    if items and len(live_items) == len(items):
        raise pytest.UsageError(
            "Only live, billable tests (marked llm) were selected, and live execution was not authorized. "
            f"Pass {LIVE_OPTION} to run them, or select offline tests."
        )
    skip_live = pytest.mark.skip(reason=f"live, billable test: requires {LIVE_OPTION}")
    for item in live_items:
        item.add_marker(skip_live)


def pytest_terminal_summary(terminalreporter, config):
    if config.getoption("run_live_eval"):
        terminalreporter.write_line(f"LIVE MODE ({LIVE_OPTION}): offline guard lifted for this session.")
        return
    intercepted = len(offline_guard.blocked_requests)
    state = "active" if offline_guard.is_installed() else "NOT ACTIVE"
    terminalreporter.write_line(
        f"offline guard {state}: {intercepted} outbound network attempt(s) intercepted, none sent."
    )
