# -*- coding: utf-8 -*-
"""Choose how the pyRevit Python Shell opens: modal, modeless, docked, or with
a built-in code editor panel (editor variants include a dockable editor pane)."""
from pyrevit import script, forms

shell_config = script.get_config()
current_mode = shell_config.get_option("mode", "Modeless")

modes = [
    "Modeless",
    "Modeless Editor",
    "Modal",
    "Modal Editor",
    "Docked",
    "Docked Editor",
]
selected = forms.ask_for_one_item(
    modes,
    default=current_mode,
    prompt="How should the Python Shell open?",
    title="Python Shell Mode",
)

if selected:
    shell_config.set_option("mode", selected)
    script.save_config()
