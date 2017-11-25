from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import script


__context__ = 'selection'
__doc__ = 'Select all elements of the same type as selected element '\
          'and reports their IDs (sorted by the owner view if they '\
          'are View Specific objects)'


output = script.get_output()

selection = revit.get_selection()

if len(selection) > 0:
    firstEl = selection.first
    CID = firstEl.Category.Id
    TID = firstEl.GetTypeId()

    cl = DB.FilteredElementCollector(revit.doc)
    catlist = cl.OfCategoryId(CID).WhereElementIsNotElementType().ToElements()

    filteredlist = []
    modelItems = []
    vsItems = {}
    vsList = firstEl.ViewSpecific

    for r in catlist:
        if r.GetTypeId() == TID:
            filteredlist.append(r.Id)
            if vsList:
                ovname = revit.doc.GetElement(r.OwnerViewId).ViewName
                if ovname in vsItems:
                    vsItems[ovname].append(r)
                else:
                    vsItems[ovname] = [r]
            else:
                modelItems.append(r)

    if vsList:
        for ovname, items in vsItems.items():
            print('OWNER VIEW: {0}'.format(ovname))
            for r in items:
                print('\tID: {0}\t{1}'.format(output.linkify(r.Id),
                                              r.GetType().Name.ljust(20)
                                              ))
            print('\n')
    else:
        print('SELECTING MODEL ITEMS:')
        for el in modelItems:
            print('\tID: {0}\t{1}'.format(output.linkify(r.Id),
                                          r.GetType().Name.ljust(20)
                                          ))

    revit.get_selection().set_to(filteredlist)
else:
    UI.TaskDialog.Show('pyrevit', 'At least one object must be selected.')
