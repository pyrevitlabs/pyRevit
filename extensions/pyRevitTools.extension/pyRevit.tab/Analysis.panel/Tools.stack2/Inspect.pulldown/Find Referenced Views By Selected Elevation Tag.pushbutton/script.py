"""Lists all the views referenced by the selected elevation tag."""

from pyrevit import revit, DB


__context__ = 'selection'


el = revit.get_selection().first

if isinstance(el, DB.ElevationMarker):
    cvc = el.CurrentViewCount

    for i in range(0, cvc):
        v = revit.doc.GetElement(el.GetViewId(i))
        if v:
            print('DETAIL #: {4}\tTYPE: {1}ID: {2}TEMPLATE: {3}  {0}'
                  .format(revit.query.get_name(v).ljust(100),
                          str(v.ViewType).ljust(15),
                          str(v.Id).ljust(10),
                          str(v.IsTemplate).ljust(10),
                          v.Parameter[DB.BuiltInParameter.VIEWER_DETAIL_NUMBER].AsString()))
