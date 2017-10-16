import os.path as op
from pyrevit import EXEC_PARAMS, LOADER_DIR, ADDIN_DIR
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import loader


logger = get_logger(__name__)


def get_addin_dll_file(addin_filename):
    addin_file = \
        op.join(ADDIN_DIR,
                coreutils.make_canonical_name(addin_filename,
                                              loader.ASSEMBLY_FILE_TYPE))
    logger.debug('Dll requested: {}'.format(addin_file))
    if op.exists(addin_file):
        return addin_file
