import clr

import System

clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference("System.Core")
clr.AddReference('System.Xml.Linq')
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('System.Drawing')
clr.AddReference('System.Management')
clr.AddReferenceByPartialName('WindowsBase')

clr.ImportExtensions(System.Linq)

from System import AppDomain, Version
from System.Diagnostics import Process
from System.Reflection import Assembly, AssemblyName
from System.Reflection import TypeAttributes, MethodAttributes
from System.Reflection import CallingConventions
from System.Reflection.Emit import AssemblyBuilderAccess
from System.Reflection.Emit import CustomAttributeBuilder, OpCodes

from System.IO import IOException, DriveInfo, Path, StringReader
from System.Net import WebClient, WebRequest

from System import Type
from System import Uri
from System import EventHandler

from System import DateTime, DateTimeOffset

from System import Array
from System.Collections.Generic import List, Dictionary

from System import Drawing
from System import Windows
from System.Windows import Forms
from System.Windows.Forms import Clipboard
from System.Windows import Controls
from System.Windows.Media import Imaging, SolidColorBrush, Color

from System.CodeDom import Compiler
from Microsoft.CSharp import CSharpCodeProvider

from System.Management import ManagementObjectSearcher

clr.AddReference('IronPython.Wpf')
import wpf
