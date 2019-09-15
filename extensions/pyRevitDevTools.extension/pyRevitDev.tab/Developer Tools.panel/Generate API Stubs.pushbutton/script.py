"""Generate python stubs for this Revit version API."""
#pylint: disable=import-error,invalid-name,broad-except
__title__ = 'Generate\nAPI Stubs'
__context__ = 'zero-doc'

from pyrevit.coreutils import assmutils
from pyrevit import labs
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


ASSMS = [
    'RevitAPI',
    'RevitAPIUI',
    # 'UIFramework',
    # 'Adwindows',
    'pyRevitLabs.Common',
    'pyRevitLabs.TargetApps.Revit',
    'pyRevitLabs.PyRevit',
]

dest_path = forms.pick_folder()

if dest_path:
    for assm_name in ASSMS:
        assm = assmutils.find_loaded_asm(assm_name)
        if assm:
            try:
                stubs_path = labs.PythonStubsBuilder.BuildAssemblyStubs(
                    assm[0].Location,
                    destPath=dest_path
                )
                print('Generated stubs for %s -> %s' % (assm_name, stubs_path))
            except Exception as sgEx:
                logger.error('Failed generating stubs for %s', assm_name)
