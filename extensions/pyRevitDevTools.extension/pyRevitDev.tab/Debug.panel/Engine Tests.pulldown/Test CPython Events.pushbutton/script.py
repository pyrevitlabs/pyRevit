#! python3
"""Test CPython event handler subscribe/unsubscribe."""
# pylint: skip-file
from pyrevit import HOST_APP
from pyrevit import UI, DB


def docchanged_eventhandler(sender, args):
    print("DocumentChanged fired: {}".format(args.GetTransactionNames()))


HOST_APP.app.DocumentChanged += docchanged_eventhandler
print("DocumentChanged event handler registered")

try:
    HOST_APP.app.DocumentChanged -= docchanged_eventhandler
    print("DocumentChanged event handler unregistered")
except Exception as ex:
    # If unsubscribe fails, the handler only prints to the output window
    # (no modal dialogs), so it won't disrupt the session.
    print("Unsubscribe failed (pythonnet delegate limitation): {}".format(ex))

print("CPython event test completed.")
