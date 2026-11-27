# -*- coding: utf-8 -*-
"""Temporarily isolate elements of a favourite category or kind in the active view."""

from pyrevit import framework
from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

import isolate_config

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def view_element_ids(view):
    return (
        DB.FilteredElementCollector(revit.doc, view.Id)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )


def category_element_ids(view, category_id):
    return framework.to_clr_list(
        DB.ElementId,
        DB.FilteredElementCollector(revit.doc, view.Id)
        .OfCategoryId(category_id)
        .WhereElementIsNotElementType()
        .ToElementIds(),
    )


def room_and_room_tag_ids(view):
    rooms = category_element_ids(view, DB.ElementId(DB.BuiltInCategory.OST_Rooms))
    room_tags = category_element_ids(
        view, DB.ElementId(DB.BuiltInCategory.OST_RoomTags)
    )
    return framework.to_clr_list(DB.ElementId, list(rooms) + list(room_tags))


def model_group_and_member_ids(view):
    model_groups = []
    members = []
    for element_id in view_element_ids(view):
        element = revit.doc.GetElement(element_id)
        if isinstance(element, DB.Group) and not element.ViewSpecific:
            model_groups.append(element_id)
            members.extend(list(element.GetMemberIds()))
    return framework.to_clr_list(DB.ElementId, members + model_groups)


def has_painted_faces(element):
    return len(list(element.GetMaterialIds(True))) > 0


def is_painted(element):
    if has_painted_faces(element):
        return True
    if isinstance(element, DB.Wall) and element.IsStackedWall:
        return any(
            has_painted_faces(revit.doc.GetElement(member_id))
            for member_id in element.GetStackedWallMemberIds()
        )
    return False


def painted_element_ids(view):
    return framework.to_clr_list(
        DB.ElementId,
        [
            element_id
            for element_id in view_element_ids(view)
            if is_painted(revit.doc.GetElement(element_id))
        ],
    )


def model_element_ids(view):
    element_to_isolate = []
    for element_id in view_element_ids(view):
        element = revit.doc.GetElement(element_id)
        if not element.ViewSpecific:  # and not isinstance(el, DB.Dimension)
            element_to_isolate.append(element_id)
    return framework.to_clr_list(DB.ElementId, element_to_isolate)


def _category_label(category_name, action_labels):
    if category_name in action_labels:
        return _t("category_option_format").format(category_name)
    return category_name


def build_isolation_options():
    actions = [
        (_t("option_room_tags"), room_and_room_tag_ids),
        (_t("option_model_groups"), model_group_and_member_ids),
        (_t("option_painted_elements"), painted_element_ids),
        (_t("option_model_elements"), model_element_ids),
    ]
    action_labels = [label for label, _ in actions]
    favourites = sorted(isolate_config.load_configs(), key=lambda x: x.Name)
    options = [
        (
            _category_label(category.Name, action_labels),
            lambda view, category_id=category.Id: category_element_ids(
                view, category_id
            ),
        )
        for category in favourites
    ]
    options.extend(actions)
    return options


def isolate(view, selected_label, collect_ids):
    isolate_name = _t("transaction_isolate").format(selected_label)
    with revit.TransactionGroup(isolate_name):
        with revit.Transaction(_t("transaction_reset_isolate")):
            # reset temporary hide/isolate before filtering elements
            view.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)
        elements_to_isolate = collect_ids(view)
        if elements_to_isolate.Count:
            with revit.Transaction(isolate_name):
                # now that list of elements is ready,
                # let's isolate them in the active view
                view.IsolateElementsTemporary(elements_to_isolate)
    return bool(elements_to_isolate.Count)


def main():
    options = build_isolation_options()
    selected_label = forms.CommandSwitchWindow.show(
        [label for label, _ in options],
        title=_t("window_title"),
        message=_t("window_message"),
    )
    if not selected_label:
        return
    collect_ids = dict(options)[selected_label]
    if not isolate(revit.active_view, selected_label, collect_ids):
        forms.alert(_t("nothing_to_isolate").format(selected_label))


if __name__ == "__main__":
    main()
