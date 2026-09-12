# encoding: utf-8
"""Shared record writer for the pyRevit development hooks.

Every hook script in this extension logs through here, so instrumentation added
to :func:`log_hook` applies to all of them at once.
"""

import re
import os
import os.path as op
import datetime

HOOK_LOGS = op.join(
    os.environ.get("APPDATA", op.expandvars("%userprofile%")), "pyRevit", "hooks.log"
)


from pyrevit import EXEC_PARAMS, revit


def _typename(obj):
    return type(obj).__name__ if obj is not None else "None"


def _handle_typename():
    try:
        return _typename(__revit__)  # pylint: disable=undefined-variable
    except NameError:
        return "undefined"


def _timestamp():
    return datetime.datetime.now().strftime("%m%j%H%M%S%f")


def _write_record(record_str):
    try:
        try:
            os.makedirs(op.dirname(HOOK_LOGS))
        except OSError:
            pass  # directory already exists - not an error
        with open(HOOK_LOGS, "a") as f:
            f.write(record_str + "\n")
    except (IOError, OSError):
        pass  # silently swallow write failures (e.g. permission denied)


def _get_hook_parts(hook_script):
    # finds the two parts of the hook script name
    # e.g command-before-exec[ID_INPLACE_COMPONENT].py
    # ('command-before-exec', 'ID_INPLACE_COMPONENT')
    parts = re.findall(r"([a-z -]+)\[?([A-Z _]+)?\]?\..+", op.basename(hook_script))
    if parts:
        return parts[0]
    else:
        return "", ""


def log_hook(hook_file, data, log_doc_access=False):
    """Append one record for this hook execution to the hooks log.

    Every record carries two fields that assert pyRevit's host-handle contract:
    ``handle`` is the type of the ``__revit__`` builtin, which must read
    ``UIApplication`` in every hook context, and ``sender`` is the type of the
    raw event sender, which is expected to vary by event and proves the sender
    was preserved rather than overwritten by normalization.

    Args:
        hook_file (str): ``__file__`` of the calling hook script.
        data (dict): Event-specific fields to record.
        log_doc_access (bool): Resolve ``revit.doc`` and count its elements.
            A non-zero count is the end-to-end signal that the handle reached
            the document; before the handle was normalized this read 0 in every
            ``Application_*`` hook.

    Side effects:
        Appends a line to the hooks log named by ``HOOK_LOGS``. Write failures
        are swallowed so a hook never fails on logging alone.
    """
    hook_name, hook_target = _get_hook_parts(hook_file)
    # collect document element count as doc access test if requested
    doc = revit.doc if log_doc_access else None
    count = len(revit.query.get_all_elements(doc=doc)) if doc else 0

    # write log record with data
    record_str = "{} [{}] ".format(_timestamp(), hook_name)
    for k, v in data.items():
        record_str += '{}: "{}" '.format(k, v)
    record_str += 'handle: "{}" '.format(_handle_typename())
    record_str += 'sender: "{}" '.format(_typename(EXEC_PARAMS.event_sender))
    record_str += "count: {}".format(str(count))
    _write_record(record_str)
