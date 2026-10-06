"""Test standard input in pyRevit console window."""
# pylint: disable-all

import pdb
import sys

if sys.version_info[0] >= 3:
    stdin_encoding = sys.stdin.encoding.lower().replace("_", "-")
    assert stdin_encoding in ("utf-8", "utf8"), (
        "Unexpected sys.stdin encoding: {}".format(sys.stdin.encoding)
    )

print("Enter 'c' at the debugger prompt to complete the test.")


class PyRevitPdb(pdb.Pdb):
    """Keep active trace callbacks callable on IronPython 3.4.2."""

    def trace_dispatch(
        self, frame, event, argument, base_trace_dispatch=pdb.Pdb.trace_dispatch
    ):
        """Return a trace callback for every frame entered during the test."""
        trace_callback = base_trace_dispatch(self, frame, event, argument)
        return trace_callback or self.trace_dispatch

    def set_continue(self):
        """Continue without clearing frame trace callbacks."""
        self._set_stopinfo(self.botframe, None, -1)


debugger = PyRevitPdb()
debugger.set_trace()


def debug_test(value):
    """Print a value while pdb traces this function."""
    i = 12
    print(value)
    print(i)


for idx in range(2):
    debug_test(idx)


def _make_noop_trace():
    def trace_callback(frame, event, argument):
        return trace_callback

    return trace_callback


sys._getframe().f_trace = _make_noop_trace()
sys.settrace(None)
print("IronPython debugger input test passed.")
