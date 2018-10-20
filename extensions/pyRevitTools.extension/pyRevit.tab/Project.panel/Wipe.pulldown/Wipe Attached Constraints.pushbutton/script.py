from pyrevit import revit, DB


__doc__ = 'Deletes all view parameter filters that has not been listed '\
          'on any views. This includes sheets as well.'


selection = revit.get_selection()

delConst = True

clconst = DB.FilteredElementCollector(revit.doc)\
            .OfCategory(DB.BuiltInCategory.OST_Constraints)\
            .WhereElementIsNotElementType()

constlst = set()


def listConsts(el, clconst):
    print('THIS OBJECT ID: {0}'.format(el.Id))
    for cnst in clconst:
        refs = [(x.ElementId, x) for x in cnst.References]
        elids = [x[0] for x in refs]
        if el.Id in elids:
            constlst.add(cnst)
            print("CONST TYPE: {0} # OF REFs: {1} CONST ID: {2}"
                  .format(cnst.GetType().Name.ljust(28),
                          str(cnst.References.Size).ljust(24),
                          cnst.Id))

            for t in refs:
                ref = t[1]
                elid = t[0]
                if elid == el.Id:
                    elid = str(elid) + ' (this)'

                elmnt = revit.doc.GetElement(ref.ElementId)
                print("     {0} LINKED OBJ CATEGORY: {1} ID: {2}"
                      .format(ref.ElementReferenceType.ToString().ljust(35),
                              elmnt.Category.Name.ljust(20),
                              elid))
            print('\n')
    print('\n')


for el in selection:
    listConsts(el, clconst)

if delConst:
    if constlst:
        with revit.Transaction('Remove associated constraints'):
            for cnst in constlst:
                try:
                    print("REMOVING CONST TYPE: {0} "
                          "# OF REFs: {1} "
                          "CONST ID: {2}"
                          .format(cnst.GetType().Name.ljust(28),
                                  str(cnst.References.Size).ljust(24),
                                  cnst.Id))

                    revit.doc.Delete(cnst.Id)
                    print('CONST REMOVED')
                except Exception:
                    print('FAILED')
                    continue
    else:
        print('NO CONSTRAINTS FOUND.')
