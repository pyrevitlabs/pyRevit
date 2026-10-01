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
import linecache
import os.path as op
import sys
import threading
import time
import traceback

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import System

from pyrevit.api import DB, UI
from pyrevit.compat import get_elementid_value_func

SOURCE_NAME = "<agent-script>"

_DEADLINE_CHECK_INTERVAL = 100
_WATCHDOG_RETRY_SECONDS = 0.2

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
    swallow it. Python drops a trace function after its first raise on every
    engine, so a handler that caught it would end the deadline checks. The
    runner therefore narrows every bare ``except`` and ``except
    BaseException`` in the script to ``except Exception`` before compiling,
    and also records that the deadline passed so :func:`run` fails the run
    even if the script then ends normally.
    """


class _NarrowBroadHandlers(ast.NodeTransformer):
    """Turn handlers that would catch ``RunTimedOut`` into ``except Exception``.

    A script that catches the timeout inside a loop can't be stopped again,
    because Python removes the trace function once it has raised.
    """

    def __init__(self):
        ast.NodeTransformer.__init__(self)
        self.narrowed = 0

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        if _catches_base_exception(node.type):
            node.type = ast.Name(id="Exception", ctx=ast.Load())
            self.narrowed += 1
        return node


def _catches_base_exception(handler_type):
    if handler_type is None:
        return True
    if isinstance(handler_type, ast.Name):
        return handler_type.id == "BaseException"
    if isinstance(handler_type, ast.Tuple):
        return any(_catches_base_exception(item) for item in handler_type.elts)
    return False


def _compile_source(source):
    """Compile the agent source with broad exception handlers narrowed.

    Returns:
        tuple: the code object, and None or a description of why the rewrite
        was skipped. Falls back to compiling the source unchanged when the
        rewrite fails, so a syntax error keeps its original message and line
        number; the caller must report the skipped rewrite, because a script
        compiled that way can swallow its own timeout.

    Note:
        IronPython reports every line as line 1 for code compiled from an AST,
        so the source text is compiled whenever no handler needed narrowing.
    """
    try:
        narrower = _NarrowBroadHandlers()
        tree = narrower.visit(ast.parse(source, SOURCE_NAME, "exec"))
        if not narrower.narrowed:
            return compile(source, SOURCE_NAME, "exec"), None
        ast.fix_missing_locations(tree)
        return compile(tree, SOURCE_NAME, "exec"), None
    except Exception as ex:
        return compile(source, SOURCE_NAME, "exec"), "{}: {}".format(
            type(ex).__name__, _safe_text(ex)
        )


def _deadline_tracer(timeout_s, state):
    deadline = time.time() + timeout_s
    events = [0]

    def trace(frame, event, arg):
        events[0] += 1
        if events[0] % _DEADLINE_CHECK_INTERVAL == 0 and time.time() > deadline:
            state["timed_out"] = True
            raise RunTimedOut(timeout_s)
        return trace

    return trace


def _start_watchdog(timeout_s, state):
    """Keep raising ``RunTimedOut`` in the script thread on CPython.

    CPython removes the trace function as soon as it raises, so a script that
    catches the first ``RunTimedOut`` inside a loop would never be checked
    again. Returns a function that stops the watchdog, waits for it to exit and
    clears any injection still pending, or None on engines where the tracer
    keeps working.
    """
    if _implementation() != "cpython":
        return None
    try:
        import ctypes

        set_async_exc = ctypes.pythonapi.PyThreadState_SetAsyncExc
    except (ImportError, AttributeError):
        return None

    thread_id = ctypes.c_ulong(threading.current_thread().ident)
    stopped = threading.Event()

    def watch():
        if stopped.wait(timeout_s):
            return
        while not stopped.is_set():
            state["timed_out"] = True
            set_async_exc(thread_id, ctypes.py_object(RunTimedOut))
            stopped.wait(_WATCHDOG_RETRY_SECONDS)

    thread = threading.Thread(target=watch)
    thread.daemon = True
    thread.start()

    def stop():
        while True:
            try:
                stopped.set()
                thread.join()
                set_async_exc(thread_id, None)
                return
            except RunTimedOut:
                pass

    return stop


def run(context):
    """Execute ``context.Source`` and report the outcome on ``context``.

    Args:
        context (AgentScriptContext): run request and outcome sink from the host.

    Note:
        Never raises. Script errors, including a failure to serialize
        ``result``, are reported through ``context.SetError`` so the host can
        roll the run back.

    Note:
        ``context.TimeoutSeconds`` is enforced with ``sys.settrace``, so it
        stops Python code, including loops, but not a single blocking call
        such as a long Revit API call or ``time.sleep``; the run fails with
        ``timeout`` once that call returns.

    Warning:
        Raising from the trace function ends tracing, so the script's own
        handlers must not catch ``RunTimedOut``. The source is compiled with
        every bare ``except`` and ``except BaseException`` narrowed to
        ``except Exception``; a script can no longer catch ``KeyboardInterrupt``
        or ``SystemExit`` that way. Suppression through an alias or
        ``contextlib.suppress(BaseException)`` still bypasses this, and on
        CPython the watchdog thread is the backstop.
    """
    context.SetEngine(_implementation(), sys.version.split()[0], sys.version)
    source = context.Source
    linecache.cache[SOURCE_NAME] = (
        len(source),
        None,
        source.splitlines(True),
        SOURCE_NAME,
    )
    captured = StringIO()
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    sys.stdout = captured
    sys.stderr = captured
    failed = False
    workspace = None
    try:
        workspace = _enter_workspace(context.Workspace)
        namespace = _build_namespace(context)
        code, rewrite_problem = _compile_source(source)
        if rewrite_problem:
            print(
                "[pyRevit agent] Could not narrow the script's bare except "
                "handlers ({}); a handler that catches everything can swallow "
                "the timeout.".format(rewrite_problem)
            )
        timeout_s = getattr(context, "TimeoutSeconds", None)
        state = {"timed_out": False}
        started = time.time()
        stop_watchdog = None
        if timeout_s:
            sys.settrace(_deadline_tracer(timeout_s, state))
            stop_watchdog = _start_watchdog(timeout_s, state)
        try:
            exec(code, namespace)
        finally:
            if stop_watchdog:
                stop_watchdog()
            if timeout_s:
                sys.settrace(None)
        if state["timed_out"] or (timeout_s and time.time() - started > timeout_s):
            raise RunTimedOut(timeout_s)
    except SystemExit:
        pass
    except RunTimedOut:
        failed = True
        context.SetError(
            "timeout",
            "The script ran longer than its {:g} second limit and was stopped; its "
            "changes were rolled back. Pass a larger timeout_s if the work needs "
            "more time.".format(timeout_s),
            _format_script_traceback(),
        )
    except Exception as ex:
        failed = True
        error_type, message = _describe_error(ex)
        context.SetError(error_type, message, _format_script_traceback())
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        _leave_workspace(workspace)
        context.SetOutput(captured.getvalue())

    if failed or "result" not in namespace:
        return

    try:
        context.SetResult(json.dumps(namespace["result"], default=_to_jsonable))
    except Exception as ex:
        context.SetError(
            "ResultSerializationError", _safe_text(ex), _format_script_traceback()
        )


def _implementation():
    implementation = getattr(sys, "implementation", None)
    if implementation is not None:
        return implementation.name
    return "ironpython" if "IronPython" in sys.version else "cpython"


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
    root = op.normcase(op.abspath(workspace)).rstrip("/\\") + op.sep
    for name, module in list(sys.modules.items()):
        if _is_under(getattr(module, "__file__", None), root):
            del sys.modules[name]
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


def _leave_workspace(workspace):
    if workspace and workspace in sys.path:
        sys.path.remove(workspace)


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
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_tb is not None:
        exc_tb = exc_tb.tb_next
    return "".join(traceback.format_exception(exc_type, exc_value, exc_tb))


def _safe_text(value):
    try:
        return str(value)
    except Exception:
        return repr(value)
