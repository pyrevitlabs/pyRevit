# -*- coding: utf-8 -*-
"""Pick only the elements of one favourite category by drawing a rectangle."""

from pyrevit import forms, script
from pyrevit.coreutils import applocales

# import this script's configurator
import pick_config
import selectionpick

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def is_in_category(element, category):
    return element.Category is not None and element.Category.Id == category.Id


def main():
    categories = pick_config.load_configs()
    if not categories:
        return
    # ask user to select a category to select by
    selected_name = forms.CommandSwitchWindow.show(
        sorted(category.Name for category in categories),
        title=_t("choose_category"),
        message=_t("choose_category"),
    )
    if not selected_name:
        return
    category = next(x for x in categories if x.Name == selected_name)
    selectionpick.select_picked(lambda element: is_in_category(element, category))


if __name__ == "__main__":
    main()
