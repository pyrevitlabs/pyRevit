__doc__ = 'List all currently loaded assemblies'

from System import AppDomain

__window__.Width = 1500

userScriptsAssemblies = []
for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
	loc = ''
	if 'pyRevit' in loadedAssembly.FullName:
		userScriptsAssemblies.append( loadedAssembly )
		continue
	try:
		loc = loadedAssembly.Location
	except:
		pass
	print('{0}{1}{2}'.format(
		loadedAssembly.GetName().Name.ljust(50),
		str( loadedAssembly.GetName().Version ).ljust(20),
		loc,
		))

print('\n\n')
for loadedAssembly in userScriptsAssemblies:
	loc = ''
	try:
		loc = loadedAssembly.Location
	except:
		pass
	print('{0}{1}{2}'.format(
			loadedAssembly.GetName().Name.ljust(50),
			str( loadedAssembly.GetName().Version ).ljust(20),
			loc,
			))