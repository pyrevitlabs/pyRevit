"""Apply repository classification to pytest and existing unittest cases."""

import pytest


def classification(item):
    """Resolve module/class defaults and explicit method marker overrides."""
    environment = getattr(item.module, "TEST_ENVIRONMENT", None)
    level = getattr(item.module, "TEST_LEVEL", None)
    if item.cls is not None:
        environment = getattr(item.cls, "TEST_ENVIRONMENT", environment)
        level = getattr(item.cls, "TEST_LEVEL", level)
    environment_marker = item.get_closest_marker("environment")
    level_marker = item.get_closest_marker("level")
    if environment_marker:
        selected = environment_marker.args[0]
        if environment == "Revit" and selected != "Revit":
            raise pytest.UsageError(
                f"{item.nodeid}: a Revit fixture cannot become HostFree"
            )
        environment = selected
    if level_marker:
        level = level_marker.args[0]
    if environment not in {"HostFree", "Revit"} or level not in {
        "Unit",
        "Integration",
        "E2E",
        "Performance",
    }:
        raise pytest.UsageError(f"{item.nodeid}: invalid Environment/Level metadata")
    return environment, level


def pytest_collection_modifyitems(config, items):
    """Exclude local Revit cases before any test fixture is set up."""
    selected = []
    excluded = []
    for item in items:
        environment, level = classification(item)
        item.user_properties.extend([("Environment", environment), ("Level", level)])
        if environment == "Revit":
            excluded.append(item)
        else:
            selected.append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=excluded)


def pytest_sessionfinish(session, exitstatus):
    """Require selected host-free cases to execute instead of silently skipping."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter and any(
        reporter.stats.get(outcome) for outcome in ("skipped", "xfailed", "xpassed")
    ):
        reporter.write_sep(
            "!",
            "Selected host-free tests must execute without skips or expected failures",
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
