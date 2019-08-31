"""Prints calculated hash values for each extension."""

__title__ = 'Get Extension\nHash Values'
__highlight_updated__= True
__context__ = 'zero-doc'
# __beta__ = True

from pyrevit import HOST_APP
from pyrevit import script
from pyrevit.extensions import extensionmgr
from pyrevit.runtime import types

# logger = script.get_logger()
# logger.set_quiet_mode()


# for ui_ext in extensionmgr.get_installed_ui_extensions():
#     print('{}\t\tExtension: {}'.format(ui_ext.dir_hash_value, ui_ext.name))


# logger.reset_level()

if __shiftclick__:
    print("Active: %s" % types.DocumentTabEventUtils.IsUpdatingDocumentTabs)
    if types.DocumentTabEventUtils.DocumentBrushes:
        print("Count: %s" % types.DocumentTabEventUtils.DocumentBrushes.Count)
        for k,v in dict(types.DocumentTabEventUtils.DocumentBrushes).items():
            print(k, v)
else:
    if types.DocumentTabEventUtils.IsUpdatingDocumentTabs:
        types.DocumentTabEventUtils.StopGroupingDocumentTabs(HOST_APP.uiapp)
    else:
        types.DocumentTabEventUtils.StartGroupingDocumentTabs(HOST_APP.uiapp)