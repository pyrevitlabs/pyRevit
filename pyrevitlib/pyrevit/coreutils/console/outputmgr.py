from pyrevit.coreutils.loadertypes import ExternalConfig

# noinspection PyUnresolvedReferences
from System import AppDomain


def _get_all_open_consoles():
    output_list_entryname = ExternalConfig.pyrevitconsolesappdata
    return list(AppDomain.CurrentDomain.GetData(output_list_entryname))


def get_all_consoles(command=None):
    if command:
        return [x for x in _get_all_open_consoles()
                  if x.commandUniqueName == command]
    else:
        return _get_all_open_consoles()
