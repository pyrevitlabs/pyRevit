#! python3
# pylint: skip-file
from pyrevit import HOST_APP, framework
from pyrevit import UI, DB


def docchanged_eventhandler(sender, args):
    UI.TaskDialog.Show("cpython", str(sender))
    UI.TaskDialog.Show("cpython", str(args))
    UI.TaskDialog.Show("cpython", "docchanged_eventhandler")


docchanged_handler = \
    framework.EventHandler[DB.Events.DocumentChangedEventArgs](
        docchanged_eventhandler
    )

HOST_APP.app.DocumentChanged += docchanged_handler
HOST_APP.app.DocumentChanged -= docchanged_handler