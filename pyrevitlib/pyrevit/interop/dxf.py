"""IxMIlia.Dxf assembly import."""
# pylint: skip-file
import os.path as op
from pyrevit import BIN_DIR
from pyrevit import framework

framework.add_reference_to_file(
    op.join(BIN_DIR, 'IxMilia.Dxf')
    )

from IxMilia import Dxf
