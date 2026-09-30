"""Checks pyRevit's host-handle contract from inside a running script.

The ``__revit__`` builtin is guaranteed to be an ``UI.UIApplication`` in every
execution context - commands, event hooks, smart buttons, combo boxes - or
``None`` outside a Revit host. Everything in the pyrevit library resolves the
host application through it, so a handle of any other type degrades
``HOST_APP`` silently rather than failing loudly.

Two injection sites have to honour that, and each button here covers one:

* the runtime engines, behind every command and event hook, and
* ``ScriptExecutor``, behind smart buttons and combo boxes.

Both engines run the same checks from this module so IronPython and CPython
cannot drift apart. The ``injection site is ...`` row verifies the entry point
really did run through the site it claims, so a path that silently stops being
covered is reported instead of quietly passing.
"""

import sys

from pyrevit import EXEC_PARAMS, HOST_APP, UI, script

RUNTIME_ENGINE_SITE = "ScriptRuntime"
EXECUTOR_SITE = "ScriptExecutor"


def _check(results, name, passed, detail):
    results.append((name, passed, detail))


def _info(results, name, detail):
    results.append((name, None, detail))


def _typename(obj):
    return type(obj).__name__ if obj is not None else "None"


def _handle():
    try:
        return __revit__  # pylint: disable=undefined-variable
    except NameError:
        return None


def _check_accessor(results, name, getter, predicate=None, detail=None):
    """Record one ``HOST_APP`` accessor read, turning a raise into a failure.

    Not every accessor in this contract is guarded. ``addin_id`` and
    ``version`` dereference ``HOST_APP.app`` directly, so they raise exactly
    when the handle is unusable - the one case this probe exists to name. Read
    the plain way, that raise would end the report in a traceback naming
    nothing, which is the silent degradation being fixed here all over again.

    Args:
        results: Report rows collected so far.
        name: Label for the check.
        getter: Callable reading the accessor.
        predicate: Callable deciding whether the read satisfies the contract.
            Defaults to "the value is not None".
        detail: Callable rendering the value into a report cell. Defaults to
            the value's type name.
    """
    if predicate is None:

        def predicate(value):
            return value is not None

    if detail is None:
        detail = _typename

    try:
        value = getter()
    except Exception as err:
        _check(results, name, False, "raised: {}".format(err))
        return None

    _check(results, name, predicate(value), detail(value))
    return value


def _collect(context, site):
    results = []

    handle = _handle()
    _check(
        results,
        "__revit__ is UIApplication",
        isinstance(handle, UI.UIApplication),
        _typename(handle),
    )

    # The engines inject __scriptruntime__; ScriptExecutor does not. A button
    # that expected one site and got the other is no longer covering it.
    actual_site = (
        RUNTIME_ENGINE_SITE if EXEC_PARAMS.script_runtime is not None else EXECUTOR_SITE
    )
    _check(
        results,
        "injection site is {}".format(site),
        actual_site == site,
        "{} ran {}".format(context, actual_site),
    )

    _check_accessor(results, "HOST_APP.uiapp", lambda: HOST_APP.uiapp)

    # Same object, not just same type: a resolver that re-wrapped the handle on
    # every read would still satisfy a type check while handing out a new
    # UIApplication each time.
    _check_accessor(
        results,
        "HOST_APP.uiapp is __revit__",
        lambda: HOST_APP.uiapp,
        predicate=lambda uiapp: uiapp is handle,
    )

    # Under the old polymorphic builtin, uiapp read None while app still
    # resolved, which is the exact split HOST_APP must never show again.
    _check_accessor(
        results,
        "HOST_APP.app follows uiapp",
        lambda: (HOST_APP.uiapp, HOST_APP.app),
        predicate=lambda pair: pair[1] is None or pair[0] is not None,
        detail=lambda pair: "{} -> {}".format(_typename(pair[0]), _typename(pair[1])),
    )

    _check_accessor(
        results,
        "HOST_APP.uidoc resolves",
        lambda: HOST_APP.uidoc,
        predicate=lambda uidoc: True,
    )
    _check_accessor(
        results,
        "HOST_APP.doc resolves (None if zero-doc)",
        lambda: HOST_APP.doc,
        predicate=lambda doc: True,
    )
    _check_accessor(results, "HOST_APP.addin_id", lambda: HOST_APP.addin_id)
    _check_accessor(
        results,
        "HOST_APP.version",
        lambda: HOST_APP.version,
        predicate=bool,
    )

    _check(
        results,
        "event_sender is None in a command",
        EXEC_PARAMS.event_sender is None,
        _typename(EXEC_PARAMS.event_sender),
    )

    try:
        from rpw import revit as rpw_revit

        _info(results, "rpw binds uiapp", _typename(rpw_revit.uiapp))
    except Exception as rpw_err:
        _info(results, "rpw binds uiapp", "unavailable: {}".format(rpw_err))

    return results


def report(context, site):
    """Print the handle contract report and return True when every check passed.

    Args:
        context: Label for the entry point running this probe.
        site: The injection site that entry point expects to run through, one
            of :data:`RUNTIME_ENGINE_SITE` or :data:`EXECUTOR_SITE`.

    Returns:
        bool: True if no check failed.
    """
    output = script.get_output()
    results = _collect(context, site)

    print("python: {}".format(sys.version.replace("\n", " ")))
    print(
        "loader: {} | cached: {}".format(
            EXEC_PARAMS.engine_ver, EXEC_PARAMS.cached_engine
        )
    )
    print("")

    for name, passed, detail in results:
        if passed is None:
            marker = "info"
        else:
            marker = "PASS" if passed else "FAIL"
        print("{}  {:<34} {}".format(marker, name, detail))

    failed = [name for name, passed, _ in results if passed is False]
    print("")
    if failed:
        output.print_md(
            "**{} check(s) FAILED:** {}".format(len(failed), ", ".join(failed))
        )
    else:
        checked = len([r for r in results if r[1] is not None])
        output.print_md("**All {} checks passed.**".format(checked))

    return not failed
