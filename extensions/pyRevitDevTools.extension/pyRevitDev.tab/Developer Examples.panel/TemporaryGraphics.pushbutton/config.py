from pyrevit import revit
from pyrevit.revit.tmpgfx import ControlManager

cm = ControlManager(revit.doc)
cm.sync()
cm.unregister()
