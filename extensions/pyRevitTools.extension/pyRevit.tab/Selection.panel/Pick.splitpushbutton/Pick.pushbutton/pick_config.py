"""Activates selection tool that picks a specific type of element.

Shift-Click:
Pick favorites from all available categories
"""
# pylint: disable=E0401,W0703,C0103
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
my_config = script.get_config()


# somehow DB.BuiltInCategory.OST_Truss does not have a corresponding DB.Category
FREQUENTLY_SELECTED_CATEGORIES = [
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
    DB.BuiltInCategory.OST_Parking
]


class FSCategoryItem(forms.TemplateListItem):
    """Wrapper class for frequently selected category list item"""
    pass


def load_configs():
    """Load list of frequently selected categories from configs or defaults"""
    fscats = my_config.get_option('fscats', [])
    revit_cats = [revit.query.get_category(x)
                  for x in (fscats or FREQUENTLY_SELECTED_CATEGORIES)]
    return filter(None, revit_cats)


def save_configs(categories):
    """Save given list of categories as frequently selected"""
    my_config.fscats = [x.Name for x in categories]
    script.save_config()


def reset_defaults(options):
    """Reset frequently selected categories to defaults"""
    defaults = [revit.query.get_category(x)
                for x in FREQUENTLY_SELECTED_CATEGORIES]
    default_names = [x.Name for x in defaults if x]
    for opt in options:
        if opt.name in default_names:
            opt.checked = True


def configure_fscats():
    """Ask for users frequently selected categories"""
    prev_fscats = load_configs()
    all_cats = revit.doc.Settings.Categories
    prev_fscatnames = [x.Name for x in prev_fscats]
    fscats = forms.SelectFromList.show(
        sorted(
            [FSCategoryItem(x,
                            checked=x.Name in prev_fscatnames,
                            name_attr='Name')
             for x in all_cats],
            key=lambda x: x.name
            ),
        title='Select Favorite Categories',
        button_name='Apply',
        multiselect=True,
        resetfunc=reset_defaults
    )
    if fscats:
        save_configs(fscats)
    return fscats


if __name__ == "__main__":
    configure_fscats()
