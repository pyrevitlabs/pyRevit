"""Wrapper module for pyRevitLabs functionality."""
import os.path as op
#pylint: disable=W0703,C0302,C0103,W0614,E0401,W0611,C0413
#pylint: disable=superfluous-parens,useless-import-alias
from pyrevit import HOST_APP
from pyrevit.framework import clr
from pyrevit.compat import PY2
from pyrevit._perf import mark as _perfmark
_perfmark("pyrevit.labs:entry")

# try loading pyrevitlabs
clr.AddReference('Nett')
clr.AddReference('MadMilkman.Ini')
clr.AddReference('OpenMcdf')
clr.AddReference('YamlDotNet')
clr.AddReference('pyRevitLabs.NLog')
clr.AddReference('pyRevitLabs.MahAppsMetro')
# roslyn csharp compiler dependencies are referenced by
# pyRevitLabs.Common thus loading ahead
clr.AddReference('System.Threading.Tasks.Extensions')
clr.AddReference('System.Collections.Immutable')
clr.AddReference('System.Numerics.Vectors')
clr.AddReference('System.Text.Encoding.CodePages')
# Revit, and its builtin addons, ship multiple versions of this assembly
# let's make sure our specific version is loaded
clr.AddReference('System.Runtime.CompilerServices.Unsafe')
clr.AddReference('System.Memory')
# clr.AddReference('System.Memory')
clr.AddReference('System.Reflection.Metadata')
clr.AddReference('Microsoft.CodeAnalysis')
clr.AddReference('Microsoft.CodeAnalysis.CSharp')
# and now
clr.AddReference('pyRevitLabs.Common')
clr.AddReference('pyRevitLabs.CommonCLI')
clr.AddReference('pyRevitLabs.CommonWPF')
clr.AddReference('pyRevitLabs.Emojis')
clr.AddReference('pyRevitLabs.Language')
clr.AddReference('pyRevitLabs.DeffrelDB')
clr.AddReference('pyRevitLabs.TargetApps.Revit')
clr.AddReference('pyRevitLabs.PyRevit')
clr.AddReference('PythonStubsBuilder')
_perfmark("pyrevit.labs:after clr.AddReference block (14 pyRevitLabs DLLs)")
import Nett
import MadMilkman.Ini
import OpenMcdf
import YamlDotNet as libyaml
import pyRevitLabs.MahAppsMetro
from pyRevitLabs import NLog
from pyRevitLabs import Common
from pyRevitLabs import CommonCLI
from pyRevitLabs import CommonWPF
from pyRevitLabs import Emojis
from pyRevitLabs import Language
from pyRevitLabs import DeffrelDB
from pyRevitLabs import TargetApps
from pyRevitLabs import PyRevit
from PythonStubs import PythonStubsBuilder
_perfmark("pyrevit.labs:after `from pyRevitLabs import` block")

from pyrevit import coreutils
from pyrevit.coreutils import logger


mlogger = logger.get_logger(__name__)


def extract_build_from_exe(proc_path):
    """Extract build number from host .exe file.

    Args:
        proc_path (str): full path of the host .exe file

    Returns:
        (str): build number (e.g. '20170927_1515(x64)')
    """
    # Revit 2021 has a bug on .VersionBuild
    ## it reports identical value as .VersionNumber
    pinfo = TargetApps.Revit.RevitProductData.GetBinaryProductInfo(proc_path)
    return "{}({})".format(pinfo.build, pinfo.target) \
        if pinfo.build else "20000101_0000(x64)"


# activate binding resolver
if HOST_APP.is_older_than(2019):
    PyRevit.PyRevitBindings.ActivateResolver()

# NLog output is configured by PyRevitLabs.PyRevit.Runtime.ScriptOutput.

_perfmark("pyrevit.labs:exit")
