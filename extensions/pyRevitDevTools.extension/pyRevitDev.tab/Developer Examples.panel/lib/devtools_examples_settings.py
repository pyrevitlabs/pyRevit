"""On/off settings that the Developer Examples share through the pyRevit user config.

The Saved Setting checkbox writes a setting here and the Show Saved Setting
command reads it back. A checkbox handler runs outside Revit API context, so
it can only store state; code that runs in API context, such as a command or
a hook, acts on it.
"""

from pyrevit import script

CONFIG_SECTION = "devtools_examples"


def is_enabled(option, default=False):
    """Return the saved value of a setting in the ``devtools_examples`` section.

    Returns ``default`` when the setting was never saved.
    """
    config = script.get_config(CONFIG_SECTION)
    return bool(config.get_option(option, default_value=default))


def set_enabled(option, value):
    """Save a setting in the ``devtools_examples`` section.

    Note:
        Writes the pyRevit user config file.
    """
    config = script.get_config(CONFIG_SECTION)
    config.set_option(option, bool(value))
    script.save_config()
