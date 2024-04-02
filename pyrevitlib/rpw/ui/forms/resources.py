"""
Consolidate all imports and resources for other forms based classes to use.

"""  #

import sys

from abc import ABCMeta

import clr

import os.path as op
from pyrevit.compat import PY3, PY2
import pyrevit.engine as eng

# WPF/Form Imports
clr.AddReference("PresentationFramework")  # System.Windows: Controls, ?
clr.AddReference("WindowsBase")            # System.Windows.Input
clr.AddReference("System.Drawing")         # FontFamily
clr.AddReference('System.Windows.Forms') # Forms

import System.Windows
from System.Windows import Window
from System.IO import StringReader

# Console
from System.Environment import Exit, NewLine
from System.Drawing import FontFamily
from System.Windows.Input import Key

# FlexForm Imports
from System.Windows import Controls, Window
from System.Windows import HorizontalAlignment, VerticalAlignment, Thickness

# OS Dialogs
from System.Windows import Forms


ASSEMBLY_FILE_TYPE = 'dll'
ASSEMBLY_FILE_EXT = '.dll'

ipy_assmname = '{prefix}IronPython'.format(prefix=eng.EnginePrefix)
ipy_dllpath = op.join(eng.EnginePath, ipy_assmname + ASSEMBLY_FILE_EXT)
if PY3:
    clr.AddReference(ipy_dllpath)
else:
    clr.AddReferenceToFileAndPath(ipy_dllpath)

import IronPython

# WPF
wpf = None
wpf_assmname = '{prefix}IronPython.Wpf'.format(prefix=eng.EnginePrefix)
wpf_dllpath = op.join(eng.EnginePath, wpf_assmname + ASSEMBLY_FILE_EXT)
try:
    clr.AddReference(wpf_assmname)
    if PY3:
        wpf = IronPython.Modules.Wpf
    else:
        import wpf
except Exception:
    clr.AddReferenceToFileAndPath(wpf_dllpath)
    import wpf