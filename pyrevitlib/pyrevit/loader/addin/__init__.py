import os.path as op
from pyrevit import EXEC_PARAMS, LOADER_DIR, ADDIN_DIR, PYREVITLOADER_DIR
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import loader


logger = get_logger(__name__)


LATEST_PYREVITLOADER = '277'
DYNAMOCOMPAT_PYREVITLOADER = '273'


def _get_pyrevitloader_dll(addin_filename):
    # finding dlls in specific PyRevitLoader directory
    addin_file = \
        op.join(PYREVITLOADER_DIR,
                coreutils.make_canonical_name(addin_filename,
                                              loader.ASSEMBLY_FILE_TYPE))
    logger.debug('Dll requested: {}'.format(addin_file))
    if op.exists(addin_file):
        return addin_file


def _get_addin_dll(addin_filename):
    # finding dlls in addins directory
    addin_file = \
        op.join(ADDIN_DIR,
                coreutils.make_canonical_name(addin_filename,
                                              loader.ASSEMBLY_FILE_TYPE))
    logger.debug('Dll requested: {}'.format(addin_file))
    if op.exists(addin_file):
        return addin_file


def get_addin_dll_file(addin_filename):
    addin_file = _get_addin_dll(addin_filename)
    if not addin_file:
        addin_file = _get_pyrevitloader_dll(addin_filename)

    return addin_file
