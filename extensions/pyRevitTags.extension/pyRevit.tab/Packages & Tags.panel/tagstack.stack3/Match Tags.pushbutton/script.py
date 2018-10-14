"""Match Tags between selected elements."""

#pylint: disable=C0111,E0401,C0103,W0613
from pyrevit import revit
from pyrevit import forms

import tagscfg
import tagsmgr


__author__ = '{{author}}'


def pick_and_match_styles(src_element):
    with forms.WarningBar(title='Pick target elements:'):
        while True:
            dest_element = revit.pick_element()

            if not dest_element:
                break

            with revit.Transaction('Match Tags'):
                tagsmgr.match_tags(src_element, [dest_element])


with forms.WarningBar(title='Pick source element:'):
    source_element = revit.pick_element()

if source_element:
    # make sure tags param is setup correctly
    tagscfg.ensure_tag_param()

    pick_and_match_styles(source_element)
