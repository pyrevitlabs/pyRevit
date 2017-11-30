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
from System import Array, IntPtr
from System.Collections import IEnumerator, IEnumerable
from System.Collections.Generic import List, Dictionary
from System import DateTime, DateTimeOffset

from System import Diagnostics
from System.Diagnostics import Process

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
from System.Net import WebClient, WebRequest

from System import Drawing
from System import Windows
from System.Windows import Forms
from System.Windows.Forms import Clipboard
from System.Windows import Controls
from System.Windows import Media
from System.Windows import Threading
from System.Windows import Interop
from System.Windows.Media import Imaging, SolidColorBrush, Color

from System import Math

from System.CodeDom import Compiler
from Microsoft.CSharp import CSharpCodeProvider

from System.Management import ManagementObjectSearcher

from System.Runtime.Serialization import FormatterServices

clr.AddReference('IronPython.Wpf')
import wpf


def get_type(fw_object):
    return clr.GetClrType(fw_object)
