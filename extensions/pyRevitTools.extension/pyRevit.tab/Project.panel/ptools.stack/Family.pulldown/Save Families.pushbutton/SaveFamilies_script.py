__doc__ = """Saves chosen families from the project"""
from pyrevit import revit, script, DB, forms
import os.path as op

logger = script.get_logger()

def get_families(doc):
    cl = DB.FilteredElementCollector(doc)
    families_types = set(cl.WhereElementIsElementType().ToElements())
    families = []
    for f in families_types:
        if type(f) == DB.FamilySymbol or type(f) == DB.AnnotationSymbolType:
            families.append(f.Family)

    return families


if __name__ == '__main__':
    doc = revit.doc
    
    fam_dict = {}
    for f in get_families(doc):
        if f.FamilyCategory:
            fam_dict["%s: %s" % (f.FamilyCategory.Name, f.Name)] = f
        
    fam_selected = forms.SelectFromList.show(sorted(fam_dict.keys()), title="Save famiiles", multiselect=True)
    if not fam_selected:
        script.exit()
    fam_selected = map(lambda f: fam_dict[f], fam_selected)
    if not fam_selected:
        script.exit()
    folder = forms.pick_folder()
    if not folder:
        script.exit()
    for fam in fam_selected:
        logger.info("Saving %s ..." % fam.Name)
        fam_doc = doc.EditFamily(fam)
        fam_doc.SaveAs(op.join(folder, fam.Name + ".rfa"))
        fam_doc.Close(False)