"""Host-free regression tests for agent-script source locations and narrowing."""

import ast
import builtins
import importlib.util
import os
import sys
import traceback
import types
import unittest
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RUNNER_PATH = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit", "agent", "_runner.py")
SAMPLE = """from contextlib import contextmanager
def decorate(fn):
    return fn
@contextmanager
def scope():
    yield
@decorate
def work():
    with scope():
        pass
    raise ValueError('campaign line 11')
work()
"""


def _load_runner():
    system = types.ModuleType("System")
    for name in ("Int16", "Int32", "Int64", "UInt16", "UInt32", "UInt64"):
        setattr(system, name, int)
    for name in ("Single", "Double", "Decimal"):
        setattr(system, name, float)
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.__path__ = []
    api = types.ModuleType("pyrevit.api")
    api.DB = types.SimpleNamespace(
        SubTransaction=type("SubTransaction", (), {}),
        Transaction=type("Transaction", (), {}),
        TransactionGroup=type("TransactionGroup", (), {}),
    )
    api.UI = types.SimpleNamespace()
    compat = types.ModuleType("pyrevit.compat")
    compat.get_elementid_value_func = lambda: int
    modules = {
        "System": system,
        "pyrevit": pyrevit,
        "pyrevit.api": api,
        "pyrevit.compat": compat,
    }
    with mock.patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location(
            "agent_runner_lines_test", RUNNER_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class AgentRunnerLinesTests(unittest.TestCase):
    """Exercise production compilation without importing Revit or the CLR."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def _traceback_frames(self, source, exception_frames=None):
        """Capture yield frames before CPython contextlib removes them on rethrow."""
        code, problem = self.runner._compile_source(source)
        self.assertIsNone(problem)

        def trace(frame, event, arg):
            if (
                exception_frames is not None
                and event == "exception"
                and frame.f_code.co_filename == self.runner.SOURCE_NAME
            ):
                exception_frames.extend(
                    (entry.name, entry.lineno)
                    for entry in traceback.extract_tb(arg[2])
                    if entry.filename == self.runner.SOURCE_NAME
                )
            return trace

        previous_trace = sys.gettrace()
        sys.settrace(trace)
        try:
            exec(code, {})
        except ValueError as error:
            return [
                (frame.name, frame.lineno)
                for frame in traceback.extract_tb(error.__traceback__)
                if frame.filename == self.runner.SOURCE_NAME
            ]
        finally:
            sys.settrace(previous_trace)
        self.fail("The script did not raise ValueError")

    def test_source_lines_matches_reference_splitter(self):
        """Match a character-based reference for every physical newline style."""

        def reference_split(source):
            lines = []
            start = 0
            index = 0
            while index < len(source):
                character = source[index]
                index += 1
                if character not in ("\r", "\n"):
                    continue
                if character == "\r" and source[index : index + 1] == "\n":
                    index += 1
                lines.append(source[start:index])
                start = index
            if start < len(source):
                lines.append(source[start:])
            return lines

        for source in (
            "",
            "first\nsecond",
            "first\nsecond\n",
            "first\r\nsecond",
            "first\r\nsecond\r\n",
            "first\rsecond",
            "first\rsecond\r",
            "first\r\nsecond\rthird\nfourth",
            "first\r\nsecond\rthird\nfourth\r\n",
            "\n\r\n\r",
            "markers = '\x0c\x1c\x1d\x1e\x85\u2028\u2029'",
            "markers = '\x0c\x1c\x1d\x1e\x85\u2028\u2029'\nresult = markers\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(
                    reference_split(source), self.runner._source_lines(source)
                )

    def test_source_line_count_matches_ast_locations(self):
        """Count the same physical lines as the parser in sample scripts."""
        samples = (
            SAMPLE,
            SAMPLE.replace("        pass", "        raise ValueError('inside with')"),
            SAMPLE + "try:\n    pass\nexcept:\n    pass\n",
            "try:\n    raise ValueError()\nexcept (\n    BaseException,\n"
            "    SystemExit\n) as error:\n    raise\n",
            "markers = '\x0c\x1c\x1d\x1e\x85\u2028\u2029'\n"
            "try:\n    pass\nexcept BaseException:\n    pass\n",
        )
        for sample in samples:
            for newline in ("\n", "\r\n", "\r"):
                for trailing_newline in (False, True):
                    source = sample.rstrip("\n").replace("\n", newline)
                    if trailing_newline:
                        source += newline
                    with self.subTest(source=source):
                        tree = ast.parse(source)
                        last_line = max(
                            node.lineno
                            for node in ast.walk(tree)
                            if hasattr(node, "lineno")
                        )
                        self.assertEqual(
                            last_line, len(self.runner._source_lines(source))
                        )

    def test_decorated_function_after_with(self):
        """Keep the original call and raise lines after a completed with block."""
        self.assertEqual(
            [("<module>", 12), ("work", 11)], self._traceback_frames(SAMPLE)
        )

    def test_bare_handler_reraise_inside_decorated_with(self):
        """Keep the measured IronPython regression's raise, call and yield lines."""
        source = SAMPLE.replace(
            "        pass\n    raise ValueError('campaign line 11')",
            "        try:\n"
            "            raise ValueError('campaign line 11')\n"
            "        except:\n"
            "            raise",
        )
        exception_frames = []
        self.assertEqual(
            [("<module>", 14), ("work", 11)],
            self._traceback_frames(source, exception_frames),
        )
        self.assertIn(("scope", 6), exception_frames)

    def test_exception_inside_with_body(self):
        """Keep the contextmanager yield line when its body throws."""
        source = SAMPLE.replace(
            "        pass", "        raise ValueError('inside with')"
        )
        exception_frames = []
        self.assertEqual(
            [("<module>", 12), ("work", 10)],
            self._traceback_frames(source, exception_frames),
        )
        self.assertIn(("scope", 6), exception_frames)

    def test_decorated_function_called_from_loop(self):
        """Keep nested function lines even when another handler is narrowed."""
        source = SAMPLE.replace("work()\n", "for item in range(1):\n    work()\n")
        source += "try:\n    pass\nexcept BaseException:\n    pass\n"
        self.assertEqual(
            [("<module>", 13), ("work", 11)], self._traceback_frames(source)
        )

    def test_narrowed_with_body_keeps_yield_line(self):
        """Preserve generator frames while rewriting a bare handler elsewhere."""
        source = SAMPLE.replace(
            "        pass", "        raise ValueError('inside with')"
        )
        source += "try:\n    pass\nexcept:\n    pass\n"
        exception_frames = []
        self.assertEqual(
            [("<module>", 12), ("work", 10)],
            self._traceback_frames(source, exception_frames),
        )
        self.assertIn(("scope", 6), exception_frames)

    def test_compiler_uses_source_for_valid_rewrite(self):
        """Avoid IronPython's line-one AST compiler path on successful rewrites."""
        original_compile = builtins.compile

        def compile_source(source, *args, **kwargs):
            self.assertNotIsInstance(source, ast.AST)
            return original_compile(source, *args, **kwargs)

        with mock.patch("builtins.compile", side_effect=compile_source):
            code, problem = self.runner._compile_source(
                "try:\n    raise ValueError()\nexcept BaseException:\n    result = 1\n"
            )
        self.assertIsNone(problem)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(1, namespace["result"])

    @unittest.skipIf(sys.version_info < (3, 11), "Requires exception groups")
    def test_except_star_keeps_exception_group_and_lines(self):
        """Preserve exception groups and source lines when narrowing star handlers."""
        for header in (
            "except* BaseException as error:",
            "except \t* \tBaseException as error:",
            "except* (\n    BaseException\n) as error:",
        ):
            with self.subTest(header=header):
                source = (
                    "import sys\n"
                    "try:\n"
                    "    raise ValueError('x')\n" + header + "\n"
                    "    result = (type(error).__name__, len(error.exceptions), "
                    "error.exceptions[0].__traceback__.tb_lineno, "
                    "sys._getframe().f_lineno)\n"
                )
                narrower = self.runner._NarrowBroadHandlers()
                narrower.visit(ast.parse(source))
                self.assertEqual(1, len(narrower.narrowed))
                self.assertEqual("Exception", narrower.narrowed[0].type.id)
                rewritten = self.runner._narrow_source_handlers(
                    source, narrower.narrowed
                )
                self.assertEqual(source.count("\n"), rewritten.count("\n"))
                code, problem = self.runner._compile_source(source)
                self.assertIsNone(problem)
                namespace = {}
                exec(code, namespace)
                self.assertEqual(
                    ("ExceptionGroup", 1, 3, len(source.splitlines())),
                    namespace["result"],
                )

    @unittest.skipIf(sys.version_info < (3, 11), "Requires exception groups")
    def test_spaced_except_star_source_keeps_star(self):
        """Retain the star when whitespace separates it from the except keyword."""
        source = "try:\n    pass\nexcept *BaseException:\n    pass\n"
        narrower = self.runner._NarrowBroadHandlers()
        narrower.visit(ast.parse(source))
        self.assertEqual(
            "try:\n    pass\nexcept * (Exception) :\n    pass\n",
            self.runner._narrow_source_handlers(source, narrower.narrowed),
        )

    def test_replacement_node_copies_location(self):
        """Copy start and available end positions from the replaced handler type."""
        for header in ("except:", "except BaseException:"):
            tree = ast.parse("try:\n    pass\n" + header + "\n    pass\n")
            handler = tree.body[0].handlers[0]
            original = handler.type or handler
            self.runner._NarrowBroadHandlers().visit(tree)
            for attribute in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
                self.assertEqual(
                    getattr(original, attribute), getattr(handler.type, attribute)
                )

    def test_multiline_tuple_and_binding(self):
        """Narrow the entire tuple and retain multiline handler body positions."""
        source = (
            "try:\n"
            "    raise ValueError('caught')\n"
            "except (\n"
            "    BaseException,\n"
            "    SystemExit\n"
            ") as error:\n"
            "    raise ValueError('handler')\n"
        )
        self.assertEqual([("<module>", 7)], self._traceback_frames(source))
        code, problem = self.runner._compile_source(
            source.replace("ValueError('caught')", "SystemExit()")
        )
        self.assertIsNone(problem)
        with self.assertRaises(SystemExit):
            exec(code, {})

    def test_multiple_handlers_and_inline_suites(self):
        """Narrow every broad header without changing ordinary exception handlers."""
        source = (
            "try: raise KeyError()\n"
            "except KeyError: result = 1\n"
            "except BaseException: result = 2\n"
            "try: raise ValueError()\n"
            "except: result += 3\n"
        )
        code, problem = self.runner._compile_source(source)
        self.assertIsNone(problem)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(4, namespace["result"])
        for exception in ("SystemExit", "RunTimedOut"):
            code, problem = self.runner._compile_source(
                source.replace("ValueError()", exception + "()")
            )
            self.assertIsNone(problem)
            with self.assertRaises((SystemExit, self.runner.RunTimedOut)):
                exec(code, {"RunTimedOut": self.runner.RunTimedOut})

    def test_string_separators_keep_handler_offsets_and_lines(self):
        """Match AST physical lines without splitting separators inside strings."""
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=newline):
                source = newline.join(
                    (
                        "markers = '\x0c\x1c\x1d\x1e\x85\u2028\u2029'",
                        "def work():",
                        "    try:",
                        "        raise ValueError('original line')",
                        "    except:",
                        "        raise",
                        "work()",
                        "",
                    )
                )
                tree = ast.parse(source)
                handler = tree.body[1].body[0].handlers[0]
                self.assertEqual((5, 4), (handler.lineno, handler.col_offset))
                lines = self.runner._source_lines(source)
                self.assertEqual(7, len(lines))
                self.assertEqual(
                    "except:" + newline,
                    lines[handler.lineno - 1][handler.col_offset :],
                )
                self.assertEqual(
                    [("<module>", 7), ("work", 4)],
                    self._traceback_frames(source),
                )
                code, problem = self.runner._compile_source(
                    source.replace("ValueError('original line')", "RunTimedOut()")
                )
                self.assertIsNone(problem)
                with self.assertRaises(self.runner.RunTimedOut):
                    exec(code, {"RunTimedOut": self.runner.RunTimedOut})

    def test_invalid_header_rewrite_falls_back_to_narrowed_ast(self):
        """Keep timeout exceptions uncaught even if replacement source is invalid."""
        source = "try:\n    raise error\nexcept:\n    result = 'caught'\n"
        with mock.patch.object(
            self.runner, "_narrow_source_handlers", return_value="except ("
        ):
            code, problem = self.runner._compile_source(source)
        self.assertIn("SyntaxError", problem)
        self.assertIn("compiled the narrowed AST instead", problem)
        self.assertIn("source line numbers may be unavailable", problem)
        namespace = {"error": ValueError()}
        exec(code, namespace)
        self.assertEqual("caught", namespace["result"])
        with self.assertRaises(self.runner.RunTimedOut):
            exec(code, {"error": self.runner.RunTimedOut()})

    def test_python_two_binding_header(self):
        """Retain legacy exception bindings without needing a Python 2 host."""
        source = "try:\n    pass\nexcept BaseException, error:\n    pass\n"
        handlers = [types.SimpleNamespace(lineno=3, col_offset=0)]
        rewritten = self.runner._narrow_source_handlers(source, handlers)
        self.assertEqual(
            "try:\n    pass\nexcept (Exception) , error:\n    pass\n", rewritten
        )

    def test_workspace_cleanup_ignores_relative_module_paths(self):
        """Do not unload standard-library modules reported with relative paths."""
        module = types.SimpleNamespace(__file__="importlib\\__init__.py")
        self.assertFalse(self.runner._is_under(module.__file__, REPO_ROOT))

    def test_workspace_cleanup_preserves_runtime_modules(self):
        """Do not unload interpreter libraries installed below the workspace."""
        module_file = os.path.join(sys.prefix, "Lib", "io.py")
        self.assertTrue(self.runner._is_runtime_module(module_file))


if __name__ == "__main__":
    unittest.main()
