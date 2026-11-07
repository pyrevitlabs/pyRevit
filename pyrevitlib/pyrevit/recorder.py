"""Extension trace API for the pyRevit session recorder.

The recorder is an explicit record/stop mode (``pyrevit agent record start`` and
``stop``). While it is not recording, every function here does nothing, so
extensions can call :func:`mark` unconditionally.

Example:
    >>> from pyrevit import recorder
    >>> recorder.mark("my-extension", {"step": "placed sheets", "count": 12})

Note:
    The module must stay parseable by IronPython 2.7, IronPython 3.4 and CPython 3.
"""

import json

_UNAVAILABLE = object()
_recorder_type = None


def _resolve():
    global _recorder_type
    if _recorder_type is None:
        try:
            from PyRevitLabs.PyRevit.Runtime.Agent import AgentRecorder

            _recorder_type = AgentRecorder
        except Exception:
            _recorder_type = _UNAVAILABLE
    return None if _recorder_type is _UNAVAILABLE else _recorder_type


def _serialize(data):
    try:
        return json.dumps(data, default=str)
    except Exception:
        return json.dumps(repr(data))


def is_recording():
    """Whether a session recording is active.

    Returns:
        bool: True between ``record start`` and ``record stop``.
    """
    recorder_type = _resolve()
    return bool(recorder_type is not None and recorder_type.IsRecording)


def mark(source, data=None):
    """Emit a structured breadcrumb into the active session recording.

    Does nothing when no recording is active, and never raises: a tracing
    failure must not break the extension that emits it.

    Args:
        source (str): who emits the breadcrumb, such as the extension or tool name.
        data (object): JSON-serializable details; values that are not
            serializable are stored as their ``str``.
    """
    try:
        recorder_type = _resolve()
        if recorder_type is None or not recorder_type.IsRecording:
            return
        if not hasattr(source, "upper"):
            source = repr(source)
        recorder_type.Mark(source, _serialize(data))
    except Exception:
        return
