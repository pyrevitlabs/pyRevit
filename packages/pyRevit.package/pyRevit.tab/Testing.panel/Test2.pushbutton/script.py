__context__ = 'Walls'

if __shiftclick__:
    print('Shif-Clicked button')

import pyrevit.scriptutils as su
script = su.get_script_info(__file__)
print script.cmd_context


from System import AppDomain as ad
for a in ad.CurrentDomain.GetAssemblies():
	if 'pyrevit' in str(a.FullName).lower():
		print a


# from System import AppDomain
# from System.Reflection import AssemblyName
# dom = AppDomain.CreateDomain("some")
# assemblyName = AssemblyName()
# assemblyName.CodeBase = r'C:\Users\eirannejad\Desktop\pyRevit\loader\pyRevitLoader\pyRevitClasses.dll'
# assembly = dom.Load(assemblyName)
# types = assembly.GetTypes()
# AppDomain.Unload(dom)

raise Exception('Test')
