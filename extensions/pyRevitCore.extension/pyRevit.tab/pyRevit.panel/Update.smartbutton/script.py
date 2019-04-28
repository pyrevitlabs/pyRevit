# -*- coding: utf-8 -*-
"""Download updates for all repos."""

from pyrevit.coreutils import ribbon
from pyrevit.versionmgr import updater
from pyrevit.userconfig import user_config
from pyrevit import script


logger = script.get_logger()


__context__ = 'zerodoc'

__doc__ = 'Downloads updates from the remote git repositories ' \
          '(e.g github, bitbucket).'


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # do not load the tool if user should not update
    if not user_config.core.get_option('usercanupdate', True):
        return False
    # otherwise set icon depending on if updates are available
    try:
        has_update_icon = script_cmp.get_bundle_file('icon_hasupdates.png')
        if user_config.core.get_option('checkupdates', False) \
                and not user_config.core.get_option('autoupdate', False) \
                and updater.check_for_updates():
            ui_button_cmp.set_icon(has_update_icon,
                                   icon_size=ribbon.ICON_LARGE)
        return True
    except Exception as e:
        logger.error('Error in checking updates: {}'.format(e))
        return False


if __name__ == '__main__':
    updater.update_pyrevit()
