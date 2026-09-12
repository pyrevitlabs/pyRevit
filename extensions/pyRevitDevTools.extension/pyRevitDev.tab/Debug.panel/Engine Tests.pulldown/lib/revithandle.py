"""Checks pyRevit's host-handle contract from inside a running command.

The ``__revit__`` builtin is guaranteed to be an ``UI.UIApplication`` in every
execution context - commands, event hooks, smart buttons, combo boxes - or
``None`` outside a Revit host. Everything in the pyrevit library resolves the
host application through it, so a handle of any other type degrades
``HOST_APP`` silently rather than failing loudly.

Both engines run the same checks from here so IronPython and CPython cannot
drift apart.
"""

import sys

from pyrevit import EXEC_PARAMS, HOST_APP, UI, script


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


def _collect():
    results = []

    handle = _handle()
    _check(
        results,
        "__revit__ is UIApplication",
        isinstance(handle, UI.UIApplication),
        _typename(handle),
    )

    _check(
        results,
        "HOST_APP.uiapp",
        HOST_APP.uiapp is not None,
        _typename(HOST_APP.uiapp),
    )
    _check(
        results,
        "HOST_APP.app",
        HOST_APP.app is not None,
        _typename(HOST_APP.app),
    )

    try:
        uidoc = HOST_APP.uidoc
        _check(
            results,
            "HOST_APP.uidoc does not raise",
            True,
            _typename(uidoc),
        )
    except Exception as uidoc_err:
        _check(results, "HOST_APP.uidoc does not raise", False, str(uidoc_err))

    _info(results, "HOST_APP.doc (None if zero-doc)", _typename(HOST_APP.doc))
    _check(
        results,
        "HOST_APP.addin_id",
        HOST_APP.addin_id is not None,
        str(HOST_APP.addin_id),
    )
    _check(
        results,
        "HOST_APP.version",
        bool(HOST_APP.version),
        str(HOST_APP.version),
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


def report():
    """Print the handle contract report and return True when every check passed.

    Returns:
        bool: True if no check failed.
    """
    output = script.get_output()
    results = _collect()

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
