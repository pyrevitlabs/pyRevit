"""Tests for the runtime-backed logging facade."""

import importlib.util
import logging
import os
import sys
import tempfile
import types
import unittest


LOGGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "pyrevitlib",
    "pyrevit",
    "coreutils",
    "logger.py",
)


class FakeService(object):
    def __init__(self):
        self.records = []
        self.minimum_level = logging.WARNING
        self.file_logging = False
        self.HasErrors = False
        self.on_log = None

    def Log(self, name, level, message, allow_window_creation=True):
        self.records.append((name, level, message, allow_window_creation))
        if level >= logging.ERROR:
            self.HasErrors = True
        if self.on_log:
            self.on_log()

    def IsEnabled(self, level):
        return self.file_logging or level >= self.minimum_level

    def IsVisibleEnabled(self, level):
        return level >= self.minimum_level

    def SetMinimumLevel(self, level):
        self.minimum_level = level

    def GetMinimumLevel(self):
        return self.minimum_level

    def SetFileLogging(self, enabled):
        self.file_logging = enabled


def load_logger_module():
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.__path__ = []
    pyrevit.EXEC_PARAMS = types.SimpleNamespace(
        script_runtime=None,
        command_uniqueid="command-id",
        exec_timestamp="timestamp",
        exec_id="exec-id",
    )
    pyrevit.USER_DESKTOP = tempfile.gettempdir()
    pyrevit.coreutils = types.ModuleType("pyrevit.coreutils")
    pyrevit.coreutils.prepare_html_str = lambda value: value

    compat = types.ModuleType("pyrevit.compat")
    compat.safe_strtype = str

    previous = {
        name: sys.modules.get(name)
        for name in ("pyrevit", "pyrevit.compat", "pyrevit.coreutils")
    }
    sys.modules["pyrevit"] = pyrevit
    sys.modules["pyrevit.compat"] = compat
    sys.modules["pyrevit.coreutils"] = pyrevit.coreutils
    try:
        spec = importlib.util.spec_from_file_location(
            "pyrevit_test_runtime_logger", LOGGER_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, old_module in previous.items():
            if old_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_module


class RuntimeLoggerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = logging.getLogger()
        cls.original_handlers = list(cls.root.handlers)
        cls.original_level = cls.root.level
        cls.module = load_logger_module()
        cls.original_resolve_service = staticmethod(cls.module._resolve_service)

    @classmethod
    def tearDownClass(cls):
        cls.root.handlers[:] = cls.original_handlers
        cls.root.setLevel(cls.original_level)

    def setUp(self):
        self.service = FakeService()
        self.module._resolve_service = lambda: self.service
        self.module.loggers.clear()

    def tearDown(self):
        self.module._resolve_service = self.original_resolve_service

    def test_facade_caching_and_percent_arguments(self):
        logger = self.module.get_logger("sample")
        self.assertIs(logger, self.module.get_logger("sample"))

        logger.error("Failed: %s", "value")

        name, level, message, spawn = self.service.records[-1]
        self.assertEqual(("sample", logging.ERROR, "Failed: value"),
                         (name, level, message))
        self.assertFalse(spawn)

    def test_facade_records_never_spawn_output_window(self):
        logger = self.module.get_logger("sample")

        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")
        logger.success("success message")
        logger.deprecate("deprecated")

        self.assertTrue(self.service.records)
        for record in self.service.records:
            self.assertFalse(
                record[3],
                "log record at level %s must not spawn the output window"
                % record[1],
            )

    def test_malformed_format_falls_back_without_raising(self):
        self.module.get_logger("sample").warning("Bad %s %s", "value")
        self.assertEqual("Bad %s %s value", self.service.records[-1][2])

    def test_warn_exception_and_custom_levels(self):
        logger = self.module.get_logger("sample")
        logger.warn("warning")
        try:
            raise ValueError("broken")
        except ValueError:
            logger.exception("operation failed")
        logger.deprecate("old")
        logger.success("done")

        self.assertEqual(logging.WARNING, self.service.records[0][1])
        self.assertIn("ValueError: broken", self.service.records[1][2])
        self.assertEqual(
            self.module.DEPRECATE_LOG_LEVEL, self.service.records[2][1]
        )
        self.assertEqual(self.module.SUCCESS_LOG_LEVEL,
                         self.service.records[3][1])

    def test_level_controls_delegate_to_service(self):
        logger = self.module.get_logger("sample")
        logger.set_debug_mode()
        self.assertEqual(logging.DEBUG, logger.get_level())
        logger.set_verbose_mode()
        self.assertEqual(logging.INFO, logger.get_level())
        logger.set_quiet_mode()
        self.assertEqual(logging.CRITICAL, logger.get_level())
        logger.reset_level()
        self.assertEqual(logging.WARNING, logger.get_level())

        self.module.set_file_logging(True)
        self.assertTrue(logger.isEnabledFor(logging.DEBUG))
        self.assertFalse(logger.is_enabled_for(logging.DEBUG))

    def test_standard_bridge_forwards_name_message_and_exception(self):
        standard_logger = logging.getLogger("third.party")
        standard_logger.handlers[:] = []
        standard_logger.propagate = True

        standard_logger.info("Hello %s", "world")
        try:
            raise RuntimeError("failure")
        except RuntimeError:
            standard_logger.exception("bridge error")

        name, level, message, spawn = self.service.records[0]
        self.assertEqual(("third.party", logging.INFO, "Hello world"),
                         (name, level, message))
        self.assertIn("RuntimeError: failure", self.service.records[1][2])
        for record in self.service.records:
            self.assertFalse(record[3])

    def test_bridge_installation_is_idempotent_and_recursive_safe(self):
        first = self.module._install_standard_logging_bridge()
        second = self.module._install_standard_logging_bridge()
        self.assertIs(first, second)

        self.service.on_log = (
            lambda: logging.getLogger("recursive").warning("again")
        )
        logging.getLogger("outer").warning("once")
        self.assertEqual(1, len(self.service.records))

    def test_disposed_runtime_resolves_session_service(self):
        runtime_types = types.ModuleType("pyrevit.runtime.types")
        default_service = FakeService()

        class ServiceResolver(object):
            @staticmethod
            def GetForRuntime(runtime):
                raise AssertionError("disposed runtime must not be reused")

            @staticmethod
            def GetDefault():
                return default_service

        runtime_types.ScriptLoggerService = ServiceResolver
        runtime_package = types.ModuleType("pyrevit.runtime")
        runtime_package.__path__ = []
        previous_runtime = sys.modules.get("pyrevit.runtime")
        previous_types = sys.modules.get("pyrevit.runtime.types")
        sys.modules["pyrevit.runtime"] = runtime_package
        sys.modules["pyrevit.runtime.types"] = runtime_types
        self.module.EXEC_PARAMS.script_runtime = types.SimpleNamespace(
            IsDisposed=True
        )
        try:
            self.assertIs(
                default_service, self.original_resolve_service()
            )
        finally:
            self.module.EXEC_PARAMS.script_runtime = None
            if previous_runtime is None:
                sys.modules.pop("pyrevit.runtime", None)
            else:
                sys.modules["pyrevit.runtime"] = previous_runtime
            if previous_types is None:
                sys.modules.pop("pyrevit.runtime.types", None)
            else:
                sys.modules["pyrevit.runtime.types"] = previous_types

    def test_runtime_service_is_resolved_without_importing_types(self):
        runtime_service = FakeService()
        self.module.EXEC_PARAMS.script_runtime = types.SimpleNamespace(
            IsDisposed=True, LoggerService=runtime_service
        )
        try:
            self.assertIs(runtime_service, self.original_resolve_service())
        finally:
            self.module.EXEC_PARAMS.script_runtime = None

    def test_live_runtime_uses_instance_logger_service(self):
        runtime_types = types.ModuleType("pyrevit.runtime.types")
        runtime_service = FakeService()
        default_service = FakeService()

        class ServiceResolver(object):
            @staticmethod
            def GetDefault():
                return default_service

        runtime_types.ScriptLoggerService = ServiceResolver
        runtime_package = types.ModuleType("pyrevit.runtime")
        runtime_package.__path__ = []
        previous_runtime = sys.modules.get("pyrevit.runtime")
        previous_types = sys.modules.get("pyrevit.runtime.types")
        sys.modules["pyrevit.runtime"] = runtime_package
        sys.modules["pyrevit.runtime.types"] = runtime_types
        self.module.EXEC_PARAMS.script_runtime = types.SimpleNamespace(
            IsDisposed=False, LoggerService=runtime_service
        )
        try:
            self.assertIs(runtime_service, self.original_resolve_service())
        finally:
            self.module.EXEC_PARAMS.script_runtime = None
            if previous_runtime is None:
                sys.modules.pop("pyrevit.runtime", None)
            else:
                sys.modules["pyrevit.runtime"] = previous_runtime
            if previous_types is None:
                sys.modules.pop("pyrevit.runtime.types", None)
            else:
                sys.modules["pyrevit.runtime.types"] = previous_types


if __name__ == "__main__":
    unittest.main()
