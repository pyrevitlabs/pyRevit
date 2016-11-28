# ----------------------------------------------------------------------------------------------------------------------
# session global environment variable defaults
# ----------------------------------------------------------------------------------------------------------------------
from ..config import PYREVIT_ASSEMBLY_NAME
from System import AppDomain

CURRENT_REVIT_APPDOMAIN = AppDomain.CurrentDomain

PYREVIT_ISC_DICT_NAME = PYREVIT_ASSEMBLY_NAME + '_dictISC'
DEBUG_ISC_NAME = PYREVIT_ASSEMBLY_NAME + '_debugISC'
VERBOSE_ISC_NAME = PYREVIT_ASSEMBLY_NAME + '_verboseISC'


# ----------------------------------------------------------------------------------------------------------------------
# portable git and LibGit2Sharp git tools
# ----------------------------------------------------------------------------------------------------------------------
GIT_LIB = 'LibGit2Sharp'


# ----------------------------------------------------------------------------------------------------------------------
# creating ui for tabs, panels, buttons and button groups
# ----------------------------------------------------------------------------------------------------------------------
PYREVIT_TAB_IDENTIFIER = 'pyrevit_tab'

ICON_SMALL = 16
ICON_MEDIUM = 24
ICON_LARGE = 32
SPLITPUSH_BUTTON_SYNC_PARAM = 'IsSynchronizedWithCurrentItem'

CONFIG_SCRIPT_TITLE_POSTFIX = u'\u25CF'

