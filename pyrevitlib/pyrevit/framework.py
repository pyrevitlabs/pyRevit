"""Provide access to DotNet Framework.

Example:
    >>> from pyrevit.framework import Assembly, Windows
"""

#pylint: disable=W0703,C0302,C0103,W0614,E0401,W0611,C0413
import os.path as op

import clr
import System


clr.AddReference("System.Core")
clr.AddReference('System.Management')
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('System.Drawing')
clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference('System.Xml.Linq')
clr.AddReferenceByPartialName('WindowsBase')

# add linq extensions?
clr.ImportExtensions(System.Linq)

from System import AppDomain, Version
from System import Type
from System import Uri, Guid
from System import EventHandler
from System import Array, IntPtr, Enum
from System import Convert
from System.Text import Encoding
from System.Collections import IEnumerator, IEnumerable
from System.Collections.Generic import List, Dictionary
from System import DateTime, DateTimeOffset

from System import Diagnostics
from System.Diagnostics import Process
from System.Diagnostics import Stopwatch

from System import Reflection
from System.Reflection import Assembly, AssemblyName
from System.Reflection import TypeAttributes, MethodAttributes
from System.Reflection import CallingConventions
from System.Reflection import BindingFlags
from System.Reflection.Emit import AssemblyBuilderAccess
from System.Reflection.Emit import CustomAttributeBuilder, OpCodes

from System import IO
from System.IO import IOException, DriveInfo, Path, StringReader

from System import Net
from System.Net import WebClient, WebRequest, WebProxy

from System import ComponentModel
from System import Drawing
from System import Windows
from System.Windows import Forms
from System.Windows.Forms import Clipboard
from System.Windows import Controls
from System.Windows import Media
from System.Windows import Threading
from System.Windows import Interop
from System.Windows import Input
from System.Windows.Media import Imaging, SolidColorBrush, Color
from System import Math
from System.CodeDom import Compiler
from System.Management import ManagementObjectSearcher
from System.Runtime.Serialization import FormatterServices

from Microsoft.CSharp import CSharpCodeProvider

clr.AddReference('IronPython.Wpf')
import wpf


from pyrevit import BIN_DIR


def get_type(fw_object):
    """Return CLR type of an object.

    Args:
        fw_object: Dotnet Framework Object Instance
    """
    return clr.GetClrType(fw_object)


def get_dll_file(assembly_name):
    """Return path to given assembly name."""
    addin_file = op.join(BIN_DIR, assembly_name + '.dll')
    if op.exists(addin_file):
        return addin_file
