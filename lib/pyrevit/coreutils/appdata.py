import os
import os.path as op

from pyrevit.core.exceptions import PyRevitException

# noinspection PyUnresolvedReferences
from System.IO import IOException


# user env paths
USER_ROAMING_DIR = os.getenv('appdata')
USER_SYS_TEMP = os.getenv('temp')


# pyrevit temp file directory
PYREVIT_APP_DIR = op.join(USER_ROAMING_DIR, 'pyRevit')

if not op.isdir(PYREVIT_APP_DIR):
    try:
        os.mkdir(PYREVIT_APP_DIR)
    except (OSError, IOException) as err:
        raise PyRevitException('Can not access pyRevit folder at: {} | {}'.format(PYREVIT_APP_DIR, err))
