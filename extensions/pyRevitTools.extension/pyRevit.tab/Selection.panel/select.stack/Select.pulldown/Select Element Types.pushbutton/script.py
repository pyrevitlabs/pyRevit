# -*- coding: utf-8 -*-
"""Select all element types of a family, graphics style category or style list."""

from functools import partial

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

logger = script.get_logger()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def types_by_family_name():
    types = {}
    for element_type in revit.query.get_types_by_class(DB.ElementType, doc=revit.doc):
        if element_type.FamilyName:
            types.setdefault(element_type.FamilyName, []).append(element_type)
    return types


def graphics_styles_by_category_name():
    styles = {}
    for style in revit.query.get_types_by_class(DB.GraphicsStyle, doc=revit.doc):
        category = style.GraphicsStyleCategory
        if category and category.CategoryType != DB.CategoryType.Internal:
            styles.setdefault(category.Name, []).append(style)
    return styles


def own_named_types(family_name, element_types):
    return [
        element_type
        for element_type in element_types
        if revit.query.get_name(element_type) != family_name
    ]


def type_choices():
    choices = {}
    for family_name, element_types in types_by_family_name().items():
        choices[family_name] = partial(own_named_types, family_name, element_types)
    for category_name, styles in graphics_styles_by_category_name().items():
        choices[_t("graphics_styles").format(category_name)] = partial(list, styles)
    choices[_t("fill_patterns")] = partial(
        revit.query.get_types_by_class, DB.FillPatternElement, doc=revit.doc
    )
    choices[_t("area_schemes")] = partial(
        revit.query.get_types_by_class, DB.AreaScheme, doc=revit.doc
    )
    choices[_t("line_styles")] = partial(revit.query.get_line_styles, doc=revit.doc)
    return choices


def main():
    choices = type_choices()
    choice = forms.CommandSwitchWindow.show(
        sorted(choices), message=_t("pick_category"), recognize_access_key=False
    )
    if not choice:
        return
    logger.debug(choice)
    types = list(choices[choice]())
    if not types:
        forms.alert(_t("no_types"), exitscript=True)
    revit.get_selection().set_to(types)


if __name__ == "__main__":
    main()
