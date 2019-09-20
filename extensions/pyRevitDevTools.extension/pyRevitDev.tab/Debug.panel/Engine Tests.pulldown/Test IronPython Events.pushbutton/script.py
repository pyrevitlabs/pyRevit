# pylint: skip-file
from pyrevit import HOST_APP, framework
from pyrevit import UI, DB


dc = __revit__.Application.GetType().GetEvent("DocumentChanged")


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

# dc.AddEventHandler(__revit__.Application, docchanged_handler)
# dc.RemoveEventHandler(__revit__.Application, docchanged_handler)