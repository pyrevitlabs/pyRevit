"""In-engine runner for agent-submitted source.

The agent host writes an entry script that calls :func:`run` with the
``AgentScriptContext`` it built. The runner executes the agent source in a
fresh namespace, captures everything printed, serializes ``result`` to JSON,
and reports all of it back through the context.

Invariant:
    This module must stay parseable by IronPython 2.7, IronPython 3.4 and
    CPython 3, because the host picks the engine per request.

Invariant:
    pyrevitlib is loaded live while the host is a compiled DLL that only
    changes after a rebuild and a Revit restart, so this module can meet an
    older ``AgentScriptContext``. Read any context member added after the
    first release with ``getattr`` and a default that keeps the old behavior.
"""

import ast
import json
import keyword
import linecache
import os.path as op
import re
import sys
import threading
import time
import tokenize
import traceback
import types
from itertools import compress

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import System

from pyrevit.api import DB, UI
from pyrevit.compat import IRONPY, get_elementid_value_func

SOURCE_NAME = "<agent-script>"

_WATCHDOG_RETRY_SECONDS = 0.2
_WATCHDOG_ESCALATE_SECONDS = 1.0
_ESCALATION_TOOL_IDS = (4, 3)
_START_RECORDER = "__agent_start__"
_CO_OPTIMIZED = 0x1

_clock = getattr(time, "perf_counter", None) or time.time

_elementid_value_raw = get_elementid_value_func()

_NET_INTEGER_TYPES = (
    System.Int16,
    System.Int32,
    System.Int64,
    System.UInt16,
    System.UInt32,
    System.UInt64,
)
_NET_FLOAT_TYPES = (System.Single, System.Double, System.Decimal)


class RunTimedOut(BaseException):
    """Raised inside the agent script once its time limit has passed.

    Derives from ``BaseException`` so a script's ``except Exception`` can't
    swallow it. The runner narrows every bare ``except`` and ``except
    BaseException`` (or ``except builtins.BaseException``) in the script to
    ``except Exception`` before compiling, and records that the deadline
    passed so :func:`run` fails the run even if the script then ends
    normally. A handler that still catches it, such
    as one reached through an alias, is stopped at the next rewritten loop
    header, or on CPython 3.12+ by the watchdog's jump escalation.
    """


class _NarrowBroadHandlers(ast.NodeTransformer):
    """Turn handlers that would catch ``RunTimedOut`` into ``except Exception``.

    Narrowing keeps ``RunTimedOut`` away from the handlers the runner can
    see. Code it does not rewrite, such as runtime-compiled code, relies on
    the jump escalation on CPython 3.12+ and on the trace function on
    IronPython, which Python removes once it has raised; a loop there that
    catches the timeout can't be stopped again.
    """

    def __init__(self):
        ast.NodeTransformer.__init__(self)
        self.narrowed = []

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        if _catches_base_exception(node.type):
            original_type = node.type
            node.type = ast.copy_location(
                ast.Name(id="Exception", ctx=ast.Load()), original_type or node
            )
            self.narrowed.append(node)
        return node


def _catches_base_exception(handler_type):
    if handler_type is None:
        return True
    if isinstance(handler_type, ast.Name):
        return handler_type.id == "BaseException"
    if isinstance(handler_type, ast.Attribute):
        return handler_type.attr == "BaseException"
    if isinstance(handler_type, ast.Tuple):
        return any(_catches_base_exception(item) for item in handler_type.elts)
    return False


def _source_lines(source):
    """Split physical source lines without treating string contents as newlines."""
    lines = []
    start = 0
    for match in re.finditer(r"\r\n|\r|\n", source):
        lines.append(source[start : match.end()])
        start = match.end()
    if start < len(source):
        lines.append(source[start:])
    return lines


def _narrow_source_handlers(source, handlers):
    """Rewrite only handler headers without compiling an AST on IronPython.

    IronPython loses source lines when compiling ASTs even when their locations
    are populated. Keep the original source and its newline count instead,
    including multiline exception tuples and Python 2 exception bindings.
    Preserve the star in exception group handlers while narrowing their types.

    Raises:
        ValueError: not every handler header was found in the source; the
            caller then compiles the narrowed AST instead of source that would
            still catch the timeout.
    """
    positions = set((node.lineno, node.col_offset) for node in handlers)
    lines = _source_lines(source)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    replacements = []
    header_start = None
    depth = 0
    token_source = source.replace("\r\n", "\n").replace("\r", "\n")
    for token in tokenize.generate_tokens(StringIO(token_source).readline):
        token_type, text, start, end, _ = token
        if header_start is None:
            if text == "except" and start in positions:
                header_start = end
                depth = 0
                type_started = False
            continue
        if not type_started:
            type_started = True
            if text == "*":
                header_start = end
                continue
        if depth == 0 and text in (":", "as", ","):
            first = offsets[header_start[0] - 1] + header_start[1]
            last = offsets[start[0] - 1] + start[1]
            newlines = "".join(re.findall(r"\r\n|\r|\n", source[first:last]))
            replacement = " (Exception" + newlines + ") "
            replacements.append((first, last, replacement))
            header_start = None
        elif token_type == tokenize.OP:
            if text in ("(", "[", "{"):
                depth += 1
            elif text in (")", "]", "}"):
                depth -= 1
    if len(replacements) != len(positions):
        raise ValueError(
            "rewrote {} of {} handler headers".format(len(replacements), len(positions))
        )
    for first, last, replacement in reversed(replacements):
        source = source[:first] + replacement + source[last:]
    return source


def _guard_loop_headers(source):
    """Make every loop in the source check the run deadline on each iteration.

    ``for`` loops and comprehensions iterate ``__agent_loop__((iterable))``
    and ``while`` conditions become ``__agent_tick__() and (condition)``.
    Only the header expressions change and every newline stays in place, so
    line numbers and tracebacks still match the submitted source. Closing
    parentheses go right after the expression's last token, so columns on
    the following lines stay put too. ``async for`` loops are left alone:
    only CPython runs them, and its watchdog interrupts them.

    Raises:
        Exception: the source could not be tokenized; compile it unguarded.
    """
    lines = _source_lines(source)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset_of(position):
        return offsets[position[0] - 1] + position[1]

    insertions = []
    open_headers = []
    depth = 0
    last_end = None
    previous = None
    for token in _significant_tokens(source):
        token_type, text, start, end, _ = token
        while open_headers and _ends_loop_header(open_headers[-1], token, depth):
            header = open_headers.pop()
            if header["guarded"]:
                insertions.append((offset_of(last_end), header["close"]))
        last_end = end
        if token_type == tokenize.NAME:
            if text == "while":
                insertions.append((offset_of(end), " __agent_tick__() and ("))
                open_headers.append(
                    {"depth": depth, "close": ")", "iterating": True, "guarded": True}
                )
            elif text == "for":
                open_headers.append(
                    {
                        "depth": depth,
                        "close": "))",
                        "iterating": False,
                        "guarded": previous != "async",
                    }
                )
            elif (
                text == "in"
                and open_headers
                and not open_headers[-1]["iterating"]
                and open_headers[-1]["depth"] == depth
            ):
                open_headers[-1]["iterating"] = True
                if open_headers[-1]["guarded"]:
                    insertions.append((offset_of(end), " __agent_loop__(("))
        elif token_type == tokenize.OP:
            if text in ("(", "[", "{"):
                depth += 1
            elif text in (")", "]", "}"):
                depth -= 1
        previous = text
    if open_headers:
        raise SyntaxError("unterminated loop header")
    for position, text in sorted(insertions, key=lambda item: item[0], reverse=True):
        source = source[:position] + text + source[position:]
    return source


class _WorkspaceLoopGuard(object):
    """Import hook that compiles the workspace's modules with guarded loops.

    Active only while a run is, on ``sys.meta_path``. A module found under the
    run's workspace folder, and only when ``sys.path`` order selects it, is
    compiled through :func:`_guard_loop_headers` and
    gets the run's ``__agent_tick__`` and ``__agent_loop__``, so a timeout
    stops loops inside workspace code. Everything outside the workspace,
    pyrevitlib and rpw included, imports as usual and stays unguarded.

    Note:
        Both the PEP 302 protocol (``find_module``/``load_module``, IronPython
        2.7) and the PEP 451 one (``find_spec``/``exec_module``) are
        implemented. A module whose source can't be rewritten is imported
        unguarded.
    """

    def __init__(self, workspace, guards):
        self._root = _folder_root(workspace)
        self._guards = guards
        self._paths = {}

    def _locate(self, fullname, path):
        if path is None and fullname in sys.builtin_module_names:
            return None
        if path is not None and not self._owns_parent(fullname):
            return None
        name = fullname.rpartition(".")[2]
        folders = path if path is not None else sys.path
        folders = [f for f in folders if f and isinstance(f, str)]
        for folder in folders:
            package = op.join(folder, name, "__init__.py")
            module = op.join(folder, name + ".py")
            found = (package, True) if op.isfile(package) else None
            found = found or ((module, False) if op.isfile(module) else None)
            if found:
                return found if _is_under(found[0], self._root) else None
        return None

    def _owns_parent(self, fullname):
        parent = sys.modules.get(fullname.rpartition(".")[0])
        return getattr(parent, "__loader__", None) is self

    def find_module(self, fullname, path=None):
        if not self._locate(fullname, path):
            return None
        self._paths[fullname] = path
        return self

    def load_module(self, fullname):
        filename, is_package = self._locate(fullname, self._paths.pop(fullname, None))
        module = types.ModuleType(fullname)
        module.__file__ = filename
        module.__loader__ = self
        if is_package:
            module.__path__ = [op.dirname(filename)]
            module.__package__ = fullname
        else:
            module.__package__ = fullname.rpartition(".")[0]
        sys.modules[fullname] = module
        try:
            self.exec_module(module)
        except BaseException:
            sys.modules.pop(fullname, None)
            raise
        return module

    def find_spec(self, fullname, path=None, target=None):
        located = self._locate(fullname, path)
        if not located:
            return None
        import importlib.util

        filename, is_package = located
        return importlib.util.spec_from_file_location(
            fullname,
            filename,
            loader=self,
            submodule_search_locations=[op.dirname(filename)] if is_package else None,
        )

    def get_data(self, path):
        with open(path, "rb") as handle:
            return handle.read()

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        with open(module.__file__, "rb") as handle:
            raw = handle.read()
        try:
            source = raw if isinstance(raw, str) else raw.decode("utf-8-sig")
            code = compile(_guard_loop_headers(source), module.__file__, "exec")
        except Exception as ex:
            print(
                "[pyRevit agent] Could not rewrite the loops of {} ({}: {}); "
                "its loops are not stopped by the timeout.".format(
                    module.__file__, type(ex).__name__, _safe_text(ex)
                )
            )
            code = compile(raw, module.__file__, "exec")
        module.__dict__.update(self._guards)
        exec(code, module.__dict__)


def _significant_tokens(source):
    token_source = source.replace("\r\n", "\n").replace("\r", "\n")
    for token in tokenize.generate_tokens(StringIO(token_source).readline):
        if token[0] not in _LAYOUT_TOKENS:
            yield token


def _runs_dynamic_code(source):
    """True when the source can compile and run code at run time.

    Code passed to ``exec``, ``eval``, ``execfile`` or the ``compile``
    builtin is never seen by :func:`_guard_loop_headers`, and IronPython 2.7's
    ``exec`` statement can't be intercepted, so such a run falls back to
    checking the deadline on every line of every frame. ``re.compile`` and
    other attribute calls named ``compile`` don't count.
    """
    previous = None
    for token in _significant_tokens(source):
        if token[0] == tokenize.NAME and token[1] in _DYNAMIC_CODE_NAMES:
            if token[1] != "compile" or previous != ".":
                return True
        previous = token[1]
    return False


_DYNAMIC_CODE_NAMES = ("exec", "eval", "execfile", "compile")


def _hides_loops_in_fstrings(source):
    """True when an f-string token holds a loop :func:`_guard_loop_headers` can't see.

    CPython before 3.12 tokenizes an f-string, replacement fields included,
    as one string token, and IronPython 3.4 as a name token for its prefix
    followed by one string token, so a comprehension inside one is never
    rewritten. Such a run falls back to checking the deadline on every line,
    like code compiled at run time.
    """
    previous = None
    for token in _significant_tokens(source):
        if token[0] == tokenize.STRING and _FIELD_LOOP.search(token[1]):
            prefix = re.match(r"[A-Za-z]*", token[1]).group()
            if _is_split_prefix(previous, token):
                prefix += previous[1]
            if "f" in prefix.lower():
                return True
        previous = token
    return False


def _is_split_prefix(previous, token):
    return (
        previous is not None
        and previous[0] == tokenize.NAME
        and set(previous[1].lower()) <= set("rbuf")
        and previous[3] == token[2]
    )


_FIELD_LOOP = re.compile(r"\{[^{}]*\b(?:for|while)\b")

_LAYOUT_TOKENS = (
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.COMMENT,
    tokenize.INDENT,
    tokenize.DEDENT,
)


def _ends_loop_header(header, token, depth):
    """True when ``token`` ends the guarded expression of an open loop header.

    A statement header (depth 0) ends at its colon. A comprehension's
    iterable ends at the next ``for``, ``if`` or ``async`` of the same
    comprehension, or at the bracket that closes it.
    """
    if not header["iterating"] or depth != header["depth"]:
        return False
    token_type, text = token[0], token[1]
    if header["depth"] == 0:
        return token_type == tokenize.OP and text == ":"
    if token_type == tokenize.NAME:
        return text in ("for", "if", "async")
    return token_type == tokenize.OP and text in (")", "]", "}")


def _compile_source(source, guard_loops=False):
    """Compile the agent source with broad exception handlers narrowed.

    Args:
        source (str): the agent source.
        guard_loops (bool): also rewrite loop headers with
            :func:`_guard_loop_headers`.

    Returns:
        tuple: the code object, None or a description of why source rewriting
        was skipped, and whether the loops are guarded. If rewritten source
        does not compile, compile the narrowed AST instead so broad handlers
        cannot swallow the timeout.

    Note:
        Prefer source text because IronPython reports every script frame as
        line 1 when compiling an AST. The fallback sacrifices source locations,
        not timeout safety.
    """
    tree = ast.parse(source, SOURCE_NAME, "exec")
    narrower = _NarrowBroadHandlers()
    narrower.visit(tree)
    narrowed_source = source
    if narrower.narrowed:
        try:
            narrowed_source = _narrow_source_handlers(source, narrower.narrowed)
            compile(narrowed_source, SOURCE_NAME, "exec")
        except Exception as ex:
            return (
                compile(ast.fix_missing_locations(tree), SOURCE_NAME, "exec"),
                "{}: {}; compiled the narrowed AST instead; source line numbers "
                "may be unavailable".format(type(ex).__name__, _safe_text(ex)),
                False,
            )
    if guard_loops:
        try:
            guarded_source = _guard_loop_headers(narrowed_source)
            return compile(guarded_source, SOURCE_NAME, "exec"), None, True
        except Exception as ex:
            return (
                compile(narrowed_source, SOURCE_NAME, "exec"),
                "{}: {}; loops check the deadline through line tracing instead".format(
                    type(ex).__name__, _safe_text(ex)
                ),
                False,
            )
    return compile(narrowed_source, SOURCE_NAME, "exec"), None, False


def _record_transaction_starts(source):
    """Route every ``<expr>.Start(...)`` call through ``__agent_start__``.

    ``t.Start()`` becomes ``__agent_start__(t).Start()``, which records ``t``
    if it is a Revit transaction before starting it. The object a start is
    called on is recorded whatever name, alias, factory or ``getattr`` it
    came from, and stays recorded after its variable is rebound, so these
    runs need no trace function to find a transaction left open. Only the
    object expression is wrapped and no newline is added, so line numbers
    still match the submitted source.

    Returns:
        tuple: the rewritten source, and whether every ``Start`` in the source
        is a wrapped call. It is False, and the source is returned unchanged,
        when the rewrite could not be proven to wrap exactly the ``.Start(``
        calls the parser sees; it is also False when ``Start`` appears any
        other way (``getattr(t, "Start")``, ``start = t.Start``, a name), since
        a start through it would not be recorded.

    Invariant:
        The rewrite is checked against the AST: the rewritten source must
        parse to the original tree with each ``.Start`` call's object wrapped
        in ``__agent_start__(...)``, and nothing else changed. The check also
        runs when the tokens show no ``Start`` call but the source contains
        the word, because IronPython 3.4 keeps an f-string, calls included,
        as one string token.
    """
    try:
        tokens = list(_significant_tokens(source))
    except Exception:
        return source, False
    lines = _source_lines(source)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset_of(position):
        return offsets[position[0] - 1] + position[1]

    insertions = []
    complete = True
    for index, token in enumerate(tokens):
        token_type, text = token[0], token[1]
        if token_type == tokenize.STRING and _is_start_literal(text):
            complete = False
        if token_type != tokenize.NAME or text != "Start":
            continue
        if not (
            0 < index < len(tokens) - 1
            and _is_op(tokens[index - 1], ".")
            and _is_op(tokens[index + 1], "(")
        ):
            complete = False
            continue
        first = _primary_start(tokens, index - 2)
        if first is None:
            return source, False
        insertions.append((offset_of(tokens[first][2]), _START_RECORDER + "("))
        insertions.append((offset_of(tokens[index - 2][3]), ")"))
    if not insertions and "Start" not in source:
        return source, complete
    rewritten = source
    for position, text in sorted(insertions, key=lambda item: item[0], reverse=True):
        rewritten = rewritten[:position] + text + rewritten[position:]
    try:
        expected = _WrapStartCalls().visit(ast.parse(source, SOURCE_NAME, "exec"))
        if ast.dump(expected) != ast.dump(ast.parse(rewritten, SOURCE_NAME, "exec")):
            return source, False
    except Exception:
        return source, False
    return rewritten, complete


class _WrapStartCalls(ast.NodeTransformer):
    """The AST :func:`_record_transaction_starts` must produce, built from the tree."""

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "Start":
            recorder = ast.parse(_START_RECORDER + "(target)", mode="eval").body
            recorder.args[0] = node.func.value
            node.func.value = recorder
        return node


def _is_op(token, text):
    return token[0] == tokenize.OP and token[1] == text


def _is_start_literal(text):
    return text.lstrip("rRbBuUfF").strip("\"'") == "Start"


_CLOSING_BRACKETS = {")": "(", "]": "[", "}": "{"}


def _primary_start(tokens, index):
    """Index of the first token of the primary expression ending at ``index``.

    Walks back over names, attribute dots, strings and bracket groups: a
    group preceded by a name, a string or another group is a call or a
    subscript of it, while one preceded by a keyword or an operator starts
    the expression. Returns None for anything else.
    """
    while index >= 0:
        token_type, text = tokens[index][0], tokens[index][1]
        if token_type == tokenize.OP and text in _CLOSING_BRACKETS:
            index = _matching_bracket(tokens, index)
            if index is None:
                return None
            if index > 0 and _continues_primary(tokens[index - 1]):
                index -= 1
                continue
            return index
        if token_type == tokenize.NAME and not keyword.iskeyword(text):
            if index > 1 and _is_op(tokens[index - 1], "."):
                index -= 2
                continue
            return index
        if token_type == tokenize.STRING:
            while index > 0 and tokens[index - 1][0] == tokenize.STRING:
                index -= 1
            return index
        return None
    return None


def _matching_bracket(tokens, index):
    depth = 0
    while index >= 0:
        token_type, text = tokens[index][0], tokens[index][1]
        if token_type == tokenize.OP:
            if text in _CLOSING_BRACKETS:
                depth += 1
            elif text in ("(", "[", "{"):
                depth -= 1
                if depth == 0:
                    return index
        index -= 1
    return None


def _continues_primary(token):
    token_type, text = token[0], token[1]
    if token_type == tokenize.NAME:
        return not keyword.iskeyword(text)
    if token_type == tokenize.OP:
        return text in _CLOSING_BRACKETS
    return token_type == tokenize.STRING


def _needs_transaction_tracking(workspace, starts_recorded, dynamic_code):
    """True when transactions left open must be found by tracing script frames.

    A run whose every ``.Start(`` call goes through ``__agent_start__`` (see
    :func:`_record_transaction_starts`) needs no trace function. Tracing stays
    for starts the rewrite can't see: workspace helpers that return a
    started transaction, code compiled at run time, and ``Start`` reached
    any other way than a direct call.
    """
    return bool(workspace) or not starts_recorded or dynamic_code


def _start_recorder(transactions):
    """Return the ``__agent_start__`` function for one run.

    It records its argument in ``transactions`` when it is a Revit
    transaction and returns it, so the wrapped ``.Start(...)`` runs on the
    same object. Called on a transaction class itself, as in
    ``DB.Transaction.Start(t)``, it returns a stand-in whose ``Start``
    records ``t`` instead.
    """

    def agent_start(target):
        if isinstance(target, type) and _transaction_rank(target) is not None:
            return _UnboundStart(target, transactions)
        _track_transaction(target, transactions)
        return target

    return agent_start


class _UnboundStart(object):
    def __init__(self, kind, transactions):
        self._kind = kind
        self._transactions = transactions

    def Start(self, transaction, *args):
        _track_transaction(transaction, self._transactions)
        return self._kind.Start(transaction, *args)


def _execution_tracer(timeout_s, state, transactions, check_lines, track):
    """Build the ``sys.settrace`` function for one run.

    With ``track`` on, which :func:`run` only asks for when
    :func:`_needs_transaction_tracking` says the start recorder can't see
    every start, every frame running the agent source records the Revit
    transactions it holds on every line, so a transaction stays found even
    after its variable is rebound or deleted. The module frame does so
    through its globals. pyRevit, rpw and workspace code runs untraced. With
    ``check_lines`` on, every frame, the script's own and any code it
    compiles at run time or calls, also checks the watchdog's flag on each
    line.

    Warning:
        On CPython 3.12, never read ``f_locals`` from a line event of a frame
        whose locals are a plain dict: the module or a class body. The trace
        machinery writes the locals back into the frame, which clobbers the
        loop variable of an inlined comprehension (PEP 709); a module-level
        ``[v for v in values if v]`` silently came back empty. Function
        frames (``CO_OPTIMIZED``) are safe, so class bodies are read only
        when they return or an exception leaves them.

    Note:
        Line events are the dominant cost of a traced run: about 3
        microseconds each on IronPython, plus the cost of reading
        ``f_locals``. Tracing every line of every frame made a 200k-step
        loop take seconds (issue #3815), so loops are normally stopped by
        :func:`_guard_loop_headers` instead, and the module frame's globals
        are checked by type (see :func:`_track_globals`).
    """
    dict_locals_on_lines = _implementation() != "cpython"

    def raise_if_timed_out(frame):
        if state["timed_out"]:
            _track_stack_transactions(frame, transactions)
            raise RunTimedOut(timeout_s)

    def track_module(frame, event, arg):
        _track_globals(frame.f_globals, transactions)
        if event == "line":
            raise_if_timed_out(frame)
        return track_module

    def track_every_line(frame, event, arg):
        _track_frame_transactions(frame, transactions)
        if event == "line":
            raise_if_timed_out(frame)
        return track_every_line

    def track_on_exit(frame, event, arg):
        if event == "line":
            raise_if_timed_out(frame)
        else:
            _track_frame_transactions(frame, transactions)
        return track_on_exit

    def check_deadline(frame, event, arg):
        if event == "line":
            raise_if_timed_out(frame)
        return check_deadline

    def trace_call(frame, event, arg):
        code = frame.f_code
        if not track or code.co_filename != SOURCE_NAME:
            return check_deadline if check_lines else None
        if code.co_name == "<module>":
            return track_module
        if dict_locals_on_lines or code.co_flags & _CO_OPTIMIZED:
            return track_every_line
        return track_on_exit

    return trace_call


def _loop_guards(timeout_s, state, transactions):
    """Return the ``__agent_tick__`` and ``__agent_loop__`` functions for one run.

    Both raise ``RunTimedOut`` once the watchdog has set
    ``state["timed_out"]``. They run in loop headers, outside any ``try`` in
    the loop body, so the script cannot swallow the timeout and keep looping.
    """

    def raise_timed_out():
        try:
            _track_stack_transactions(sys._getframe(2), transactions)
        except Exception:
            pass
        raise RunTimedOut(timeout_s)

    def agent_tick():
        if state["timed_out"]:
            raise_timed_out()
        return True

    def agent_loop(iterable):
        return guarded(iter(iterable))

    def guarded(iterator):
        for item in iterator:
            if state["timed_out"]:
                raise_timed_out()
            yield item

    return agent_tick, agent_loop


def _start_watchdog(timeout_s, state):
    """Set ``state["timed_out"]`` once ``timeout_s`` passes.

    The loop guards, or the line tracer when loops are unguarded, raise
    ``RunTimedOut`` when they next see the flag. On CPython the watchdog also
    keeps raising ``RunTimedOut`` in the script thread itself, which stops
    code the guards never see, such as a loop in a library function.

    An injection lands wherever the script happens to be, usually inside a
    loop body, so a handler the runner could not narrow, such as one
    reached through an alias or one in code compiled at run time, can
    swallow every one of them. If the run is still going
    ``_WATCHDOG_ESCALATE_SECONDS`` after the deadline, the watchdog arms a
    :class:`_JumpEscalation`, which raises at every backward jump: the end
    of a loop body, outside any ``try`` inside that body.

    Invariant:
        The script thread sets ``state["finished"]`` with a plain store once
        the script and the serialization of its ``result``, which can still
        run script code, are done, and at the latest when it stops the
        watchdog. From then on nothing new is
        raised in that thread, even if ``RunTimedOut`` interrupts the runner
        before it calls the returned function, so an injection can never
        outlive the run and reach other Python code on Revit's main thread.

    Returns:
        function: stops the watchdog and clears any injection still pending.
        It is also stored as ``state["stop_watchdog"]`` before the watchdog
        starts, so the runner can stop it even when ``RunTimedOut`` lands
        before this function has returned.
    """
    stopped = threading.Event()
    thread_id = threading.current_thread().ident
    inject = _timeout_injector(thread_id, state)
    escalation = _JumpEscalation(thread_id, timeout_s, state)

    def watch():
        if stopped.wait(timeout_s):
            return
        state["timed_out"] = True
        if inject is None:
            return
        escalate_at = _clock() + _WATCHDOG_ESCALATE_SECONDS
        while not stopped.is_set() and not state["finished"]:
            inject(RunTimedOut)
            if _clock() >= escalate_at:
                escalation.arm()
            stopped.wait(_WATCHDOG_RETRY_SECONDS)

    thread = threading.Thread(target=watch)
    thread.daemon = True

    def stop():
        state["finished"] = True
        stopped.set()
        if inject is None:
            return
        while True:
            try:
                thread.join()
                inject(None)
                escalation.release()
                return
            except RunTimedOut:
                pass

    state["stop_watchdog"] = stop
    thread.start()
    return stop


class _JumpEscalation(object):
    """Raise ``RunTimedOut`` at every backward jump of one thread (CPython 3.12+).

    Every loop iteration ends in a backward jump that sits after the loop
    body, so a ``try`` inside the body can't catch what is raised there. An
    enclosing loop that catches it hits its own backward jump next, so
    nothing that keeps looping can keep the run alive: not an aliased
    ``BaseException`` handler, an ``async for``, nor code compiled at run
    time. Uses a ``sys.monitoring`` tool id, so it costs nothing until it is
    armed and does nothing when no id is free or the engine lacks
    ``sys.monitoring``.

    Invariant:
        Once ``state["finished"]`` is set the callback never raises and
        :meth:`arm` does nothing. :meth:`release` must follow once the
        watchdog has stopped.
    """

    def __init__(self, thread_id, timeout_s, state):
        self._state = state
        self._thread_id = thread_id
        self._timeout_s = timeout_s
        self._tool_id = None
        self._lock = threading.Lock()

    def arm(self):
        monitoring = getattr(sys, "monitoring", None)
        with self._lock:
            if (
                monitoring is None
                or self._state["finished"]
                or self._tool_id is not None
            ):
                return
            for tool_id in _ESCALATION_TOOL_IDS:
                if monitoring.get_tool(tool_id) is None:
                    break
            else:
                return
            monitoring.use_tool_id(tool_id, "pyRevit agent timeout")
            self._tool_id = tool_id
            monitoring.register_callback(tool_id, monitoring.events.JUMP, self._on_jump)
            monitoring.set_events(tool_id, monitoring.events.JUMP)

    def release(self):
        with self._lock:
            tool_id, self._tool_id = self._tool_id, None
            if tool_id is None:
                return
            monitoring = sys.monitoring
            monitoring.set_events(tool_id, 0)
            monitoring.register_callback(tool_id, monitoring.events.JUMP, None)
            monitoring.free_tool_id(tool_id)

    def _on_jump(self, code, offset, destination):
        if (
            not self._state["finished"]
            and destination < offset
            and threading.get_ident() == self._thread_id
        ):
            raise RunTimedOut(self._timeout_s)


def _timeout_injector(thread_id, state):
    """Return ``inject(exc_type)`` that raises in the script thread, or None.

    None on engines without :func:`_set_async_exc_function`.
    ``inject(None)`` clears an injection still pending.

    Invariant:
        ``inject(RunTimedOut)`` reads ``state["finished"]`` and calls
        ``PyThreadState_SetAsyncExc`` with prebuilt arguments and no Python
        call in between, so the GIL can't pass to the script thread between
        the check and the injection. Building the ctypes arguments inside
        ``inject`` would reopen that window.
    """
    raw = _set_async_exc_function()
    if raw is None:
        return None
    import ctypes

    target = ctypes.c_ulong(thread_id)
    timed_out = ctypes.py_object(RunTimedOut)

    def inject(exc_type):
        if exc_type is None:
            raw(target, None)
        elif not state["finished"]:
            raw(target, timed_out)

    return inject


def _set_async_exc_function():
    """Return CPython's ``PyThreadState_SetAsyncExc``, or None on other engines.

    Only CPython can raise an exception in a running thread from outside it;
    IronPython has no equivalent on .NET Core.
    """
    if _implementation() != "cpython":
        return None
    try:
        import ctypes

        return ctypes.pythonapi.PyThreadState_SetAsyncExc
    except (ImportError, AttributeError):
        return None


class _PhaseClock(object):
    """Report runner phase durations through ``context.ReportTiming``.

    Hosts built before ``ReportTiming`` existed get nothing reported.
    """

    def __init__(self, context):
        self._report = getattr(context, "ReportTiming", None)
        self._last = _clock()

    def lap(self, phase):
        now = _clock()
        if self._report is not None:
            try:
                self._report(phase, (now - self._last) * 1000.0)
            except Exception:
                self._report = None
        self._last = now


def _finish_and_stop_watchdog(state):
    """Mark the script finished and stop its watchdog, whatever is still pending.

    Invariant:
        Retries until both are done: an injection already in flight can land on
        any statement here, and leaving the watchdog running would keep raising
        ``RunTimedOut`` into Revit's main thread after the run.
    """
    while True:
        try:
            state["finished"] = True
            stop_watchdog = state.get("stop_watchdog")
            if stop_watchdog:
                stop_watchdog()
            return
        except RunTimedOut:
            pass


def run(context):
    """Execute ``context.Source`` and report the outcome on ``context``.

    Args:
        context (AgentScriptContext): run request and outcome sink from the host.

    Note:
        Never raises. Script errors, including a failure to serialize
        ``result``, are reported through ``context.SetError`` so the host can
        roll the run back.

    Note:
        ``context.TimeoutSeconds`` is enforced by a watchdog thread that sets
        a flag every loop header of the agent source checks (see
        :func:`_guard_loop_headers`); on CPython it also raises
        ``RunTimedOut`` in the script thread. It stops Python code, including
        loops, but not a single blocking call such as a long Revit API call or
        ``time.sleep``, nor, on IronPython, a long loop inside a
        pyrevitlib or rpw function the script calls; the run fails with
        ``timeout`` once that call returns. Modules imported from the
        ``workspace`` folder get the same loop rewrite through an import hook
        (:class:`_WorkspaceLoopGuard`) that lives only as long as the run.
        On IronPython, a run with no trace function
        (see ``docs/agent-runtime.md``) has no check outside loop headers, so
        unbounded recursion or a callback passed to ``map``, ``filter`` or
        ``sorted`` over an endless iterable is not stopped.

    Note:
        Transactions the script leaves open are found by rewriting each
        ``<expr>.Start(...)`` call to record its object first (see
        :func:`_record_transaction_starts`), so a script that opens
        transactions runs as fast as one that doesn't. A line tracer is only
        installed when that can't see every start: a ``workspace`` run, code
        compiled at run time, or ``Start`` reached other than by a direct
        call. Reported tracebacks leave out this module's frames.

    Warning:
        When ``context.Reckless`` is true (``[agent] reckless``, see
        ``docs/agent-runtime.md``), none of the above applies: the source is
        compiled as submitted, no watchdog starts, no trace function is
        installed, and ``context.TimeoutSeconds`` is not enforced at all, so a
        runaway loop blocks Revit until the process is ended. Transactions
        left open are still rolled back, but only those reachable from the
        script's globals; one left open inside a function is not found and
        can crash Revit when it is finalized.

    Warning:
        The source is compiled with every bare ``except`` and ``except
        BaseException`` narrowed to ``except Exception``, so a script cannot
        swallow ``RunTimedOut`` there, and can no longer catch
        ``KeyboardInterrupt`` or ``SystemExit`` that way. A script that
        suppresses it some other way, such as through an alias, is stopped
        again at its next loop header, and on CPython 3.12+ at the end of
        any loop it is still in a second later (see :func:`_start_watchdog`).
    """
    phases = _PhaseClock(context)
    context.SetEngine(_implementation(), sys.version.split()[0], sys.version)
    source = context.Source
    linecache.cache[SOURCE_NAME] = (
        len(source),
        None,
        _source_lines(source),
        SOURCE_NAME,
    )
    captured = StringIO()
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    sys.stdout = captured
    sys.stderr = captured
    failed = False
    workspace = None
    workspace_guard = None
    workspace_folder = context.Workspace
    namespace = None
    left_open = 0
    reckless = bool(getattr(context, "Reckless", False))
    timeout_s = None if reckless else getattr(context, "TimeoutSeconds", None)
    state = {"timed_out": False, "finished": False}
    timed_out_after_script = False
    tracked_transactions = {}
    try:
        workspace = _enter_workspace(context.Workspace)
        namespace = _build_namespace(context)
        guard_loops = bool(timeout_s)
        if guard_loops:
            (
                namespace["__agent_tick__"],
                namespace["__agent_loop__"],
            ) = _loop_guards(timeout_s, state, tracked_transactions)
            if workspace_folder:
                workspace_guard = _WorkspaceLoopGuard(
                    workspace_folder,
                    {
                        name: namespace[name]
                        for name in ("__agent_tick__", "__agent_loop__")
                    },
                )
                sys.meta_path.insert(0, workspace_guard)
        phases.lap("setup")
        if reckless:
            code = compile(source, SOURCE_NAME, "exec")
            rewrite_problem, track, unguarded_code = None, False, False
        else:
            namespace[_START_RECORDER] = _start_recorder(tracked_transactions)
            recorded_source, starts_recorded = _record_transaction_starts(source)
            code, rewrite_problem, loops_guarded = _compile_source(
                recorded_source, guard_loops
            )
            dynamic_code = _runs_dynamic_code(source)
            track = _needs_transaction_tracking(
                context.Workspace, starts_recorded, dynamic_code
            )
            unguarded_code = (
                not loops_guarded or dynamic_code or _hides_loops_in_fstrings(source)
            )
        phases.lap("compile")
        if rewrite_problem:
            print(
                "[pyRevit agent] Could not rewrite the script's headers ({}).".format(
                    rewrite_problem
                )
            )
        check_lines = (
            guard_loops and unguarded_code and _set_async_exc_function() is None
        )
        started = time.time()
        try:
            if timeout_s:
                _start_watchdog(timeout_s, state)
            if check_lines or track:
                sys.settrace(
                    _execution_tracer(
                        timeout_s, state, tracked_transactions, check_lines, track
                    )
                )
            script_exit = None
            try:
                exec(code, namespace)
            except SystemExit as ex:
                script_exit = ex
            finally:
                phases.lap("exec")

            if script_exit is not None:
                if not _is_successful_exit(script_exit):
                    failed = True
                    context.SetError(
                        "SystemExit", _system_exit_message(script_exit), ""
                    )
            if not failed and "result" in namespace:
                try:
                    context.SetResult(
                        json.dumps(
                            namespace["result"],
                            default=_to_jsonable,
                            ensure_ascii=False,
                        )
                    )
                except Exception as ex:
                    failed = True
                    context.SetError(
                        "ResultSerializationError",
                        _safe_text(ex),
                        _format_script_traceback(),
                    )
                phases.lap("result")

            state["finished"] = True
            if state["timed_out"] or (timeout_s and time.time() - started > timeout_s):
                timed_out_after_script = True
                raise RunTimedOut(timeout_s)
        finally:
            _finish_and_stop_watchdog(state)
            sys.settrace(None)
    except RunTimedOut:
        failed = True
        if timed_out_after_script:
            context.SetError("timeout", _late_timeout_message(timeout_s), "")
        else:
            context.SetError(
                "timeout",
                "The script ran longer than its {:g} second limit and was stopped; "
                "its changes were rolled back. Pass a larger timeout_s if the work "
                "needs more time.".format(timeout_s),
                _format_script_traceback(),
            )
    except Exception as ex:
        failed = True
        error_type, message = _describe_error(ex)
        context.SetError(error_type, message, _format_script_traceback())
    finally:
        if workspace_guard is not None:
            sys.meta_path[:] = [
                finder for finder in sys.meta_path if finder is not workspace_guard
            ]
        if namespace is not None:
            left_open = _roll_back_open_transactions(namespace, tracked_transactions)
        _TRANSACTION_RANKS.clear()
        _UNTRACKED_TYPES.clear()
        _TRACKED_TYPES.clear()
        _ATTRIBUTE_HOLDERS.clear()
        linecache.cache.pop(SOURCE_NAME, None)
        phases.lap("rollback")
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        _leave_workspace(context.Workspace, workspace)
        context.SetOutput(captured.getvalue())
        phases.lap("cleanup")

    if left_open and not failed:
        context.SetError(
            "transaction_left_open",
            "The script left {} transaction(s) open; they were rolled back. Commit or "
            "roll back every transaction it starts.".format(left_open),
            None,
        )
        return
    if failed or "result" not in namespace:
        return


def _late_timeout_message(timeout_s):
    return (
        "The script passed its {:g} second limit inside a call that could not be "
        "interrupted, such as a long Revit API call, and was stopped when it "
        "finished; its changes were rolled back. Pass a larger timeout_s if the "
        "work needs more time.".format(timeout_s)
    )


def _is_successful_exit(error):
    return error.code is None or error.code == 0


def _system_exit_message(error):
    return "The script exited with code {}".format(error.code)


_TRANSACTION_ORDER = (
    (DB.SubTransaction, 0),
    (DB.Transaction, 1),
    (DB.TransactionGroup, 2),
)


def _roll_back_open_transactions(namespace, tracked_transactions):
    """Roll back Revit transactions the script started and never ended.

    Revit keeps such a transaction open after the run, and the abandoned
    object is later finalized off the main thread, which crashes Revit. The
    runner records every transaction the script starts through
    ``__agent_start__`` (see :func:`_record_transaction_starts`), or, when
    that rewrite can't see every start, the transactions script frames hold
    while it executes; it then also inspects script globals, their immediate
    containers and the attributes of objects found there, such as
    ``pyrevit.revit.Transaction``. A reckless run records nothing while it
    executes, so only the globals are inspected.

    Returns:
        int: how many transactions were rolled back.
    """
    found = tracked_transactions
    for value in _reachable_values(namespace):
        _track_transaction(value, found)
    rolled_back = 0
    for _, transaction in sorted(found.values(), key=lambda item: item[0]):
        try:
            if transaction.HasStarted() and not transaction.HasEnded():
                transaction.RollBack()
                rolled_back += 1
        except Exception:
            pass
    return rolled_back


def _track_frame_transactions(frame, transactions):
    try:
        code = frame.f_code
        if code.co_filename != SOURCE_NAME:
            return
        if code.co_name == "<module>":
            variables = frame.f_globals
        else:
            variables = frame.f_locals
    except Exception:
        return
    _track_values(variables, transactions)


def _track_values(variables, transactions):
    """Record the transactions among a frame's locals and their attributes.

    Note:
        This runs on every traced line. The attributes of all the locals are
        gathered and checked by type in one pass (see :func:`_track_typed`):
        visiting them one call at a time made a traced loop in a method whose
        ``self`` has 40 attributes about 30 times slower.
    """
    try:
        values = list(variables.values())
    except Exception:
        return
    attributes = []
    for value in values:
        if type(value) is _CELL_TYPE:
            try:
                value = value.cell_contents
            except ValueError:
                continue
        value_type = type(value)
        if value_type not in _UNTRACKED_TYPES:
            _track_transaction(value, transactions)
            continue
        holds = _ATTRIBUTE_HOLDERS.get(value_type)
        if holds is None:
            holds = _holds_attributes(value)
        if holds:
            held = getattr(value, "__dict__", None)
            if type(held) is dict:
                attributes.extend(held.values())
    if attributes:
        _track_typed(attributes, transactions)


def _track_globals(variables, transactions):
    """Record the transactions among the module's globals on a traced line.

    Globals hold the whole run namespace, so walking them value by value on
    every line of a module-level loop was the main cost of a traced run.
    Their types are compared with the types already classified in builtins
    instead, and only values of a transaction type are visited.
    """
    try:
        values = list(variables.values())
    except Exception:
        return
    _track_typed(values, transactions)


def _track_typed(values, transactions):
    """Record the transactions among ``values``, comparing their types in bulk.

    Types not seen yet are classified first, so the rest of the work is set
    operations done in builtins rather than one Python call per value.
    """
    kinds = set(map(type, values))
    for kind in kinds.difference(_UNTRACKED_TYPES, _TRACKED_TYPES):
        _transaction_rank(kind)
    if kinds.isdisjoint(_TRACKED_TYPES):
        return
    for value in compress(values, map(_TRACKED_TYPES.__contains__, map(type, values))):
        _record_transaction(value, transactions)


def _track_stack_transactions(frame, transactions):
    while frame is not None:
        _track_frame_transactions(frame, transactions)
        frame = frame.f_back


def _track_transaction(value, transactions):
    """Record ``value`` if it is a transaction, else the transactions it holds.

    A Python object's own attributes are checked one level deep, which finds
    the transaction inside ``pyrevit.revit.Transaction``, the rpw wrappers
    and the script's own classes. Modules and classes are skipped: walking
    their namespaces on every traced line would cost too much.
    """
    if type(value) is _CELL_TYPE:
        try:
            value = value.cell_contents
        except ValueError:
            return
    if _record_transaction(value, transactions) or not _holds_attributes(value):
        return
    attributes = getattr(value, "__dict__", None)
    if type(attributes) is dict:
        _track_typed(list(attributes.values()), transactions)


def _holds_attributes(value):
    """Whether ``value`` is an object whose attributes may hold a transaction.

    Cached per type like :func:`_transaction_rank`, and cleared with it, so a
    .NET object costs one dictionary lookup per traced line.
    """
    value_type = type(value)
    try:
        return _ATTRIBUTE_HOLDERS[value_type]
    except KeyError:
        pass
    except TypeError:
        return False
    try:
        holds = not issubclass(value_type, (type, _MODULE_TYPE)) and hasattr(
            value, "__dict__"
        )
    except Exception:
        holds = False
    _ATTRIBUTE_HOLDERS[value_type] = holds
    return holds


def _record_transaction(value, transactions):
    rank = _transaction_rank(type(value))
    if rank is None:
        return False
    transactions[id(value)] = (rank, value)
    return True


_TRANSACTION_RANKS = {}

_UNTRACKED_TYPES = set()
_TRACKED_TYPES = set()
"""Types :func:`_transaction_rank` found not to be, or to be, transactions.

Cleared with ``_TRANSACTION_RANKS`` for the same reason.
"""

_ATTRIBUTE_HOLDERS = {}

_CELL_TYPE = type((lambda value: lambda: value)(None).__closure__[0])
"""IronPython with full frames reports function locals as closure cells."""

_MODULE_TYPE = type(sys)


def _transaction_rank(value_type):
    """Rollback order of a transaction type, or None for any other type.

    Cached per type because the tracer asks for every local on every traced
    line, and ``isinstance`` against .NET types is slow on both engines.

    Invariant:
        :func:`run` clears the cache when the run ends. The engine is reused
        between runs, and a cached script class would keep that run's whole
        namespace alive through its methods' globals.
    """
    try:
        return _TRANSACTION_RANKS[value_type]
    except KeyError:
        pass
    except TypeError:
        return None
    rank = None
    for kind, kind_rank in _TRANSACTION_ORDER:
        try:
            if issubclass(value_type, kind):
                rank = kind_rank
                break
        except Exception:
            pass
    _TRANSACTION_RANKS[value_type] = rank
    if rank is None:
        _UNTRACKED_TYPES.add(value_type)
    else:
        _TRACKED_TYPES.add(value_type)
    return rank


def _reachable_values(namespace):
    """Yield script globals, and the items of global containers that hold a transaction.

    A container's items are only walked when one of their types is a
    transaction type, because a script often keeps every element of the
    model in one list and walking it item by item costs about 3
    microseconds per item on IronPython.
    """
    for value in list(namespace.values()):
        yield value
        if isinstance(value, dict):
            items = list(value.values())
        elif isinstance(value, (list, tuple)):
            items = value
        else:
            continue
        if any(_transaction_rank(kind) is not None for kind in set(map(type, items))):
            for item in items:
                yield item


def _implementation():
    return "ironpython" if IRONPY else "cpython"


def _build_namespace(context):
    uiapp = context.UIApp
    uidoc = uiapp.ActiveUIDocument
    return {
        "__name__": "__main__",
        "uiapp": uiapp,
        "app": uiapp.Application,
        "uidoc": uidoc,
        "doc": uidoc.Document if uidoc else None,
        "DB": DB,
        "UI": UI,
        "inputs": json.loads(context.InputsJson or "{}"),
    }


def _enter_workspace(workspace):
    """Put the agent's workspace folder on sys.path with its modules unloaded.

    The script engine is reused between runs, so a module imported from the
    workspace would otherwise keep the code of the first run that imported
    it. Dropping those modules makes every run import the files as they are
    on disk now.
    """
    if not workspace:
        return None
    _unload_modules_under(workspace)
    added = workspace not in sys.path
    if added:
        sys.path.insert(0, workspace)
    return workspace if added else None


def _is_under(module_file, root):
    """True when a module's file is inside ``root``.

    Loaded modules can have a ``__file__`` that isn't a file path (built-in
    and dynamically created modules, assemblies); ``op.abspath`` raises on
    those in IronPython, so they are treated as outside the workspace.
    """
    if not isinstance(module_file, str) or not module_file:
        return False
    try:
        return (op.normcase(op.abspath(module_file)) + op.sep).startswith(root)
    except Exception:
        return False


def _folder_root(folder):
    return op.normcase(op.abspath(folder)).rstrip("/\\") + op.sep


def _unload_modules_under(folder):
    root = _folder_root(folder)
    for name, module in list(sys.modules.items()):
        if _is_under(getattr(module, "__file__", None), root):
            del sys.modules[name]


def _leave_workspace(workspace, added_to_path):
    """Unload the workspace's modules and drop the ``sys.path`` entry the run added.

    A module left loaded would shadow a module of the same name in a different
    workspace folder on a later run, since ``import`` returns the cached module
    without looking at ``sys.path``.
    """
    if workspace:
        _unload_modules_under(workspace)
    if added_to_path and added_to_path in sys.path:
        sys.path.remove(added_to_path)


def _elementid_value(element_id):
    return int(_elementid_value_raw(element_id))


def _to_jsonable(value):
    if isinstance(value, _NET_INTEGER_TYPES):
        return int(value)
    if isinstance(value, _NET_FLOAT_TYPES):
        return float(value)
    if isinstance(value, DB.ElementId):
        return _elementid_value(value)
    if isinstance(value, DB.Element):
        return _describe_element(value)
    if isinstance(value, DB.XYZ):
        return [value.X, value.Y, value.Z]
    if isinstance(value, (set, frozenset)):
        return list(value)
    if hasattr(value, "Keys") and hasattr(value, "Values"):
        return dict((_safe_text(key), value[key]) for key in value.Keys)
    if hasattr(value, "__iter__"):
        return list(value)
    return _safe_text(value)


def _describe_element(element):
    category = element.Category
    try:
        name = element.Name
    except Exception:
        name = None
    return {
        "id": _elementid_value(element.Id),
        "category": category.Name if category else None,
        "name": name,
        "class": type(element).__name__,
    }


_GENERIC_ERROR_TYPES = ("Exception", "SystemError", "EnvironmentError", "OSError")
_MAX_INNER_EXCEPTIONS = 4


def _describe_error(ex):
    """Return (type, message) for a script error, surfacing the .NET exception.

    Revit API failures often reach Python as a generic "A managed exception
    was thrown..." whose real cause sits on the underlying .NET exception and
    its InnerException chain. The agent can only fix what it can read.
    """
    error_type = type(ex).__name__
    message = _safe_text(ex)
    clr_exception = _clr_exception(ex)
    if clr_exception is None:
        return error_type, message

    chain = []
    current = clr_exception
    while current is not None and len(chain) < _MAX_INNER_EXCEPTIONS:
        chain.append(
            "%s: %s" % (current.GetType().FullName, _safe_text(current.Message))
        )
        current = current.InnerException

    if error_type in _GENERIC_ERROR_TYPES:
        error_type = clr_exception.GetType().Name
    details = " <- ".join(chain)
    if details and details not in message:
        message = "%s [.NET: %s]" % (message, details)
    return error_type, message


def _clr_exception(ex):
    clr_exception = getattr(ex, "clsException", None)
    if clr_exception is not None:
        return clr_exception
    if hasattr(ex, "GetType") and hasattr(ex, "InnerException"):
        return ex
    try:
        import clr

        return clr.GetClrException(ex)
    except Exception:
        return None


def _format_script_traceback():
    """Format the exception being handled without this module's frames.

    The runner's frames (``run`` itself, the loop guards, the tracer) say
    nothing about the script, and a timeout raised inside one of them, such
    as one CPython injects as ``__agent_tick__`` is entered, would otherwise
    point at the runner instead of the script line that was running.
    """
    exc_type, exc_value, exc_tb = sys.exc_info()
    summary_type = getattr(traceback, "TracebackException", None)
    if summary_type is not None:
        summary = summary_type(exc_type, exc_value, exc_tb)
        _drop_runner_frames(summary, set())
        return "".join(summary.format())
    entries = [
        entry for entry in traceback.extract_tb(exc_tb) if entry[0] != _RUNNER_FILENAME
    ]
    lines = traceback.format_exception_only(exc_type, exc_value)
    if entries:
        lines = (
            ["Traceback (most recent call last):\n"]
            + traceback.format_list(entries)
            + lines
        )
    return "".join(lines)


def _drop_runner_frames(summary, seen):
    if summary is None or id(summary) in seen:
        return
    seen.add(id(summary))
    summary.stack = traceback.StackSummary.from_list(
        [frame for frame in summary.stack if frame.filename != _RUNNER_FILENAME]
    )
    _drop_runner_frames(summary.__cause__, seen)
    _drop_runner_frames(summary.__context__, seen)
    for nested in getattr(summary, "exceptions", None) or ():
        _drop_runner_frames(nested, seen)


_RUNNER_FILENAME = _format_script_traceback.__code__.co_filename


def _safe_text(value):
    try:
        return str(value)
    except Exception:
        return repr(value)
