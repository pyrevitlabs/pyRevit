"""In-engine runner for agent-submitted source.

The agent host writes an entry script that calls :func:`run` with the
``AgentScriptContext`` it built. The runner executes the agent source in a
fresh namespace, captures everything printed, serializes ``result`` to JSON,
and reports all of it back through the context.

Invariant:
    This module must stay parseable by IronPython 2.7, IronPython 3.4 and
    CPython 3, because the host picks the engine per request.
"""

import json
import linecache
import sys
import traceback

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import System

from pyrevit.api import DB, UI
from pyrevit.compat import get_elementid_value_func

SOURCE_NAME = "<agent-script>"

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


def run(context):
    """Execute ``context.Source`` and report the outcome on ``context``.

    Args:
        context (AgentScriptContext): run request and outcome sink from the host.

    Note:
        Never raises. Script errors, including a failure to serialize
        ``result``, are reported through ``context.SetError`` so the host can
        roll the run back.
    """
    source = context.Source
    linecache.cache[SOURCE_NAME] = (
        len(source),
        None,
        source.splitlines(True),
        SOURCE_NAME,
    )
    namespace = _build_namespace(context)
    captured = StringIO()
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    sys.stdout = captured
    sys.stderr = captured
    failed = False
    try:
        code = compile(source, SOURCE_NAME, "exec")
        exec(code, namespace)
    except SystemExit:
        pass
    except Exception as ex:
        failed = True
        context.SetError(type(ex).__name__, _safe_text(ex), _format_script_traceback())
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        context.SetOutput(captured.getvalue())

    if failed or "result" not in namespace:
        return

    try:
        context.SetResult(json.dumps(namespace["result"], default=_to_jsonable))
    except Exception as ex:
        context.SetError(
            "ResultSerializationError", _safe_text(ex), _format_script_traceback()
        )


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
