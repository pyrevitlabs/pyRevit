"""Find all constraints attached to the selected element."""

from revitutils import doc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory


def listconstraints(selelement):
    print('THIS OBJECT ID: {0}'.format(selelement.Id))
    clconst = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Constraints).WhereElementIsNotElementType()
    constlst = set()
    for cnst in clconst:
        refs = [(x.ElementId, x) for x in cnst.References]
        elids = [x[0] for x in refs]
        if selelement.Id in elids:
            constlst.add(cnst)
            print("CONST TYPE: {0} # OF REFs: {1} CONST ID: {2}".format(cnst.GetType().Name.ljust(28),
                                                                        str(cnst.References.Size).ljust(24), cnst.Id))
            for t in refs:
                ref = t[1]
                elid = t[0]
                if elid == selelement.Id:
                    elid = str(elid) + ' (this)'
                print("     {0} LINKED OBJ CATEGORY: {1} ID: {2}".format(ref.ElementReferenceType.ToString().ljust(35),
                                                                         doc.GetElement(
                                                                             ref.ElementId).Category.Name.ljust(20),
                                                                         elid))
            print('\n')
    print('\n')


for el in selection.elements:
    listconstraints(el)
