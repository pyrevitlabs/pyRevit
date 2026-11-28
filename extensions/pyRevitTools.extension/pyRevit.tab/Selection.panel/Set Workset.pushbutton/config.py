# -*- coding: utf-8 -*-
"""Choose what the Set Workset button sets from the selected element."""

from pyrevit import forms, script
from pyrevit.coreutils import applocales

my_config = script.get_config()

RESOURCES = script.get_bundle_file("resources.xaml")
OPTION_DEFAULTS = [
    ("set_workset", True),
    ("set_workset_checkout", False),
    ("set_workplane_to_level", False),
    ("set_workplane_visible", False),
    ("set_phase", False),
    # ("set_design_option", False),
]


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


class ConfigOption(forms.TemplateListItem):
    @property
    def name(self):
        return _t("option_" + self.item)


def main():
    options = [
        ConfigOption(key, my_config.get_option(key, default))
        for key, default in OPTION_DEFAULTS
    ]
    results = forms.SelectFromList.show(
        options,
        title=_t("config_title"),
        multiselect=True,
        button_name=_t("config_button"),
        return_all=True,
        width=300,
        height=350,
    )
    if not results:
        return
    states = {result.item: result.state for result in results}
    for key, _ in OPTION_DEFAULTS:
        my_config.set_option(key, states.get(key, False))
    script.save_config()


if __name__ == "__main__":
    main()
