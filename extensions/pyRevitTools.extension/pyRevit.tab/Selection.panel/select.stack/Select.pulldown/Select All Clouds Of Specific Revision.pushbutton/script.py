# -*- coding: utf-8 -*-
"""Select all revision clouds that belong to a revision picked from a list."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def main():
    revision = forms.select_revisions(
        title=_t("dialog_title"), button_name=_t("button_name"), multiple=False
    )
    if not revision:
        return
    clouds = revit.query.get_elements_by_class(DB.RevisionCloud, doc=revit.doc)
    cloud_ids = [cloud.Id for cloud in clouds if cloud.RevisionId == revision.Id]
    if not cloud_ids:
        forms.alert(_t("no_clouds"), exitscript=True)
    revit.get_selection().set_to(cloud_ids)


if __name__ == "__main__":
    main()
