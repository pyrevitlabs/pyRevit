"""Find all constraints attached to the selected element."""

from pyrevit import revit, DB


__context__ = 'selection'


def listconstraints(selected_el):
    print('THIS OBJECT ID: {0}'.format(selected_el.Id))
    clconst = DB.FilteredElementCollector(revit.doc)\
                .OfCategory(DB.BuiltInCategory.OST_Constraints)\
                .WhereElementIsNotElementType()
    constlst = set()
    for cnst in clconst:
        refs = [(x.ElementId, x) for x in cnst.References]
        elids = [x[0] for x in refs]
        if selected_el.Id in elids:
            constlst.add(cnst)
            print('CONST TYPE: {0} # OF REFs: {1} CONST ID: {2}'
                  .format(cnst.GetType().Name.ljust(28),
                          str(cnst.References.Size).ljust(24),
                          cnst.Id))
            for t in refs:
                ref = t[1]
                elid = t[0]
                if elid == selected_el.Id:
                    elid = str(elid) + ' (this)'

                el = revit.doc.GetElement(ref.ElementId)

                print('     {0} LINKED OBJ CATEGORY: {1} ID: {2}'
                      .format(ref.ElementReferenceType.ToString().ljust(35),
                              el.Category.Name.ljust(20),
                              elid))
            print('\n')
    print('\n')


selection = revit.get_selection()
for el in selection.elements:
    listconstraints(el)
