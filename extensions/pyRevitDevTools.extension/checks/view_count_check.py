# -*- coding: utf-8 -*-
from pyrevit import DB
from pyrevit.preflight import PreflightTestCase


class ViewCountCheck(PreflightTestCase):
    """Reference preflight check: counts views by type.

    Shows up in the Preflight Checks dialog under the name below.
    The first docstring line is the subtitle; the remaining lines are the description.
    """

    name = "Dev: View Count"
    author = "pyRevit"

    def startTest(self, doc, output):
        views = DB.FilteredElementCollector(doc).OfClass(DB.View)
        counts = {}
        for view in views:
            if not view.IsTemplate:
                counts[view.ViewType] = counts.get(view.ViewType, 0) + 1
        for view_type in sorted(counts, key=str):
            output.print_md("**{}**: {}".format(view_type, counts[view_type]))
