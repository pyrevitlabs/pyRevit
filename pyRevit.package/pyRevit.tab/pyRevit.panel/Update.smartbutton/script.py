"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Downloads updates from the github repository.'

from pyrevit.logger import get_logger
logger = get_logger(__commandname__)

from pyrevit.config import ICON_LARGE_SIZE
from pyrevit.loader import updater

def selfInit(__rvt__, script_cmp, commandbutton):
    has_update_icon = script_cmp.get_bundle_file('icon_hasupdates.png')
    for repo in updater._find_all_pkg_repos():
        if updater.has_pending_updates(repo):
            commandbutton.set_icon(has_update_icon, icon_size=ICON_LARGE_SIZE)


if __name__ == '__main__':
    import pyrevit.session as session
    if updater.update_pyrevit():
        logger.info('Successfully updated...')
        # re-load pyrevit session.
        logger.info('Reloading...')
        session.load()
    else:
        logger.info('Already updated...')
