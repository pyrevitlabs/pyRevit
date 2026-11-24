# -*- coding: utf-8 -*-
from pyrevit import forms, script
from pyrevit.coreutils import applocales

import filter_options

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


class OptionItem(forms.TemplateListItem):
    @property
    def name(self):
        return _t(self.item)


def main():
    config = script.get_config()
    options = filter_options.load_options(config)
    results = forms.SelectFromList.show(
        [OptionItem(key, options[key]) for key, _ in filter_options.OPTION_DEFAULTS],
        title=_t("config_title"),
        multiselect=True,
        button_name=_t("config_button"),
        return_all=True,
        width=420,
        height=350,
    )
    if results:
        filter_options.save_options(config, {item.item: item.state for item in results})
        script.save_config()


if __name__ == "__main__":
    main()
