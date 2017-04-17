import clr
from pyrevit import EXEC_PARAMS
from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
import System


logger = get_logger(__name__)


if not EXEC_PARAMS.doc_mode:
    clr.AddReference("System.Core")
    clr.ImportExtensions(System.Linq)
    clr.AddReferenceByName('Rhino3dmIO')
    from Rhino import *
    rhg = Geometry
