# -*- coding: utf-8 -*-
"""Favourite categories shared by the Pick and Isolate buttons.

Both buttons keep their favourites in the `favourite_categories` section of the
pyRevit config, option `fscats` (category names). A list saved from one button is
therefore also the list the other one shows; only the defaults differ per button.
"""

from pyrevit import forms, script
from pyrevit import revit, DB

CONFIG_SECTION = "favourite_categories"
CONFIG_OPTION = "fscats"


def load(default_categories):
    """Return the favourite categories saved by the user, or the defaults.

    Args:
        default_categories: Built-in categories that stand in until the user saves a
            list of their own.

    Returns:
        The categories of the current document. Names or built-in categories that
        the document has no category for are left out.
    """
    config = script.get_config(CONFIG_SECTION)
    saved_names = config.get_option(CONFIG_OPTION, [])
    categories = [
        _find_category(category) for category in (saved_names or default_categories)
    ]
    return [category for category in categories if category]


def configure(default_categories, title, button_name):
    """Ask the user which categories are favourites and save the answer.

    Side effects:
        Writes the chosen category names to the pyRevit config file. A cancelled
        dialog or an empty choice saves nothing.

    Args:
        default_categories: Built-in categories the dialog's reset button checks.
        title: Dialog title.
        button_name: Caption of the dialog's confirm button.
    """
    all_categories = list(revit.doc.Settings.Categories)
    area_scheme_lines = _area_scheme_lines()
    if area_scheme_lines:
        all_categories.append(area_scheme_lines)
    favourite_names = [category.Name for category in load(default_categories)]
    chosen = forms.SelectFromList.show(
        sorted(
            [
                forms.TemplateListItem(
                    category, checked=category.Name in favourite_names, name_attr="Name"
                )
                for category in all_categories
            ],
            key=lambda item: item.name,
        ),
        title=title,
        button_name=button_name,
        multiselect=True,
        resetfunc=lambda options: _check_defaults(default_categories, options),
    )
    if chosen:
        config = script.get_config(CONFIG_SECTION)
        config.set_option(CONFIG_OPTION, [category.Name for category in chosen])
        script.save_config()


def _area_scheme_lines():
    return revit.doc.Settings.Categories.get_Item(
        DB.BuiltInCategory.OST_AreaSchemeLines
    )


def _find_category(category):
    found = revit.query.get_category(category)
    if found:
        return found
    area_scheme_lines = _area_scheme_lines()
    if area_scheme_lines and category == area_scheme_lines.Name:
        return area_scheme_lines
    return None


def _check_defaults(default_categories, options):
    default_names = [
        category.Name
        for category in (_find_category(x) for x in default_categories)
        if category
    ]
    for option in options:
        if option.name in default_names:
            option.checked = True
