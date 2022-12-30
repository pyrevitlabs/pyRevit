from pyrevit.coreutils.ribbon import ICON_MEDIUM
from pyrevit import script
from pyrevit.userconfig import user_config
from pyrevit import forms

__context__ = "zero-doc"
__title__ = "Autosave"
__author__ = "Alex D\'Aversa"


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    if user_config.has_section("autosave") and user_config.autosave.has_option(
        "enabled"
    ):
        button_icon = script_cmp.get_bundle_file(
            "on.png" if user_config.autosave.get_option("enabled") else "off.png"
        )
    else:
        user_config.add_section("autosave")
        user_config.autosave.interval = 900
        user_config.autosave.enabled = False
        user_config.save_changes()
        button_icon = script_cmp.get_bundle_file(
            "on.png" if user_config.autosave.get_option("enabled") else "off.png"
        )
    ui_button_cmp.set_icon(button_icon, icon_size=ICON_MEDIUM)


def toggle_autosave():
    if user_config.autosave.enabled == False:
        user_config.autosave.enabled = True
    else:
        user_config.autosave.enabled = False
    user_config.save_changes()
    return user_config.autosave.enabled


def config_autosave_interval():
    default_interval = user_config.autosave.interval / 60
    interval = forms.GetValueWindow.show(
        None,
        value_type="slider",
        default=default_interval,
        prompt="Set autosave interval in minutes:",
        title="Autosave Interval",
        min=5,
        max=240,
    )
    if interval:
        user_config.autosave.interval = int(interval * 60)
        user_config.save_changes()

if __name__ == "__main__":
    if __shiftclick__:
        config_autosave_interval()
    else:
        is_active = toggle_autosave()
        script.toggle_icon(is_active)
