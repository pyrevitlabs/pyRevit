# -*- coding: utf-8 -*-
"""Python-side perf checkpoints recorded on the C# session load timeline.

Checkpoints are recorded on `pyRevitLabs.Common.LoadTimeline`, the clock the C#
loader times the whole session load with, and logged as DEBUG `[PERF:py]` lines
that interleave with its `[PERF]` lines. Outside a session load there is no
active timeline and every call does nothing, so checkpoints left in library
modules cost nothing when commands import them.

Self-contained on purpose: imports only sys at module load so it can be the first
line of pyrevit/__init__.py without triggering circular loads. The timeline type
is resolved on first use. The pyRevit logger is never imported from here, since
importing it before pyrevit/__init__.py finishes fails and costs time inside the
very checkpoints being measured; it is used once another import has loaded it.
Lines recorded before then are held and logged, in order, ahead of the first
line after it.
"""

import sys

_UNRESOLVED = object()

_TIMELINE_TYPE = [_UNRESOLVED]

_LOGGER = [None]

_PENDING_LINES = []


def _timeline_type():
    if _TIMELINE_TYPE[0] is _UNRESOLVED:
        try:
            import clr  # pylint: disable=E0401

            clr.AddReference("pyRevitLabs.Common")
            from pyRevitLabs.Common import LoadTimeline  # pylint: disable=E0401

            _TIMELINE_TYPE[0] = LoadTimeline
        except Exception:
            _TIMELINE_TYPE[0] = None
    return _TIMELINE_TYPE[0]


def _active_timeline():
    timeline_type = _timeline_type()
    if timeline_type is None:
        return None
    return timeline_type.Active


def _logger():
    if _LOGGER[0] is not None:
        return _LOGGER[0]
    logger_module = sys.modules.get("pyrevit.coreutils.logger")
    get_logger = getattr(logger_module, "get_logger", None)
    if get_logger is None:
        return None
    try:
        _LOGGER[0] = get_logger("pyrevit.perf")
    except Exception:
        return None
    return _LOGGER[0]


def _log_debug(message, *args):
    lg = _logger()
    if lg is None:
        _PENDING_LINES.append((message, args))
        return
    lines = _PENDING_LINES[:] + [(message, args)]
    del _PENDING_LINES[:]
    for line_message, line_args in lines:
        try:
            lg.debug(line_message, *line_args)
        except Exception:
            pass


def elapsed_load_seconds():
    """Seconds since the current session load started, or None outside a load."""
    timeline = _active_timeline()
    if timeline is None:
        return None
    return timeline.ElapsedMilliseconds / 1000.0


def mark(label):
    """Record a perf checkpoint.

    Logs one DEBUG `[PERF:py]` line with the time since the previous checkpoint
    in the innermost open timeline span, or since that span started. Deltas
    therefore never reach back into another script or loader step.

    Note:
        Checkpoints taken before the pyRevit logger has been loaded are held
        and logged, in order, once it has, so their log timestamps run late
        but their deltas are exact.
    """
    timeline = _active_timeline()
    if timeline is None:
        return
    span = timeline.CurrentSpan
    if span is None:
        return
    _log_debug("[PERF:py] %s: %.0fms", label, span.Lap())


class time_block(object):
    """Context manager: time a block as a child span of the innermost open span.

    Logs one DEBUG `[PERF:py]` line at exit, indented two extra spaces past
    `mark()` lines to mirror C# sub-item indentation (`[PERF]   <name>:`).
    Does nothing outside a session load.
    """

    def __init__(self, label):
        self.label = label
        self._span = None

    def __enter__(self):
        timeline = _active_timeline()
        if timeline is not None:
            self._span = timeline.StartSpan(self.label)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._span is None:
            return False
        _log_debug("[PERF:py]   %s: %.0fms", self.label, self._span.End())
        return False
