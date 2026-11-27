# -*- coding: utf-8 -*-
"""tmpgfx example — remove the icons this example placed."""

from pyrevit import script

STATE_ENVVAR = "PYREVITDEV_TMPGFX_EXAMPLE"

state = script.get_envvar(STATE_ENVVAR)
if state:
    for document, manager in state["managers"].values():
        if document.IsValidObject:
            manager.clear_all()
    state["handler"].unregister()
    script.set_envvar(STATE_ENVVAR, None)
