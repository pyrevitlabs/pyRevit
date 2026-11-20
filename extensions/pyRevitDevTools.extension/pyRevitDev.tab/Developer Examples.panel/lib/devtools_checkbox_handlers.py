"""Checkbox handlers that the Shared A and Shared B examples both use.

Each checkbox imports these as its own ``__chk_init__`` and
``__chk_on_change__``. ``script.get_config()`` still resolves the checkbox
the handler runs for, and ``ctx.user_data`` belongs to that checkbox, so each
one keeps its own saved state and change count. The count goes in the
checkbox's label because handler output only reaches the pyRevit log, which
pyRevit records only when verbose or file logging is on.
"""

from pyrevit import script

STATE_OPTION = "state"
LABEL_KEY = "label"
CHANGE_COUNT_KEY = "change_count"


def init(ctx):
    """Restore the checkbox's saved state and remember its label.

    Note:
        pyRevit resets the label to the bundle title on every load, before
        ``__chk_init__`` runs, so the label kept here never carries an old
        count.
    """
    config = script.get_config()
    ctx.is_checked = bool(config.get_option(STATE_OPTION, default_value=ctx.is_checked))
    ctx.user_data[LABEL_KEY] = ctx.text


def on_change(sender, args, ctx):
    """Save the checkbox's state and show its change count in the label.

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
    ctx.text = "{} ({})".format(user_data[LABEL_KEY], count)
