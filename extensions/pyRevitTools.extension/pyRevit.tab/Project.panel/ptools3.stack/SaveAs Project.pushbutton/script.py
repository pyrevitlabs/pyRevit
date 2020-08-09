"""Save As Project
This tool uses the postable command to save your project with the SaveAs command
Copyright (c) 2020 Jean-Marc Couffin
https://github.com/jmcouffin
--------------------------------------------------------
pyRevit Notice:
Copyright (c) 2014-2020 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

__title__ = "SaveAs Project"
__author__ = 'Jean-Marc Couffin'
__contact__ = 'https://github.com/jmcouffin'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'Allows you to set the save as command as an icon and attribute a shortcut'

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
import Autodesk
from Autodesk.Revit.UI import RevitCommandId
from Autodesk.Revit.UI import UIApplication
from Autodesk.Revit.UI import ExternalCommandData
clr.AddReference('RevitServices')
import RevitServices
from RevitServices.Persistence import DocumentManager

uiapp = DocumentManager.Instance.CurrentUIApplication
CmndID = RevitCommandId.LookupCommandId('ID_REVIT_FILE_SAVE_AS')
CmId = CmndID.Id
uiapp.PostCommand(CmndID)