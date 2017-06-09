import clr
import os.path as op

from rpw import DOC_MODE, ASSEMBLY_FILE_TYPE
from rpw import get_logger
from rpw.utils import make_canonical_name

# noinspection PyUnresolvedReferences
import System


logger = get_logger(__name__)


RHINO_THREEDM = 'Rhino3dmIO'
EXTENSION_DIR = op.dirname(__file__)


def get_dll_file(addin_filename):
    addin_file = op.join(EXTENSION_DIR,
                         make_canonical_name(addin_filename,
                                             ASSEMBLY_FILE_TYPE))
    if op.exists(addin_file):
        return addin_file

    return None


if not DOC_MODE:
    clr.AddReference("System.Core")
    clr.ImportExtensions(System.Linq)
    # clr.AddReferenceByName(RHINO_THREEDM)
    try:
        clr.AddReferenceToFileAndPath(get_dll_file(RHINO_THREEDM))
    except:
        logger.error('Can not load %s module.' % RHINO_THREEDM)

    from Rhino import *
