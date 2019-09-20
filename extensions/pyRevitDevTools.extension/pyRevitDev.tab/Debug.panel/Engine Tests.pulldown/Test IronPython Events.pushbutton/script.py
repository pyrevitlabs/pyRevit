# pylint: skip-file
from pyrevit import HOST_APP, framework
from pyrevit import UI, DB


def docchanged_eventhandler(sender, args):
    UI.TaskDialog.Show("ironpython", str(sender))
    UI.TaskDialog.Show("ironpython", str(args))
    UI.TaskDialog.Show("ironpython", "docchanged_eventhandler")


docchanged_handler = \
    framework.EventHandler[DB.Events.DocumentChangedEventArgs](
        docchanged_eventhandler
    )

HOST_APP.app.DocumentChanged += docchanged_handler
HOST_APP.app.DocumentChanged -= docchanged_handler