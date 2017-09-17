import clr

import System

clr.AddReference('PresentationCore')
clr.AddReference("System.Core")
clr.AddReference('System.Xml.Linq')
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('System.Drawing')

clr.ImportExtensions(System.Linq)

from System import AppDomain, Version
from System.Diagnostics import Process
from System.Reflection import Assembly, AssemblyName
from System.Reflection import TypeAttributes, MethodAttributes
from System.Reflection import CallingConventions
from System.Reflection.Emit import AssemblyBuilderAccess
from System.Reflection.Emit import CustomAttributeBuilder, OpCodes

from System.IO import IOException, DriveInfo, Path
from System.Net import WebClient, WebRequest

from System import Type, Uri, Array
from System import DateTime, DateTimeOffset
from System.Collections.Generic import List, Dictionary

import System.Drawing as Drawing
import System.Windows as Windows
import System.Windows.Forms as Forms
import System.Windows.Media.Imaging as Imaging

from System.CodeDom import Compiler
from Microsoft.CSharp import CSharpCodeProvider
