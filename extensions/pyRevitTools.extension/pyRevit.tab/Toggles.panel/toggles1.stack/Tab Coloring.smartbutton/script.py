"""Does its best at visually separating open documents."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import HOST_APP
from pyrevit.runtime.types import DocumentTabEventUtils
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from pyrevit import script
from pyrevit.userconfig import user_config


__context__ = 'zero-doc'
__min_revit_ver__ = 2019


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    button_icon = script_cmp.get_bundle_file(
        'on.png' if user_config.colorize_docs else 'off.png'
        )
    ui_button_cmp.set_icon(button_icon, icon_size=ICON_MEDIUM)


if __name__ == '__main__':
    if __shiftclick__: #pylint: disable=undefined-variable
        print("Active: %s" % DocumentTabEventUtils.IsUpdatingDocumentTabs)
        if DocumentTabEventUtils.DocumentBrushes:
            print("Count: %s" % DocumentTabEventUtils.DocumentBrushes.Count)
            for k, v in dict(DocumentTabEventUtils.DocumentBrushes).items():
                print(k, v)
    else:
        if DocumentTabEventUtils.IsUpdatingDocumentTabs:
            DocumentTabEventUtils.StopGroupingDocumentTabs()
        else:
            DocumentTabEventUtils.StartGroupingDocumentTabs(HOST_APP.uiapp)
        script.toggle_icon(DocumentTabEventUtils.IsUpdatingDocumentTabs)
