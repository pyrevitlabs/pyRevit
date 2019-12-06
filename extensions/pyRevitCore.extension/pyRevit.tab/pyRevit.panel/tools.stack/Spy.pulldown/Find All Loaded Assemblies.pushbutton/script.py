"""List all currently loaded assemblies"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit.compat import safe_strtype
from pyrevit import framework
from pyrevit import script

__context__ = 'zero-doc'


output = script.get_output()

output.freeze()

userscript_assms = []
for loadedAssembly in framework.AppDomain.CurrentDomain.GetAssemblies():
    loc = ''
    if 'pyrevit' in safe_strtype(loadedAssembly.FullName).lower():
        userscript_assms.append(loadedAssembly)
        continue
    try:
        loc = loadedAssembly.Location
    except Exception:
        pass
    print('\n{0}{1}{2}'.format(loadedAssembly.GetName().Name.ljust(50),
                               str(loadedAssembly.GetName().Version).ljust(20),
                               loc))
    try:
        print('External Applications:')
        print([x.FullName
               for x in loadedAssembly.GetTypes()
               if x.GetInterface("IExternalApplication") is not None])
    except Exception:
        pass
    try:
        print('External Commands:')
        print([x.FullName
               for x in loadedAssembly.GetTypes()
               if x.GetInterface("IExternalCommand") is not None])
    except Exception:
        pass

print('\n\nPYREVIT ASSEMBLIES:')
for loadedAssembly in userscript_assms:
    loc = ''
    try:
        loc = loadedAssembly.Location
    except Exception:
        pass
    print('{0}{1}{2}'.format(loadedAssembly.GetName().Name.ljust(50),
                             str(loadedAssembly.GetName().Version).ljust(20),
                             loc))
    try:
        print('External Commands:')
        print([x.FullName
               for x in loadedAssembly.GetTypes()
               if x.GetInterface("IExternalCommand") is not None])
        print('\n')
    except Exception:
        pass

output.unfreeze()