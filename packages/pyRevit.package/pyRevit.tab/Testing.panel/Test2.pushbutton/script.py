from pyrevit.logger import get_logger
logger = get_logger(__commandname__)

if __shiftclick__:
    print('Shif-Clicked button')

logger.critical('message')

# testing rpw ----------------------------------------------------------------------------------------------------------
import rpw
from rpw import doc, uidoc

print doc, uidoc

# from System import AppDomain as ad
#
# for a in ad.CurrentDomain.GetAssemblies():
#     if 'pyrevit' in str(a.FullName).lower():
#         print a

# # testing getting loaded assemblies ----------------------------------------------------------------------------------------------------------
# from System import AppDomain
# from System.Reflection import AssemblyName
# dom = AppDomain.CreateDomain("some")
# assemblyName = AssemblyName()
# assemblyName.CodeBase = r'C:\Users\eirannejad\Desktop\pyRevit\loader\pyRevitLoader\pyRevitClasses.dll'
# assembly = dom.Load(assemblyName)
# types = assembly.GetTypes()
# AppDomain.Unload(dom)
