from pyrevit import revit, DB
from pyrevit import script


__doc__ = 'List all views that have been placed on a sheet '\
          'but are not referenced by any other views.'

output = script.get_output()


view_ref_prefixes = {DB.ViewType.CeilingPlan: 'Reflected Ceiling Plan: ',
                     DB.ViewType.FloorPlan: 'Floor Plan: ',
                     DB.ViewType.EngineeringPlan: 'Structural Plan: ',
                     DB.ViewType.DraftingView: 'Drafting View: '}


def find_sheeted_unrefed_views(view_list):
    for v in view_list:
        sheetnum = v.LookupParameter('Sheet Number')
        detnum = v.LookupParameter('Detail Number')
        refsheet = v.LookupParameter('Referencing Sheet')
        refviewport = v.LookupParameter('Referencing Detail')
        # is the view placed on a sheet?
        if sheetnum \
                and detnum \
                and ('-' not in sheetnum.AsString()) \
                and ('-' not in detnum.AsString()):
            # is the view referenced by at least one other view?
            if refsheet \
                    and refviewport \
                    and refsheet.AsString() != '' \
                    and refviewport.AsString() != '' \
                    or (v.ViewType in view_ref_prefixes
                        and (view_ref_prefixes[v.ViewType] + v.ViewName))\
                    in view_refs_names:
                continue
            else:
                # print the view sheet and det number
                print('-'*20)
                print('NAME: {0}\nDET/SHEET: {1}\nID: {2}'
                      .format(v.ViewName,
                              unicode(detnum.AsString()
                                      + '/'
                                      + sheetnum.AsString()),
                              output.linkify(v.Id)
                              )
                      )


views = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Views)\
          .WhereElementIsNotElementType()\
          .ToElements()

view_refs = DB.FilteredElementCollector(revit.doc)\
              .OfCategory(DB.BuiltInCategory.OST_ReferenceViewer)\
              .WhereElementIsNotElementType()\
              .ToElements()

view_refs_names = set()
for view_ref in view_refs:
    ref_param = view_ref.LookupParameter('Target view')
    view_refs_names.add(ref_param.AsValueString())

dviews = []
mviews = []

# separating model view and drafting view from the full view list
for v in views:
    if not v.IsTemplate:
        if v.ViewType == DB.ViewType.DraftingView:
            dviews.append(v)
        else:
            mviews.append(v)

print('DRAFTING VIEWS NOT ON ANY SHEETS' + '-' * 80)
find_sheeted_unrefed_views(dviews)
print('\n\n\n' + 'MODEL VIEWS NOT ON ANY SHEETS' + '-' * 80)
find_sheeted_unrefed_views(mviews)
