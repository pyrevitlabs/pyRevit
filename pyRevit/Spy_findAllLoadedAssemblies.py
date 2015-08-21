from System import AppDomain

userScriptsAssemblies = []
for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
	loc = ''
	if 'userScripts' in loadedAssembly.FullName:
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