"""Host-free regression tests for agent-script source locations and narrowing."""

import ast
import builtins
import importlib.util
import os
import re
import sys
import time
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
        code, problem, _ = self.runner._compile_source(source)
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
            code, problem, _ = self.runner._compile_source(
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
                code, problem, _ = self.runner._compile_source(source)
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
        code, problem, _ = self.runner._compile_source(
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
        code, problem, _ = self.runner._compile_source(source)
        self.assertIsNone(problem)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(4, namespace["result"])
        for exception in ("SystemExit", "RunTimedOut"):
            code, problem, _ = self.runner._compile_source(
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
                code, problem, _ = self.runner._compile_source(
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
            code, problem, _ = self.runner._compile_source(source)
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

    def test_compile_reports_whether_loops_are_guarded(self):
        """Guard loops only when asked, and report it."""
        source = "for item in range(2):\n    pass\n"
        self.assertFalse(self.runner._compile_source(source)[2])
        code, problem, guarded = self.runner._compile_source(source, True)
        self.assertIsNone(problem)
        self.assertTrue(guarded)


LOOP_SHAPES = {
    "simple_for": "s = 0\nfor i in range(5):\n    s += i\nresult = s\n",
    "tuple_target": "s = []\nfor (a, b) in [(1, 2), (3, 4)]:\n    s.append(a * b)\nresult = s\n",
    "bare_tuple_iter": "s = []\nfor x in 1, 2, 3:\n    s.append(x)\nresult = s\n",
    "ternary_iter": "c = False\ns = []\nfor x in [1] if c else [2, 3]:\n    s.append(x)\nresult = s\n",
    "slice_iter": "s = []\nfor x in [1, 2, 3, 4][1:]:\n    s.append(x)\nresult = s\n",
    "in_inside_iter": "s = []\nfor x in (1 in [1], 2 in [3]):\n    s.append(x)\nresult = s\n",
    "for_else": "s = 0\nfor x in []:\n    s = 1\nelse:\n    s = 2\nresult = s\n",
    "one_line_for": "s = 0\nfor x in range(3): s += x\nresult = s\n",
    "multiline_iter": "s = []\nfor x in (1,  # comment\n          2):\n    s.append(x)\nresult = s\n",
    "backslash_iter": "s = []\nfor x in 1, \\\n        2:\n    s.append(x)\nresult = s\n",
    "no_space_in": "s = []\nfor x in(1, 2):\n    s.append(x)\nresult = s\n",
    "while": "i = 0\nwhile i < 5:\n    i += 1\nresult = i\n",
    "while_or": "i = 0\nwhile i < 3 or False:\n    i += 1\nresult = i\n",
    "while_one_line": "i = 0\nwhile i < 3: i += 1\nresult = i\n",
    "while_not": "i = 0\nwhile not i >= 4:\n    i += 1\nresult = i\n",
    "while_comment_colon": "i = 0\nwhile i < 2:  # note: colon\n    i += 1\nresult = i\n",
    "while_break_else": (
        "i = 0\nwhile True:\n    i += 1\n    if i > 2:\n        break\n"
        "else:\n    i = -1\nresult = i\n"
    ),
    "list_comp": "result = [x * 2 for x in range(4)]\n",
    "list_comp_if": "result = [x for x in range(6) if x % 2]\n",
    "comp_if_next_line": "data = [1, 2, 3]\nresult = [\n    x\n    for x in data\n    if x > 1\n]\n",
    "nested_comp": "result = [(x, y) for x in range(3) for y in range(x) if y]\n",
    "comp_in_iter": "result = [y for y in [x for x in range(3)]]\n",
    "dict_comp": "result = {k: v for k, v in [('a', 1), ('b', 2)]}\n",
    "set_comp": "result = sorted({x % 3 for x in range(9)})\n",
    "gen_arg": "result = sum(x for x in range(5))\n",
    "gen_with_kw": "result = sorted((x for x in [3, 1, 2]), reverse=True)\n",
    "ternary_element": "result = [x if x else -1 for x in [0, 1, 2]]\n",
    "lambda_in_comp": "result = [f(2) for f in [lambda v: v + 1, lambda v: v * 3]]\n",
    "keywords_in_strings": "s = 'for x in y: while'  # for while in\nresult = [c for c in s if c == 'w']\n",
    "nested_loops_in_function": (
        "def f(n):\n    out = []\n    for i in range(n):\n        j = 0\n"
        "        while j < i:\n            out.append((i, j))\n            j += 1\n"
        "    return out\nresult = f(4)\n"
    ),
    "class_body": (
        "class A:\n    items = [x for x in range(3)]\n    for k in range(2):\n"
        "        pass\nresult = A.items\n"
    ),
    "crlf": "s = 0\r\nfor i in range(3):\r\n    s += i\r\nresult = s\r\n",
    "unicode": "s = 'Привет мир'\nresult = [c for c in s if c in 'ир']\n",
}


class AgentRunnerLoopGuardTests(unittest.TestCase):
    """Loop-header guards, timeout tracking and tracer scope, without Revit."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def _guards(self, timed_out=False):
        state = {"timed_out": timed_out}
        tick, loop = self.runner._loop_guards(5, state, {})
        return state, {"__agent_tick__": tick, "__agent_loop__": loop}

    def _run_guarded(self, source, namespace=None):
        code, problem, guarded = self.runner._compile_source(source, True)
        self.assertIsNone(problem)
        self.assertTrue(guarded)
        scope = self._guards()[1]
        scope.update(namespace or {})
        exec(code, scope)
        return scope

    def test_loop_shapes_keep_results_and_lines(self):
        """Every loop shape behaves the same, gets one guard, and keeps its lines."""
        for name, source in sorted(LOOP_SHAPES.items()):
            with self.subTest(shape=name):
                guarded = self.runner._guard_loop_headers(source)
                expected = {}
                exec(compile(source, "<original>", "exec"), expected)
                actual = self._run_guarded(source)
                self.assertEqual(expected["result"], actual["result"])
                self.assertEqual(
                    len(self.runner._source_lines(source)),
                    len(self.runner._source_lines(guarded)),
                )
                guards = guarded.count("__agent_tick__") + guarded.count(
                    "__agent_loop__"
                )
                loops = sum(
                    1
                    for token in self.runner._significant_tokens(source)
                    if token[1] in ("for", "while")
                )
                self.assertEqual(loops, guards)
                for before, after in zip(source.splitlines(), guarded.splitlines()):
                    if before == after:
                        continue
                    closer_only = any(
                        after.replace(closer, "", 1) == before for closer in ("))", ")")
                    )
                    self.assertTrue(
                        closer_only or re.search(r"\b(for|while)\b", before),
                        (before, after),
                    )

    def test_guards_stop_a_loop_that_swallows_the_timeout(self):
        """A handler the runner can't narrow still can't keep the loop running."""
        source = (
            "Base = BaseException\n"
            "count = 0\n"
            "while True:\n"
            "    count += 1\n"
            "    try:\n"
            "        trip()\n"
            "    except Base:\n"
            "        pass\n"
        )
        code, problem, guarded = self.runner._compile_source(source, True)
        state, scope = self._guards()

        def trip():
            state["timed_out"] = True
            raise self.runner.RunTimedOut(5)

        scope["trip"] = trip
        with self.assertRaises(self.runner.RunTimedOut):
            exec(code, scope)
        self.assertEqual(1, scope["count"])

    def test_generator_expression_iterates_its_source_immediately(self):
        """Create the outermost iterator when the generator expression is built."""
        source = "d = {1: 1}\ng = (k for k in d)\nd.clear()\nresult = list(g)\n"
        with self.assertRaises(RuntimeError):
            exec(compile(source, "<original>", "exec"), {})
        with self.assertRaises(RuntimeError):
            self._run_guarded(source)

    @unittest.skipIf(sys.version_info < (3, 7), "Requires asyncio.run")
    def test_async_loops_are_left_alone(self):
        """Leave async for loops to the CPython watchdog instead of breaking them."""
        source = (
            "import asyncio\n"
            "async def numbers():\n"
            "    for value in range(3):\n"
            "        yield value\n"
            "async def collect():\n"
            "    found = [value async for value in numbers()]\n"
            "    async for value in numbers():\n"
            "        found.append(value)\n"
            "    return found\n"
            "result = asyncio.run(collect())\n"
        )
        guarded = self.runner._guard_loop_headers(source)
        self.assertIn("[value async for value in numbers()]", guarded)
        self.assertIn("    async for value in numbers():", guarded)
        self.assertEqual([0, 1, 2, 0, 1, 2], self._run_guarded(source)["result"])

    def test_dynamic_code_is_detected(self):
        """Spot code compiled at run time, but not attribute calls named compile."""
        for source in (
            "exec(inputs['code'])\n",
            "value = eval('1 + 1')\n",
            "code = compile('x = 1', '<s>', 'exec')\n",
        ):
            with self.subTest(source=source):
                self.assertTrue(self.runner._runs_dynamic_code(source))
        for source in (
            "import re\npattern = re.compile('a+')\n",
            "text = 'exec eval compile'  # exec\n",
        ):
            with self.subTest(source=source):
                self.assertFalse(self.runner._runs_dynamic_code(source))

    def test_transaction_tracking_needs_a_mention_or_a_workspace(self):
        """Skip the tracer only for scripts that can't reach a transaction."""
        needs = self.runner._needs_transaction_tracking
        self.assertTrue(needs("T = DB.Transaction\n", None))
        self.assertTrue(needs("result = helpers.run()\n", r"C:\work"))
        self.assertTrue(needs("t = getattr(DB, name)(doc)\nt.Start()\n", None))
        self.assertFalse(needs("result = [1, 2]\n", None))

    def _tracked(self, source):
        transactions = {}
        tracer = self.runner._execution_tracer(
            5, {"timed_out": False}, transactions, False, True
        )
        code, problem, guarded = self.runner._compile_source(source, True)
        scope = self._guards()[1]
        scope["DB"] = self.runner.DB
        scope["Labelled"] = type(
            "Labelled",
            (self.runner.DB.Transaction,),
            {"__init__": lambda self, label: setattr(self, "label", label)},
        )
        previous = sys.gettrace()
        sys.settrace(tracer)
        try:
            exec(code, scope)
        finally:
            sys.settrace(previous)
        return sorted(
            getattr(value, "label", "?") for _, value in transactions.values()
        )

    def test_helpers_that_never_name_a_transaction_are_tracked(self):
        """Find transactions held under aliases, factory results and parameters."""
        source = (
            "T = Labelled\n"
            "def make(label):\n"
            "    return T(label)\n"
            "def aliased():\n"
            "    t = T('alias')\n"
            "def from_factory():\n"
            "    txn = make('factory')\n"
            "def start(txn):\n"
            "    pass\n"
            "aliased()\n"
            "from_factory()\n"
            "start(make('parameter'))\n"
        )
        self.assertEqual(["alias", "factory", "parameter"], self._tracked(source))

    def test_tracking_keeps_module_comprehensions_intact(self):
        """Reading frame locals must not clobber inlined comprehension variables."""
        source = (
            "label = 'transaction'\n"
            "values = [10, 20, 30]\n"
            "result = [\n"
            "    value\n"
            "    for value in values\n"
            "    if value is not None\n"
            "]\n"
        )
        transactions = {}
        tracer = self.runner._execution_tracer(
            5, {"timed_out": False}, transactions, False, True
        )
        code, problem, guarded = self.runner._compile_source(source, True)
        scope = self._guards()[1]
        previous = sys.gettrace()
        sys.settrace(tracer)
        try:
            exec(code, scope)
        finally:
            sys.settrace(previous)
        self.assertEqual([10, 20, 30], scope["result"])

    def test_helpers_that_rebind_or_delete_a_transaction_are_tracked(self):
        """Keep a transaction found after its only variable is rebound or deleted."""
        source = (
            "def rebound():\n"
            "    t = Labelled('rebound')\n"
            "    t = None\n"
            "def deleted():\n"
            "    t = Labelled('deleted')\n"
            "    del t\n"
            "rebound()\n"
            "deleted()\n"
        )
        self.assertEqual(["deleted", "rebound"], self._tracked(source))

    def test_tracking_keeps_class_body_comprehensions_intact(self):
        """Class bodies have dict locals too; tracking must not clobber them."""
        source = (
            "label = 'transaction'\n"
            "class A:\n"
            "    values = [10, 20, 30]\n"
            "    picked = [\n"
            "        value\n"
            "        for value in values\n"
            "        if value > 10\n"
            "    ]\n"
            "result = A.picked\n"
        )
        tracer = self.runner._execution_tracer(5, {"timed_out": False}, {}, False, True)
        code, problem, guarded = self.runner._compile_source(source, True)
        scope = self._guards()[1]
        previous = sys.gettrace()
        sys.settrace(tracer)
        try:
            exec(code, scope)
        finally:
            sys.settrace(previous)
        self.assertEqual([20, 30], scope["result"])

    def _run_with_timeout(self, source, timeout_s):
        errors = []
        context = types.SimpleNamespace(
            Source=source,
            Workspace=None,
            TimeoutSeconds=timeout_s,
            InputsJson="{}",
            UIApp=types.SimpleNamespace(ActiveUIDocument=None, Application=None),
            SetEngine=lambda *args: None,
            SetResult=lambda *args: None,
            SetOutput=lambda *args: None,
            SetError=lambda *args: errors.append(args[0]),
        )
        with mock.patch.object(self.runner, "_WATCHDOG_ESCALATE_SECONDS", 0.2):
            self.runner.run(context)
        return errors

    @unittest.skipUnless(
        hasattr(sys, "monitoring"), "Escalation needs CPython 3.12+ sys.monitoring"
    )
    def test_escalation_stops_loops_the_guards_never_see(self):
        """Stop swallowing loops in async for and in code compiled at run time."""
        sources = {
            "exec": (
                "exec('while True:\\n    try:\\n        for i in range(10 ** 9):\\n"
                "            pass\\n    except:\\n        pass\\n')\n"
            ),
            "async_for": (
                "import asyncio\n"
                "Base = BaseException\n"
                "async def forever():\n"
                "    while True:\n"
                "        yield 1\n"
                "async def main():\n"
                "    async for value in forever():\n"
                "        try:\n"
                "            await asyncio.sleep(0)\n"
                "        except Base:\n"
                "            pass\n"
                "asyncio.run(main())\n"
            ),
        }
        for name, source in sorted(sources.items()):
            with self.subTest(loop=name):
                started = time.time()
                self.assertEqual(["timeout"], self._run_with_timeout(source, 0.2))
                self.assertLess(time.time() - started, 5)
                for tool_id in self.runner._ESCALATION_TOOL_IDS:
                    self.assertIsNone(sys.monitoring.get_tool(tool_id))

    def test_rank_cache_is_cleared_after_a_run(self):
        """Never keep a run's script classes, and through them its namespace."""
        context = types.SimpleNamespace(
            Source="class Holder(object):\n    pass\nkeep = Holder()\nresult = 1\n",
            Workspace=None,
            TimeoutSeconds=5,
            InputsJson="{}",
            UIApp=types.SimpleNamespace(ActiveUIDocument=None, Application=None),
            SetEngine=lambda *args: None,
            SetResult=lambda *args: None,
            SetOutput=lambda *args: None,
            SetError=lambda *args: self.fail(args),
        )
        self.runner.run(context)
        self.assertEqual({}, self.runner._TRANSACTION_RANKS)


LOOP_PAST_TIMEOUT = (
    "import time\n"
    "deadline = time.time() + 0.4\n"
    "count = 0\n"
    "while time.time() < deadline:\n"
    "    count += 1\n"
    "result = count\n"
)


class AgentRunnerRecklessTests(unittest.TestCase):
    """Reckless runs (issue #3815) skip the in-script checks; default runs keep them."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def _run(self, source, reckless, timeout_s=5):
        errors = []
        results = []
        context = types.SimpleNamespace(
            Source=source,
            Workspace=None,
            TimeoutSeconds=timeout_s,
            Reckless=reckless,
            InputsJson="{}",
            UIApp=types.SimpleNamespace(ActiveUIDocument=None, Application=None),
            SetEngine=lambda *args: None,
            SetResult=results.append,
            SetOutput=lambda *args: None,
            SetError=lambda *args: errors.append(args[0]),
        )
        with mock.patch.object(self.runner, "_WATCHDOG_ESCALATE_SECONDS", 0.2):
            self.runner.run(context)
        return errors, results

    def _trace_functions_installed(self, source, reckless):
        with mock.patch.object(sys, "settrace", wraps=sys.settrace) as settrace:
            errors, _ = self._run(source, reckless)
        self.assertEqual([], errors)
        return [call.args[0] for call in settrace.call_args_list if call.args[0]]

    def test_reckless_runs_the_source_unrewritten(self):
        """No loop-header guards and no handler narrowing touch the source."""
        runner = self.runner
        with (
            mock.patch.object(
                runner, "_compile_source", wraps=runner._compile_source
            ) as compile_source,
            mock.patch.object(
                runner, "_guard_loop_headers", wraps=runner._guard_loop_headers
            ) as guard_loops,
        ):
            errors, results = self._run(
                "names = [n for n in globals() if n.startswith('__agent')]\n"
                "for _ in range(2):\n    pass\n"
                "try:\n    pass\nexcept:\n    pass\n"
                "result = names\n",
                reckless=True,
            )
        self.assertEqual([], errors)
        self.assertEqual(["[]"], results)
        compile_source.assert_not_called()
        guard_loops.assert_not_called()

    def test_reckless_installs_no_trace_function(self):
        """A script that names a transaction still runs with no tracer at all."""
        source = "label = 'DB.Transaction'\nresult = [v for v in range(3)]\n"
        self.assertEqual([], self._trace_functions_installed(source, reckless=True))

    def test_default_run_still_traces_a_script_that_names_a_transaction(self):
        """The checked default keeps tracking transactions line by line."""
        source = "label = 'DB.Transaction'\nresult = [v for v in range(3)]\n"
        self.assertNotEqual([], self._trace_functions_installed(source, reckless=False))

    def test_reckless_does_not_stop_a_loop_past_its_timeout(self):
        """The timeout is not enforced: no watchdog, no timeout error."""
        with mock.patch.object(
            self.runner, "_start_watchdog", wraps=self.runner._start_watchdog
        ) as watchdog:
            errors, results = self._run(LOOP_PAST_TIMEOUT, True, timeout_s=0.05)
        self.assertEqual([], errors)
        self.assertEqual(1, len(results))
        watchdog.assert_not_called()

    def test_default_run_still_stops_a_loop_past_its_timeout(self):
        """Checked execution stays the default and still enforces the timeout."""
        errors, results = self._run(LOOP_PAST_TIMEOUT, False, timeout_s=0.05)
        self.assertEqual(["timeout"], errors)
        self.assertEqual([], results)

    def test_reckless_still_rolls_back_transactions_left_open_in_globals(self):
        """The end-of-run cleanup of script globals runs in reckless mode too."""
        created = []

        class OpenTransaction(self.runner.DB.Transaction):
            def __init__(self):
                self.started = False
                self.rolled_back = False
                created.append(self)

            def Start(self):
                self.started = True

            def HasStarted(self):
                return self.started

            def HasEnded(self):
                return self.rolled_back

            def RollBack(self):
                self.rolled_back = True

        doubles = types.ModuleType("reckless_doubles")
        doubles.OpenTransaction = OpenTransaction
        with mock.patch.dict(sys.modules, {"reckless_doubles": doubles}):
            errors, _ = self._run(
                "from reckless_doubles import OpenTransaction\n"
                "kept = [OpenTransaction()]\n"
                "kept[0].Start()\n"
                "t = OpenTransaction()\n"
                "t.Start()\n"
                "result = 1\n",
                reckless=True,
            )
        self.assertEqual(["transaction_left_open"], errors)
        self.assertEqual(2, len(created))
        self.assertTrue(all(transaction.rolled_back for transaction in created))


class AgentRunnerSourceTests(unittest.TestCase):
    """Constraints on the runner file itself."""

    def test_runner_source_is_ascii_for_ironpython_two(self):
        """IronPython 2.7 refuses a non-ASCII module without a coding line."""
        with open(RUNNER_PATH, "rb") as runner_file:
            source = runner_file.read()
        offending = [
            number
            for number, line in enumerate(source.splitlines(), 1)
            if any(byte > 127 for byte in line)
        ]
        self.assertEqual([], offending)


if __name__ == "__main__":
    unittest.main()
