"""Run a marked automation operation for the agent's ``run_automation`` tool.

The CLI picks the operation from its library index and sends a fixed script
that calls :func:`invoke`; the module, function and id arrive as data in the
run's inputs, never as code. :func:`invoke` re-checks everything the CLI
checked against the live marker, so a stale index or a hand-built request
cannot call anything that is not a marked, invocable operation.

The run itself is a ``query`` run, so the host still rolls back any model
change and blocks saves and exports.
"""

import importlib
import inspect
import io
import os.path as op
import re

import pyrevit_automation as automation


ALLOWED_PACKAGES = ("pyrevit.", "rpw.")
"""Packages an operation can be imported from."""

INVOCABLE_MODES = ("query", "pure")
"""Modes ``run_automation`` may call; every other mode needs run_modify."""

MAX_ITEMS = 200
"""Items returned from a list result; ``total`` and ``truncated`` say the rest."""

_MODULE_NAME = re.compile(r"^(?:pyrevit|rpw)(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")


class OperationError(Exception):
    """Raised when an operation cannot be run through ``run_automation``."""


def _parameter_names(function):
    """Parameter names, from the code object where inspect.signature is missing (IronPython 2.7)."""
    try:
        return list(inspect.signature(function).parameters)
    except (AttributeError, TypeError, ValueError):
        code = getattr(function, "__code__", None) or function.func_code
        return list(code.co_varnames[: code.co_argcount])


def _module_source(module_name):
    """Source text of a pyrevitlib or rpw module, read without importing it.

    Returns None when the module has no source file in its package folder.
    """
    package_name, _, submodule = module_name.partition(".")
    package = importlib.import_module(package_name)
    base = op.join(op.dirname(package.__file__), *submodule.split("."))
    for path in (base + ".py", op.join(base, "__init__.py")):
        if op.isfile(path):
            with io.open(path, encoding="utf-8") as source:
                return source.read()
    return None


def _marked_function(operation):
    """Import the operation's module and return its marked function and marker.

    Important:
        The module's source must name the operation id before it is imported,
        so a request naming any other pyrevitlib or rpw module never runs that
        module's import side effects.
    """
    module_name = operation.get("module") or ""
    function_name = operation.get("function") or ""
    automation_id = operation.get("id") or ""
    if not module_name.startswith(ALLOWED_PACKAGES) or not _MODULE_NAME.match(
        module_name
    ):
        raise OperationError("'{}' is not in pyrevitlib or rpw.".format(module_name))
    source = (_module_source(module_name) or "").lower()
    if not automation_id or (
        '"{}"'.format(automation_id.lower()) not in source
        and "'{}'".format(automation_id.lower()) not in source
    ):
        raise OperationError(
            "{} does not mark an operation '{}'.".format(module_name, automation_id)
        )
    module = importlib.import_module(module_name)
    function = getattr(module, function_name, None)
    marker = getattr(function, "__pyrevit_automation__", None)
    if not callable(function) or not isinstance(marker, dict):
        raise OperationError(
            "{}.{} is not a marked automation operation.".format(
                module_name, function_name
            )
        )
    if (marker.get("id") or "").lower() != automation_id.lower():
        raise OperationError(
            "{}.{} is marked as '{}', not '{}'.".format(
                module_name, function_name, marker.get("id"), automation_id
            )
        )
    if (
        marker.get("kind") == "type"
        or marker.get("mode") not in INVOCABLE_MODES
        or marker.get("transaction") != "none"
        or "inputs" not in marker
    ):
        raise OperationError(
            "'{}' cannot run through run_automation. Call it from a "
            "run_query or run_modify script instead.".format(marker.get("id"))
        )
    return function, marker


def _element(doc, element_id, name):
    from pyrevit.compat import get_elementid_from_value_func

    if doc is None:
        raise OperationError(
            "'inputs.{}' names an element, which needs an active document.".format(name)
        )
    try:
        element_id_value = get_elementid_from_value_func()(element_id)
    except (TypeError, ValueError, OverflowError):
        raise automation.InputError(
            "'inputs.{}': {} is not a valid element id in this Revit version.".format(
                name, element_id
            )
        )
    element = doc.GetElement(element_id_value)
    if element is None:
        raise automation.InputError(
            "'inputs.{}': no element with id {} in the active document.".format(
                name, element_id
            )
        )
    return element


def _is_sequence(value):
    """Whether a result is a collection to bound.

    Covers Python collections, .NET lists such as
    ``FilteredElementCollector.ToElements()``, and Python iterators such as
    generators and ``map()`` or ``filter()`` results; dictionaries and .NET
    dictionaries are returned whole.
    """
    if isinstance(value, (list, tuple, set, frozenset)):
        return True
    if not hasattr(value, "__iter__") or hasattr(value, "Keys"):
        return False
    return (
        hasattr(value, "Count") or hasattr(value, "__next__") or hasattr(value, "next")
    )


def _bounded(value):
    if _is_sequence(value):
        items = list(value)
        return {
            "value": items[:MAX_ITEMS],
            "total": len(items),
            "truncated": len(items) > MAX_ITEMS,
        }
    return {"value": value}


def invoke(operation, inputs, doc):
    """Validate the inputs and call one marked operation.

    Args:
        operation (dict): ``{"id", "module", "function"}`` chosen by the CLI
        inputs (dict): the caller's input object
        doc (DB.Document): the active document, or None

    Returns:
        (dict): ``{"value": ...}``; a list result keeps its first
        :data:`MAX_ITEMS` items and adds ``total`` and ``truncated``

    Raises:
        OperationError: when the operation is not invocable
        pyrevit_automation.InputError: when the inputs do not match
    """
    function, marker = _marked_function(operation)
    automation.validate_inputs(marker["inputs"], inputs)

    needs_document = marker.get("context") == "document"
    if needs_document and doc is None:
        raise OperationError("'{}' requires an active document.".format(marker["id"]))

    arguments = {}
    for spec in automation.parse_inputs(marker["inputs"]):
        if spec["name"] not in inputs:
            continue
        value = inputs[spec["name"]]
        if spec["type"] == "element":
            value = _element(doc, value, spec["name"])
        arguments[spec["name"]] = value
    if needs_document and "doc" in _parameter_names(function):
        arguments["doc"] = doc

    return _bounded(function(**arguments))
