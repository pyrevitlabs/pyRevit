"""
Consolidate all imports and resources for other forms based classes to use.

"""  #

import sys

from abc import ABCMeta

from rpw import revit
from rpw.utils.dotnet import clr
from rpw.utils.logger import logger

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

if revit.host == 'Dynamo':
    # IronPython 2.7.3 - Dynamo + RPS w/out pyRevit
    # Conflicts with PyRevit. Must Ensure exact path is specified
    # https://github.com/architecture-building-systems/revitpythonshell/issues/46
    clr.AddReferenceToFileAndPath(r'C:\Program Files (x86)\IronPython 2.7\Platforms\Net40\IronPython.Wpf.dll')
    import wpf
    # on 2.7.7 this raises wpf import error
else:
    # IronPython 2.7.7 - pyRevit
    # clr.AddReference('IronPython')    # Works W/Out
    clr.AddReference('IronPython.Wpf')  # 2.7.
    from IronPython.Modules import Wpf as wpf
    # on 2.7.7 this works. On 2.7.3 you get a LoadComponent 3 args error
