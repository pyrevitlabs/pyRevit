"""Host application feature detectors."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import DB, UI

# check whether global parameters feature is available
GLOBAL_PARAMS = hasattr(DB, 'GlobalParametersManager')
