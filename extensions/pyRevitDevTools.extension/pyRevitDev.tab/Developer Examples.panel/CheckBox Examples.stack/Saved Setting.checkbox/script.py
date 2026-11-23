"""Developer example: a checkbox that stores a setting for commands to read.

__chk_init__ restores the saved state when the ribbon loads. Setting
ctx.is_checked there does not raise __chk_on_change__, because the change
handler is connected only after __chk_init__ returns. __chk_on_change__
saves each new state, and Toggle Examples > Show Saved Setting reads it.

Checkbox handlers run outside Revit API context, so they store state and
never start transactions; commands and hooks act on it.
"""

import devtools_examples_settings

SETTING = "saved_setting"


def __chk_init__(ctx):
    ctx.is_checked = devtools_examples_settings.is_enabled(
        SETTING, default=ctx.is_checked
    )


def __chk_on_change__(sender, args, ctx):
    devtools_examples_settings.set_enabled(SETTING, ctx.is_checked)
