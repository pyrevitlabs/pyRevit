# -*- coding: utf-8 -*-
"""Download updates for all repos."""

from pyrevit.coreutils import ribbon
from pyrevit.versionmgr import updater
from pyrevit.userconfig import user_config
from pyrevit import script


logger = script.get_logger()


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # do not load the tool if user should not update
    if not user_config.user_can_update:
        return False
    # set icon if updates available; a failed availability check must not
    # deactivate the tool that performs the update
    try:
        if user_config.check_updates \
                and not user_config.auto_update \
                and updater.check_for_updates():
            has_update_icon = script_cmp.get_bundle_file('icon_hasupdates.png')
            ui_button_cmp.set_icon(has_update_icon,
                                   icon_size=ribbon.ICON_LARGE)
    except Exception as ex:
        logger.error('Error in checking updates: %s', ex)
    return True


if __name__ == '__main__':
    updater.update_pyrevit()
