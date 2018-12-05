"""MathNet importer module.

See https://www.mathdotnet.com for documentation.
"""

from pyrevit import EXEC_PARAMS
from pyrevit.framework import clr
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader.addin import get_addin_dll_file


logger = get_logger(__name__)


MATHNET_LIB = 'MathNet.Numerics'

if not EXEC_PARAMS.doc_mode:
    mathnet_dll = get_addin_dll_file(MATHNET_LIB)
    logger.debug('Loading dll: {}'.format(mathnet_dll))
    try:
        clr.AddReferenceToFileAndPath(mathnet_dll)
        import MathNet
    except Exception as load_err:
        logger.error('Can not load {} module. | {}'
                     .format(MATHNET_LIB, load_err))
