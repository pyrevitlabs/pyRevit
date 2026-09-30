"""Verify that IronPython can subscribe to and unsubscribe from a Revit event."""

# pylint: skip-file
from pyrevit import HOST_APP, framework
from pyrevit import DB


def docchanged_eventhandler(sender, args):
    """Report a DocumentChanged event if the subscribed handler is invoked."""
    print("DocumentChanged fired: {}".format(args.GetTransactionNames()))


docchanged_handler = framework.EventHandler[DB.Events.DocumentChangedEventArgs](
    docchanged_eventhandler
)

HOST_APP.app.DocumentChanged += docchanged_handler
print("DocumentChanged event handler registered")
HOST_APP.app.DocumentChanged -= docchanged_handler
print("DocumentChanged event handler unregistered")
print("IronPython event subscription test passed.")
