# -*- coding: utf-8 -*-
"""Select all revision clouds that share a comment with the selected revision clouds."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def comment_of(cloud):
    parameter = cloud.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    return parameter.AsString() if parameter else None


def main():
    selected_clouds = [
        element
        for element in revit.get_selection().elements
        if isinstance(element, DB.RevisionCloud)
    ]
    comments = {comment_of(cloud) for cloud in selected_clouds}
    comments.discard(None)
    comments.discard("")
    if not comments:
        forms.alert(_t("no_comment"), exitscript=True)
    clouds = revit.query.get_elements_by_class(DB.RevisionCloud, doc=revit.doc)
    revit.get_selection().set_to(
        [cloud.Id for cloud in clouds if comment_of(cloud) in comments]
    )


if __name__ == "__main__":
    main()
