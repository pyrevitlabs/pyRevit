"""Reload pyRevit into new session."""
# -*- coding=utf-8 -*-
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import EXEC_PARAMS
from pyrevit import script
from pyrevit import forms
from pyrevit.loader import sessionmgr
from pyrevit.loader import sessioninfo


__cleanengine__ = True
__context__ = 'zero-doc'
__doc__ = 'Searches the script folders and create buttons ' \
          'for the new script or newly installed extensions.'
__title__ = {
    'en_us': 'Reload',
    'fa': 'بارگذاری مجدد',
    'bg': 'Презареди',
    'nl_nl': 'Herladen',
}


res = True
if EXEC_PARAMS.executed_from_ui:
    res = forms.alert('Reloading increases the memory footprint and is '
                      'automatically called by pyRevit when necessary.\n\n'
                      'pyRevit developers can manually reload when:\n'
                      '    - New buttons are added.\n'
                      '    - Buttons have been removed.\n'
                      '    - Button icons have changed.\n'
                      '    - Base C# code has changed.\n'
                      '    - Value of pyRevit parameters\n'
                      '      (e.g. __title__, __doc__, ...) have changed.\n'
                      '    - Cached engines need to be cleared.\n\n'
                      'Are you sure you want to reload?',
                      ok=False, yes=True, no=True)

if res:
    logger = script.get_logger()
    results = script.get_results()

    # re-load pyrevit session.
    logger.info('Reloading....')
    sessionmgr.reload_pyrevit()

    results.newsession = sessioninfo.get_session_uuid()
