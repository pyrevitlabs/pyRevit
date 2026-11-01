"""Stable metadata markers for Python automation APIs.

This module deliberately has no pyRevit, Revit, CLR or rpw dependency. It can
therefore mark APIs in either pyrevitlib or rpw without changing their import
lifecycle.
"""

import math
import re

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)

try:
    integer_types = (int, long)
except NameError:
    integer_types = (int,)


_MODES = ("pure", "query", "modify", "navigation", "interactive", "infrastructure")
_CONTEXTS = ("none", "document", "ui", "application")
_TRANSACTIONS = ("none", "caller", "owner")

#: Input types an operation can declare in ``inputs``. ``element`` is an
#: element id number that the agent runtime resolves to the element in the
#: active document; ``scalar`` is a string, number or boolean.
INPUT_TYPES = ("string", "number", "integer", "boolean", "element", "scalar")

#: Longest string input an operation accepts.
MAX_TEXT_LENGTH = 256

_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1

# One flat string per input keeps the marker readable by the CLI library
# index, which scans the source text instead of importing it.
_INPUT_SPEC = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([a-z]+)\s*(\?)?\s*$")


class InputError(ValueError):
    """Raised when operation inputs do not match their declaration."""


def _required_text(value, name):
    if not isinstance(value, string_types) or not value.strip():
        raise ValueError("{} must be a non-empty string.".format(name))
    return value


def _string_tuple(values, name):
    if not isinstance(values, tuple) or not all(
        isinstance(value, string_types) and value for value in values
    ):
        raise ValueError("{} must be a tuple of non-empty strings.".format(name))
    return values


def parse_inputs(specs):
    """Parse an ``inputs`` declaration into input descriptions.

    Each entry is one string, ``"<name>: <type>"``, with a trailing ``?`` for
    an optional input: ``("element: element", "title_on_sheet: boolean?")``.
    The name is the keyword argument the operation receives.

    Args:
        specs (tuple[str]): the declaration as written in the marker

    Returns:
        (list[dict]): ``{"name", "type", "required"}`` per input, in order

    Raises:
        ValueError: when an entry is malformed, its type is unknown or a
            name is declared twice
    """
    _string_tuple(specs, "inputs")
    parsed = []
    names = set()
    for spec in specs:
        match = _INPUT_SPEC.match(spec)
        if not match:
            raise ValueError(
                "inputs entry {!r} must look like 'name: type' or 'name: type?'.".format(
                    spec
                )
            )
        name, input_type, optional = match.groups()
        if input_type not in INPUT_TYPES:
            raise ValueError(
                "inputs entry {!r} has an unknown type; use one of {}.".format(
                    spec, ", ".join(INPUT_TYPES)
                )
            )
        if name in names:
            raise ValueError("input {!r} is declared twice.".format(name))
        names.add(name)
        parsed.append({"name": name, "type": input_type, "required": not optional})
    return parsed


def _is_integer(value):
    return isinstance(value, integer_types) and not isinstance(value, bool)


def _is_number(value):
    if _is_integer(value):
        return True
    return isinstance(value, float) and not math.isinf(value) and not math.isnan(value)


def _check_text(name, value):
    if not isinstance(value, string_types):
        raise InputError("'inputs.{}' must be a string.".format(name))
    if not value.strip() or len(value) > MAX_TEXT_LENGTH:
        raise InputError(
            "'inputs.{}' must be non-empty and contain at most {} characters.".format(
                name, MAX_TEXT_LENGTH
            )
        )


def _check_value(name, input_type, value):
    if input_type == "string":
        _check_text(name, value)
    elif input_type == "boolean":
        if not isinstance(value, bool):
            raise InputError("'inputs.{}' must be true or false.".format(name))
    elif input_type in ("integer", "element"):
        if not _is_integer(value) or not _INT64_MIN <= value <= _INT64_MAX:
            what = "an element id" if input_type == "element" else "an integer"
            raise InputError("'inputs.{}' must be {}.".format(name, what))
    elif input_type == "number":
        if not _is_number(value):
            raise InputError("'inputs.{}' must be a finite number.".format(name))
    elif input_type == "scalar":
        if isinstance(value, string_types):
            _check_text(name, value)
        elif not isinstance(value, bool) and not _is_number(value):
            raise InputError(
                "'inputs.{}' must be a string, a finite number or a boolean.".format(
                    name
                )
            )
    else:
        raise InputError("'inputs.{}' has an unknown type.".format(name))


def validate_inputs(specs, inputs):
    """Check an input object against an ``inputs`` declaration.

    Args:
        specs (tuple[str]): the declaration as written in the marker
        inputs (dict): the JSON-decoded input object

    Returns:
        (dict): the inputs that were given, unchanged

    Raises:
        InputError: when an input is missing, unknown or of the wrong type
    """
    declared = parse_inputs(specs)
    if not isinstance(inputs, dict):
        raise InputError("'inputs' must be an object.")
    known = set(spec["name"] for spec in declared)
    unknown = sorted(name for name in inputs if name not in known)
    if unknown:
        accepted = ", ".join(sorted(known)) if known else "nothing"
        raise InputError(
            "'inputs' accepts only {} (got {}).".format(accepted, ", ".join(unknown))
        )
    for spec in declared:
        if spec["name"] not in inputs or inputs[spec["name"]] is None:
            if spec["required"]:
                raise InputError("'inputs.{}' is required.".format(spec["name"]))
            if spec["name"] in inputs:
                raise InputError(
                    "'inputs.{}' must be left out rather than null.".format(
                        spec["name"]
                    )
                )
            continue
        _check_value(spec["name"], spec["type"], inputs[spec["name"]])
    return inputs


def _metadata(automation_id, plain_english, mode, effects, context, transaction):
    _required_text(automation_id, "automation_id")
    _required_text(plain_english, "PlainEnglish")
    if mode not in _MODES:
        raise ValueError("mode must be one of {}.".format(", ".join(_MODES)))
    if context not in _CONTEXTS:
        raise ValueError("context must be one of {}.".format(", ".join(_CONTEXTS)))
    if transaction not in _TRANSACTIONS:
        raise ValueError(
            "transaction must be one of {}.".format(", ".join(_TRANSACTIONS))
        )
    return {
        "id": automation_id,
        "PlainEnglish": plain_english,
        "mode": mode,
        "effects": _string_tuple(effects, "effects"),
        "context": context,
        "transaction": transaction,
    }


def operation(
    automation_id,
    PlainEnglish,
    mode="query",
    effects=(),
    context="document",
    transaction="none",
    inputs=None,
):
    """Mark a function or accessor as a stable automation contract.

    The marker only attaches metadata. The agent runtime decides whether a
    marked API is listed or invoked and continues to enforce its own policy,
    approval and transaction guards.

    Declaring ``inputs`` lets the agent's ``run_automation`` tool call a
    module-level ``query`` or ``pure`` operation that opens no transaction,
    passing each input as the keyword argument of the same name; see
    :func:`parse_inputs` for the syntax. ``inputs=()`` declares an operation
    that takes no inputs. Without ``inputs`` the operation is only listed.
    """
    metadata = _metadata(
        automation_id, PlainEnglish, mode, effects, context, transaction
    )
    if inputs is not None:
        parse_inputs(inputs)
        metadata["inputs"] = inputs

    def decorate(target):
        target.__pyrevit_automation__ = metadata.copy()
        return target

    return decorate


def type(automation_id, PlainEnglish):
    """Mark a class as a stable automation type description."""
    metadata = _metadata(
        automation_id, PlainEnglish, "infrastructure", (), "none", "none"
    )
    metadata["kind"] = "type"

    def decorate(target):
        target.__pyrevit_automation__ = metadata.copy()
        return target

    return decorate
