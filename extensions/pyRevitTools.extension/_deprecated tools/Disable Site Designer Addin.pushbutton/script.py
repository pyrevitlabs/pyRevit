import os
import os.path as op

from pyrevit import framework


__context__ = 'zerodoc'
__doc__ = 'Site Designer has a bug that duplicates its standard line styles.' \
          'This script will disable the Add-in.'


assmName = 'SiteDesigner'


def findassembly(assemblyname):
    """Finds the loaded assembly that contains assemblyname in name
    """
    alist = []
    for loadedAssembly in framework.AppDomain.CurrentDomain.GetAssemblies():
        if assemblyname in loadedAssembly.FullName:
            alist.append(loadedAssembly)
    return alist


def disableaddin(assemb):
    """Find the addin definition file location and append .bak to its name.
    This way Revit won;t be able to find it on next load.
    """
    assmloc = op.dirname(assemb.Location)
    files = os.listdir(assmloc)
    atleastonedisabled = False
    for f in files:
        if f.endswith('.addin'):
            fname = op.join(assmloc, f)
            newfname = op.join(assmloc, f.replace('.addin', '.addin.bak'))
            os.rename(fname, newfname)
            print('Addin description file renamed:\n{0}'.format(newfname))
            atleastonedisabled = True
    if atleastonedisabled:
        print('ADDIN SUCCESSFULLY DISABLED.')
    else:
        print('--- Disabling unsuccessful ---')


assmList = findassembly(assmName)

if len(assmList) > 1:
    print('Multiple assemblies found:'
          '\n{0}'
          '\n\nAttemping disabling all...'.format(assmList))
    for i, a in enumerate(assmList):
        print('\n\n{0}: {1}'.format(i, a.GetName().Name))
        if not a.IsDynamic:
            disableaddin(a)
        else:
            print('Can not disable dynamic assembly...')

elif len(assmList) == 1:
    assm = assmList[0]
    if not assm.IsDynamic:
        print('Assembly found:'
              '\n{0}'
              '\nAttemping disabling...'.format(assm.GetName().Name))
        disableaddin(assm)
    else:
        print('Can not disable dynamic assembly...')
else:
    print('Can not find addin: {0}'.format(assmName))
