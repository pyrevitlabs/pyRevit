__doc__ = 'Opens the central log for the current workshared project.'

import os
import os.path as op

from pyrevit.revit import DB, UI


if __activedoc__.GetWorksharingCentralModelPath():
    model_path = __activedoc__.GetWorksharingCentralModelPath()
    centralPath = \
        DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path)
    centralName = op.splitext(op.basename(centralPath))[0]
    slogFile = centralPath.replace('.rvt',
                                   '_backup\\{0}.slog'.format(centralName))
    pfFolder = os.getenv('ProgramFiles(x86)')
    nppExists = op.isfile(op.join(pfFolder, 'Notepad++\\Notepad++.EXE'))
    if nppExists:
        os.system('start notepad++ "{0}"'.format(slogFile))
    else:
        os.system('start notepad "{0}"'.format(slogFile))
else:
    UI.TaskDialog.Show('pyRevit', 'Model is not workshared.')
