# -*- coding: utf-8 -*-
"""Pick elements that share the parameter values of a chosen element."""

from pyrevit import forms, script
from pyrevit import revit, EXEC_PARAMS
from pyrevit.coreutils import applocales

import selectionpick

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def get_source_element():
    selected = list(revit.get_selection())
    if len(selected) == 1:
        return selected[0]
    return revit.pick_element(message=_t("pick_element_prompt"))


def read_parameter_values(element, parameter_names):
    parameters = {name: element.LookupParameter(name) for name in parameter_names}
    return {
        name: revit.query.get_param_value(parameter)
        for name, parameter in parameters.items()
        if parameter
    }


def has_value(element, name, expected_value):
    parameter = element.LookupParameter(name)
    if not parameter:
        return False
    return revit.query.get_param_value(parameter) == expected_value


def matches_values(element, expected_values, require_all):
    results = [
        has_value(element, name, value) for name, value in expected_values.items()
    ]
    if require_all:
        # ALL match (config mode)
        return all(results)
    # ANY match (default mode)
    return any(results)


def main():
    source = get_source_element()
    if not source:
        return
    parameter_defs = forms.select_parameters(
        source,
        title=_t("select_parameters_title"),
        button_name=_t("select_parameters_button"),
        exclude_readonly=False,
    )
    if not parameter_defs:
        return
    expected_values = read_parameter_values(source, [x.name for x in parameter_defs])
    if not expected_values:
        forms.alert(_t("no_readable_parameters"))
        return
    require_all = EXEC_PARAMS.config_mode
    selectionpick.select_picked(
        lambda element: matches_values(element, expected_values, require_all),
        message=_t("pick_rectangle_prompt"),
    )


if __name__ == "__main__":
    main()
