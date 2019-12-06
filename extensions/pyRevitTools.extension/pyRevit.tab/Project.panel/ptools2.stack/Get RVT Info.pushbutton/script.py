"""Get information from a RVT file."""
#pylint: disable=E0401,C0103
from pyrevit import forms
from pyrevit.labs import TargetApps


__context__ = 'zero-doc'


rvt_file = forms.pick_file(files_filter='Revit Files |*.rvt;*.rte;*.rfa|'
                                        'Revit Model |*.rvt|'
                                        'Revit Template |*.rte|'
                                        'Revit Family |*.rfa')
if rvt_file:
    mfile = TargetApps.Revit.RevitModelFile(rvt_file)
    print("Created in: {0} ({1}({2}))".format(mfile.RevitProduct.Name,
                                              mfile.RevitProduct.BuildNumber,
                                              mfile.RevitProduct.BuildTarget))
    print("Workshared: {0}".format("Yes" if mfile.IsWorkshared else "No"))
    if mfile.IsWorkshared:
        print("Central Model Path: {0}".format(mfile.CentralModelPath))
    print("Last Saved Path: {0}".format(mfile.LastSavedPath))
    print("Document Id: {0}".format(mfile.UniqueId))
    print("Open Workset Settings: {0}".format(mfile.OpenWorksetConfig))
    print("Document Increment: {0}".format(mfile.DocumentIncrement))

    print("Project Information (Properties):")
    for k, v in sorted(dict(mfile.ProjectInfoProperties).items()):
        print('\t{} = {}'.format(k, v))

    if mfile.IsFamily:
        print("Model is a Revit Family!")
        print("Category Name: {0}".format(mfile.CategoryName))
        print("Host Category Name: {0}".format(mfile.HostCategoryName))
