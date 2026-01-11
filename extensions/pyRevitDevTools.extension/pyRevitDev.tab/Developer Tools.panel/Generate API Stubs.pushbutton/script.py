"""Generate python stubs for this Revit version API."""
#pylint: disable=import-error,invalid-name,broad-except
__title__ = 'Generate\nAPI Stubs'
__context__ = 'zero-doc'

from pyrevit.coreutils import assmutils
from pyrevit import labs
from pyrevit import forms
from pyrevit import script
from rpw.ui.forms.flexform import FlexForm, Label, Button, CheckBox


logger = script.get_logger()
output = script.get_output()

RVT_ASSMS = [
    'RevitAPI',
    'RevitAPIUI'
]
DYN_ASSMS = [
    'DynamoServices',
    'DynamoCore',
    'DynamoApplications',
    'DSCoreNodes',
    'RevitServices',
    'RevitNodes',
    # 'ProtoGeometry',
    # 'UIFramework',
    # 'Adwindows',
]
PYR_ASSMS = [
    'pyRevitLabs.Common',
    'pyRevitLabs.TargetApps.Revit',
    'pyRevitLabs.PyRevit'
]

def flexform_select():
    components = [
        Label('Select Assembly Group to Generate Stubs:'),
        CheckBox('Revit', 'Revit Assemblies', default=True),
        CheckBox('Dynamo', 'Dynamo Assemblies', default=False),
        CheckBox('pyRevit', 'pyRevit Assemblies', default=False),
        Button('Pick Destination Folder and Continue'),
    ]
    form = FlexForm('Generate API Stubs', components)
    form.show()
    selected = []
    if form.values.get('Revit'):
        selected.extend(RVT_ASSMS)
    if form.values.get('Dynamo'):
        selected.extend(DYN_ASSMS)
    if form.values.get('pyRevit'):
        selected.extend(PYR_ASSMS)
    return selected

ASSMS = flexform_select()
if not ASSMS:
    print("No assembly group selected. Exiting...")
    script.exit()

dest_path = forms.pick_folder()

if dest_path:
    for assm_name in ASSMS:
        print('Processing assembly: {}'.format(assm_name))
        try:
            load_assm = assmutils.load_asm(assm_name)
            print('Loaded assembly: {}'.format(assm_name))
        except Exception as ldEx:
            print('Error loading assembly {} | {}'.format(assm_name, ldEx))
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

