import clr
import os.path as op

from pyrevit import EXEC_PARAMS
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import make_canonical_name
from pyrevit.loader import ASSEMBLY_FILE_TYPE

# noinspection PyUnresolvedReferences
import System


logger = get_logger(__name__)


RHINO_THREEDM = 'Rhino3dmIO'
EXTENSION_DIR = op.dirname(op.dirname(__file__))


def get_dll_file(addin_filename):
    addin_file = op.join(EXTENSION_DIR,
                         make_canonical_name(addin_filename,
                                             ASSEMBLY_FILE_TYPE))
    if op.exists(addin_file):
        return addin_file

    return None


if not EXEC_PARAMS.doc_mode:
    clr.AddReference("System.Core")
    clr.ImportExtensions(System.Linq)
    # clr.AddReferenceByName(RHINO_THREEDM)
    try:
        clr.AddReferenceToFileAndPath(get_dll_file(RHINO_THREEDM))
    except:
        logger.error('Can not load %s module.' % RHINO_THREEDM)

    from Rhino import *
    rhg = Geometry
