# -*- coding: utf-8 -*-
"""Favourite categories of the Pick button and the dialog to choose them."""

from pyrevit import script
from pyrevit import DB
from pyrevit.coreutils import applocales

import favouritecategories

RESOURCES = script.get_bundle_file("resources.xaml")

# somehow DB.BuiltInCategory.OST_Truss does not have a corresponding DB.Category
DEFAULT_CATEGORIES = [
    DB.BuiltInCategory.OST_Areas,
    DB.BuiltInCategory.OST_AreaTags,
    DB.BuiltInCategory.OST_AreaSchemeLines,
    DB.BuiltInCategory.OST_Columns,
    DB.BuiltInCategory.OST_StructuralColumns,
    DB.BuiltInCategory.OST_Dimensions,
    DB.BuiltInCategory.OST_Doors,
    DB.BuiltInCategory.OST_Floors,
    DB.BuiltInCategory.OST_StructuralFraming,
    DB.BuiltInCategory.OST_Furniture,
    DB.BuiltInCategory.OST_Grids,
    DB.BuiltInCategory.OST_Rooms,
    DB.BuiltInCategory.OST_RoomTags,
    DB.BuiltInCategory.OST_Truss,
    DB.BuiltInCategory.OST_Walls,
    DB.BuiltInCategory.OST_Windows,
    DB.BuiltInCategory.OST_Ceilings,
    DB.BuiltInCategory.OST_SectionBox,
    DB.BuiltInCategory.OST_ElevationMarks,
    DB.BuiltInCategory.OST_Parking,
]


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def load_configs():
    return favouritecategories.load(DEFAULT_CATEGORIES)


if __name__ == "__main__":
    favouritecategories.configure(
        DEFAULT_CATEGORIES,
        title=_t("favourites_title"),
        button_name=_t("favourites_button"),
    )
