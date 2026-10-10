#! python3
"""Run the agent runtime end-to-end tests from CPython.

CPython keeps one interpreter for the whole Revit session, so the test modules
are dropped from ``sys.modules`` first; otherwise a second click would run the
code of the first one.
"""

# pylint: skip-file
import importlib
import sys

for name in [name for name in sys.modules if name.startswith("agent_")]:
    del sys.modules[name]

agent_harness = importlib.import_module("agent_harness")
agent_harness.run_suites(
    [
        importlib.import_module(name)
        for name in (
            "agent_requests_tests",
            "agent_validation_tests",
            "agent_query_tests",
            "agent_modify_tests",
            "agent_settings_tests",
            "agent_session_tests",
            "agent_awareness_tests",
            "agent_panel_tests",
            "agent_pipe_tests",
        )
    ]
)
