"""Assert engine injection when invoked through the event-hook executor."""

from pyrevit import EXEC_PARAMS, HOST_APP, UI
from System import Object


assert isinstance(__revit__, UI.UIApplication), "Hook handle must be UIApplication"
assert Object.ReferenceEquals(__eventsender__, EXEC_PARAMS.event_sender)
assert Object.ReferenceEquals(__eventargs__, EXEC_PARAMS.event_args)
assert HOST_APP.app.VersionNumber == __revit__.Application.VersionNumber
assert HOST_APP.uiapp is not None
assert __scriptruntime__.UIApp is not None
print(
    "PASS: hook handle={}, raw sender={}".format(
        __revit__.GetType().FullName,
        __eventsender__.GetType().FullName if __eventsender__ is not None else "None",
    )
)
