"""MathNet importer module.

See https://www.mathdotnet.com for documentation.

Examples:
    ```python
    from pyrevit.coreutils.mathnet import MathNet
    ```
"""
#pylint: disable=W0703,C0302,C0103
from pyrevit import framework
from pyrevit.framework import clr
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)


MATHNET_LIB = 'MathNet.Numerics'

mathnet_dll = framework.get_dll_file(MATHNET_LIB)
mlogger.debug('Loading dll: %s', mathnet_dll)
try:
    clr.AddReferenceToFileAndPath(mathnet_dll)
    import MathNet  #pylint: disable=E0401,W0611
except Exception as load_err:
    mlogger.error('Can not load %s module. | %s', MATHNET_LIB, load_err)
