# -*- coding: utf-8 -*-

from time import sleep

from pyrevit import HOME_DIR
from pyrevit.coreutils import check_internet_connection
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.ribbon import ICON_LARGE
from pyrevit.loader.sessionmgr import load_session

import pyrevit.versionmgr.updater as updater
import pyrevit.versionmgr.upgrade as upgrade
from pyrevit.userconfig import user_config

from scriptutils import logger, this_script


__doc__ = 'Downloads updates from the remote libgit repositories (e.g github, bitbucket).'


COREUPDATE_MESSAGE = '<div style="background:#F7F3F2; color:#C64325; padding:20px; margin:10px 0px 10px 0px; ' \
                                 'border: 2px solid #C64325; border-radius:10px;">' \
                     ':warning_sign:\n\nIMPORTANT:\n' \
                     'pyRevit has a major core update. This update <u>can not</u> be applied when Revit is running. ' \
                     'Please close all Revit instances, and run the tool listed below to update the repository. ' \
                     'Start Revit again after the update and pyRevit will load with the new core changes:\n\n' \
                     '{home}\\release\\<strong>upgrade.bat</strong>' \
                     '</div>'

def _check_connection():
    logger.info('Checking internet connection...')
    successful_url = check_internet_connection()
    if successful_url:
        logger.debug('Url access successful: {}'.format(successful_url))
        return True
    else:
        return False


def _check_for_updates():
    if _check_connection():
        logger.info('Checking for updates...')

        for repo in updater.get_all_extension_repos():
            if updater.has_pending_updates(repo):
                return True
    else:
        logger.warning('No internet access detected. Skipping check for updates.')
        return False


def _update_repo(repo_info):
    # update one by one
    logger.debug('Updating repo: {}'.format(repo_info.directory))
    try:
        upped_repo_info = updater.update_pyrevit(repo_info)
        logger.info(':inbox_tray: Successfully updated: {} to {}'.format(upped_repo_info.name,
                                                                         upped_repo_info.last_commit_hash[:7]))
    except:
        logger.info('Can not update repo: {}  (Run in debug to see why)'.format(repo_info.name))


# noinspection PyUnusedLocal
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    try:
        has_update_icon = script_cmp.get_bundle_file('icon_hasupdates.png')
        if user_config.core.checkupdates and _check_for_updates():
            ui_button_cmp.set_icon(has_update_icon, icon_size=ICON_LARGE)
    except:
        return


if __name__ == '__main__':
    # collect a list of all repos to be updates
    if _check_connection():
        pyrevit_repo = updater.get_pyrevit_repo()
        thirdparty_repos = updater.get_thirdparty_ext_repos()

        logger.debug('List of thirdparty repos to be updated: {}'.format(thirdparty_repos))

        for thirdparty_repo_info in thirdparty_repos:
            _update_repo(thirdparty_repo_info)

        if not updater.has_core_updates():
            _update_repo(pyrevit_repo)
            # perform upgrade tasks
            logger.info('Upgrading settings...')
            upgrade.upgrade_existing_pyrevit()

            # now re-load pyrevit session.
            sleep(1)
            logger.info('Reloading...')
            load_session()
        else:
            this_script.output.print_html(COREUPDATE_MESSAGE.format(home=HOME_DIR))
            logger.debug('Core updates. Skippin update and reload.')
    else:
        logger.warning('No internet access detected. Skipping update.')
