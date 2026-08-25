# -*- coding: utf-8 -*-
"""Lightweight Python-side perf instrumentation.

Emits [PERF:py] checkpoints through the standard pyRevit logger at DEBUG
level so Python startup-script timings interleave with the C# loader's
[PERF] timeline in the regular runtime log / output window.

Self-contained on purpose: imports only stdlib at module load so it can be
the first line of pyrevit/__init__.py without triggering circular loads. The
pyRevit logger is resolved lazily on first use; checkpoints that fire before
the logger is importable (early bootstrap) are silently skipped.
"""
import time

# perf_counter exists on IronPython 2.7.6+ and CPython 3.3+; fall back to
# time.time() so a stripped-down engine still gets coarse-grained data.
_now = getattr(time, "perf_counter", None) or time.time

# Tracks the wall-clock time of the previous mark() call so we can emit a
# delta-since-last-mark. Updated even when a checkpoint isn't logged, so the
# timeline stays continuous across early bootstrap marks.
_LAST = [_now()]

# Resolved pyRevit logger, cached once available. Holds None until the logger
# module can be imported; each call retries until resolution succeeds.
_LOGGER = [None]


def _logger():
    if _LOGGER[0] is not None:
        return _LOGGER[0]
    try:
        from pyrevit.coreutils.logger import get_logger
        _LOGGER[0] = get_logger("pyrevit.perf")
    except Exception:
        return None
    return _LOGGER[0]


def mark(label):
    """Record a perf checkpoint.

    Emits one DEBUG `[PERF:py]` line with elapsed time since the previous
    mark. Format mirrors the C# `[PERF]` lines for visual parity. No-op until
    the pyRevit logger is importable.
    """
    now = _now()
    delta_ms = (now - _LAST[0]) * 1000.0
    _LAST[0] = now
    lg = _logger()
    if lg is None:
        return
    try:
        lg.debug("[PERF:py] %s: %.0fms", label, delta_ms)
    except Exception:
        pass


class time_block(object):
    """Context manager: time a block independently of the running timeline.

    Emits one DEBUG `[PERF:py]` line at exit, indented two extra spaces past
    `mark()` lines to mirror C# sub-item indentation (`[PERF]   <name>:`).
    """

    def __init__(self, label):
        self.label = label
        self._t0 = None

    def __enter__(self):
        self._t0 = _now()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._t0 is None:
            return False
        elapsed_ms = (_now() - self._t0) * 1000.0
        lg = _logger()
        if lg is None:
            return False
        try:
            lg.debug("[PERF:py]   %s: %.0fms", self.label, elapsed_ms)
        except Exception:
            pass
        return False
