# -*- coding: utf-8 -*-

"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
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
from pyrevit.coreutils import check_internet_connection
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.ribbon import ICON_LARGE
from pyrevit.loader.sessionmgr import load_session

import pyrevit.versionmgr.updater as updater
from pyrevit.userconfig import user_config


# noinspection PyUnresolvedReferences
logger = get_logger(__commandname__)


__doc__ = 'Downloads updates from the remote libgit repositories (e.g github, bitbucket).'


def _check_connection():
    logger.info('Checking internet connection...')
    successful_url = check_internet_connection()
    if successful_url:
        logger.debug('Url access successful: {}'.format(successful_url))
        return True
    else:
        return False

def _check_updates():
    if _check_connection():
        logger.info('Checking for updates...')

        for repo in updater.get_all_extension_repos():
            if updater.has_pending_updates(repo):
                return True
    else:
        logger.warning('No internet access detected. Skipping check for updates.')
        return False


# noinspection PyUnusedLocal
def __selfinit__(script_cmp, commandbutton, __rvt__):
    try:
        has_update_icon = script_cmp.get_bundle_file('icon_hasupdates.png')
        if user_config.init.checkupdates and _check_updates():
            commandbutton.set_icon(has_update_icon, icon_size=ICON_LARGE)
    except:
        return

if __name__ == '__main__':
    # collect a list of all repos to be updates
    if _check_connection():
        repo_info_list = updater.get_all_extension_repos()
        logger.debug('List of repos to be updated: {}'.format(repo_info_list))

        for repo_info in repo_info_list:
            # update one by one
            logger.debug('Updating repo: {}'.format(repo_info.directory))
            upped_repo_info = updater.update_pyrevit(repo_info)
            if upped_repo_info:
                logger.info(':inbox_tray: Successfully updated: {} to {}'.format(upped_repo_info.name,
                                                                                 upped_repo_info.last_commit_hash[:7]))

        # now re-load pyrevit session.
        logger.info('Reloading...')
        load_session()
    else:
        logger.warning('No internet access detected. Skipping update.')
