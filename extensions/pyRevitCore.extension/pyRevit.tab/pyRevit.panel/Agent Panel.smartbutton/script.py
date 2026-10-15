# -*- coding: utf-8 -*-
"""Open the pyRevit Agent panel.

The panel belongs to the agent host in the pyRevit runtime, which registers it
when Revit starts; this button only shows it. The button hides itself while the
agent host is turned off in the pyRevit settings.
"""

from System import Array, Object

from pyrevit import HOST_APP
from pyrevit.coreutils import assmutils
from pyrevit.labs import PyRevit
from pyrevit.runtime import RUNTIME_ASSM

AGENT_PANEL = "PyRevitLabs.PyRevit.Runtime.Agent.AgentPanel"


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    """Show the button only while the agent host is turned on."""
    ui_button_cmp.visible = bool(PyRevit.PyRevitConfigs.GetAgentEnabled())
    return True


if __name__ == "__main__":
    panel = assmutils.find_type_by_name(RUNTIME_ASSM, AGENT_PANEL)
    panel.GetMethod("Show").Invoke(None, Array[Object]([HOST_APP.uiapp]))
