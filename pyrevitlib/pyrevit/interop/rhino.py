"""Rhinoceros interop."""
# pylint: skip-file
import os.path as op
from pyrevit import clr, BIN_DIR

clr.AddReferenceToFileAndPath(
    op.join(BIN_DIR, 'Rhino3dmIO')
    )

import Rhino
