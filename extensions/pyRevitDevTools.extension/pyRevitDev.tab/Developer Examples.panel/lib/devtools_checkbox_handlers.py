"""Checkbox handlers that the Shared A and Shared B examples both use.

Each checkbox imports these as its own ``__chk_init__`` and
``__chk_on_change__``. ``EXEC_PARAMS`` and ``script.get_config()`` still
resolve the checkbox the handler runs for, and ``ctx.user_data`` belongs to
that checkbox, so each one keeps its own saved state and change count.
"""

from pyrevit import EXEC_PARAMS, script

STATE_OPTION = "state"
CHANGE_COUNT_KEY = "change_count"


def init(ctx):
    """Restore the checkbox's saved state when the ribbon loads."""
    config = script.get_config()
    ctx.is_checked = bool(config.get_option(STATE_OPTION, default_value=ctx.is_checked))


def on_change(sender, args, ctx):
    """Save the checkbox's state and log how often it changed since the last reload.

    Note:
        ``ctx.user_data`` is a .NET dictionary that lasts until the next
        pyRevit reload. On IronPython 2.7 it has no ``get``, so keys are
        tested with ``ContainsKey``.
    """
    config = script.get_config()
    config.set_option(STATE_OPTION, ctx.is_checked)
    script.save_config()

    user_data = ctx.user_data
    count = 1
    if user_data.ContainsKey(CHANGE_COUNT_KEY):
        count += user_data[CHANGE_COUNT_KEY]
    user_data[CHANGE_COUNT_KEY] = count
    print(
        "{} is {}, changed {} times since the last reload".format(
            EXEC_PARAMS.command_name, "on" if ctx.is_checked else "off", count
        )
    )
