"""Test CheckBox - reference for the pyRevit CheckBox bundle.

Handlers:
- __chk_init__(ctx) runs once per ribbon load, before the change handler is
  wired, so restoring a saved state here does not fire __chk_on_change__.
- __chk_on_change__(sender, args, ctx) runs on every change of ctx.is_checked,
  from a click or from code.

Handlers run outside Revit API context: they can read and store settings
but must not start transactions. Printed text goes to the pyRevit log.
"""

from pyrevit import script

CONFIG_SECTION = "devtools_checkbox_tests"
STATE_OPTION = "test_checkbox_state"


def __chk_init__(ctx):
    config = script.get_config(CONFIG_SECTION)
    ctx.is_checked = bool(config.get_option(STATE_OPTION, default_value=ctx.is_checked))


def __chk_on_change__(sender, args, ctx):
    config = script.get_config(CONFIG_SECTION)
    config.set_option(STATE_OPTION, ctx.is_checked)
    script.save_config()
    print(
        "Test CheckBox is now {}".format("checked" if ctx.is_checked else "unchecked")
    )
