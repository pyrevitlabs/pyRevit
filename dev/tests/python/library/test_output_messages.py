"""Host-free tests for page message dispatch in ``pyrevit.output``.

Loads ``pyrevitlib/pyrevit/output/__init__.py`` with stubbed ``pyrevit``
modules for each engine flag and checks that page messages reach their handlers
only through ``events.execute_in_revit_context``.
"""

import importlib.util
import json
import pathlib
import sys
import types
import unittest
from unittest import mock

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

OUTPUT = (
    pathlib.Path(__file__).resolve().parents[4]
    / "pyrevitlib"
    / "pyrevit"
    / "output"
    / "__init__.py"
)


def _module(name, **values):
    module = types.ModuleType(name)
    module.__dict__.update(values)
    return module


class ApiContext:
    """Records what is scheduled and runs it only when told to."""

    def __init__(self):
        self.scheduled = []

    def execute_in_revit_context(self, func, *args):
        self.scheduled.append((func, args))
        return True

    def run_scheduled(self):
        pending, self.scheduled = self.scheduled, []
        for func, args in pending:
            func(*args)


def stub_modules(ironpython, api_context):
    events = _module(
        "pyrevit.revit.events",
        execute_in_revit_context=api_context.execute_in_revit_context,
    )
    modules = {
        "pyrevit.compat": _module(
            "pyrevit.compat", IRONPY=ironpython, PY3=True, safe_strtype=str
        ),
        "pyrevit.coreutils.envvars": _module(
            "pyrevit.coreutils.envvars",
            OUTPUT_STYLESHEET_ENVVAR="stylesheet",
            set_pyrevit_env_var=lambda *args: None,
        ),
        "pyrevit.coreutils.charts": _module("pyrevit.coreutils.charts"),
        "pyrevit.coreutils.logger": _module(
            "pyrevit.coreutils.logger", get_logger=lambda name: mock.Mock()
        ),
        "pyrevit.runtime": _module("pyrevit.runtime"),
        "pyrevit.runtime.types": _module(
            "pyrevit.runtime.types", ScriptConsoleManager=None, ScriptOutput=None
        ),
        "pyrevit.userconfig": _module(
            "pyrevit.userconfig",
            user_config=types.SimpleNamespace(output_stylesheet=None),
        ),
        "pyrevit.output": _module("pyrevit.output"),
        "pyrevit.output.linkmaker": _module("pyrevit.output.linkmaker"),
        "pyrevit.revit": _module("pyrevit.revit", events=events),
        "pyrevit.revit.events": events,
    }
    coreutils = _module(
        "pyrevit.coreutils",
        envvars=modules["pyrevit.coreutils.envvars"],
        charts=modules["pyrevit.coreutils.charts"],
        logger=modules["pyrevit.coreutils.logger"],
    )
    modules["pyrevit.coreutils"] = coreutils
    modules["pyrevit.output"].linkmaker = modules["pyrevit.output.linkmaker"]
    modules["pyrevit"] = _module(
        "pyrevit",
        HOST_APP=None,
        EXEC_PARAMS=None,
        DB=None,
        framework=None,
        coreutils=coreutils,
    )
    return modules


class PageMessageDispatchTests(unittest.TestCase):
    def dispatch(self, ironpython, text, handlers):
        api_context = ApiContext()
        with mock.patch.dict(sys.modules, stub_modules(ironpython, api_context)):
            spec = importlib.util.spec_from_file_location("output_under_test", OUTPUT)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            wrapper = module.PyRevitOutputWindow.__new__(module.PyRevitOutputWindow)
            wrapper._message_handlers = list(handlers)
            wrapper._dispatch_message(None, types.SimpleNamespace(Json=text))
        return api_context

    def test_handlers_wait_for_the_api_context_on_both_engines(self):
        for ironpython in (True, False):
            with self.subTest(ironpython=ironpython):
                seen = []
                api_context = self.dispatch(
                    ironpython, json.dumps({"ids": [1]}), [seen.append]
                )
                self.assertEqual(seen, [])
                api_context.run_scheduled()
                self.assertEqual(seen, [{"ids": [1]}])

    def test_each_handler_is_scheduled_in_registration_order(self):
        calls = []

        def first(message):
            calls.append(("first", message))

        def second(message):
            calls.append(("second", message))

        self.dispatch(False, '"go"', [first, second]).run_scheduled()
        self.assertEqual(calls, [("first", "go"), ("second", "go")])

    def test_text_that_is_not_json_schedules_nothing(self):
        api_context = self.dispatch(False, "not json", [print])
        self.assertEqual(api_context.scheduled, [])


if __name__ == "__main__":
    unittest.main()
