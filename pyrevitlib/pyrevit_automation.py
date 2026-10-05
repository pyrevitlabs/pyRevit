"""Stable metadata markers for Python automation APIs.

This module deliberately has no pyRevit, Revit, CLR or rpw dependency. It can
therefore mark APIs in either pyrevitlib or rpw without changing their import
lifecycle.
"""

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


_MODES = ("pure", "query", "modify", "navigation", "interactive", "infrastructure")
_CONTEXTS = ("none", "document", "ui", "application")
_TRANSACTIONS = ("none", "caller", "owner")


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
):
    """Mark a function or accessor as a stable automation contract.

    The marker only attaches metadata. The agent runtime decides whether a
    marked API is listed or invoked and continues to enforce its own policy,
    approval and transaction guards.
    """
    metadata = _metadata(
        automation_id, PlainEnglish, mode, effects, context, transaction
    )

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
