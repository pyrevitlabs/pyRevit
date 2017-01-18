"""Lists views that have not been references by any other view."""


from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View, ViewType


__window__.Width = 1200

view_ref_prefixes = {ViewType.CeilingPlan: 'Reflected Ceiling Plan: ',
                     ViewType.FloorPlan: 'Floor Plan: ',
                     ViewType.EngineeringPlan: 'Structural Plan: ',
                     ViewType.DraftingView: 'Drafting View: '}

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


def find_unrefed_views(view_list):
    for v in view_list:
        phasep = v.LookupParameter('Phase')
        sheetnum = v.LookupParameter('Sheet Number')
        detnum = v.LookupParameter('Detail Number')
        refsheet = v.LookupParameter('Referencing Sheet')
        refviewport = v.LookupParameter('Referencing Detail')
        if refsheet and refviewport \
           and refsheet.AsString() != '' and refviewport.AsString() != '' \
           or (view_ref_prefixes[v.ViewType] + v.ViewName) in view_refs_names:
            continue
        else:
            print('-'*20)
            print('NAME: {0}\nTYPE: {1}\nID: {2}\nPLACED ON DETAIL/SHEET: {4} / {3}'.format(
                v.ViewName,
                str(v.ViewType).ljust(20),
                str(v.Id).ljust(10),
                sheetnum.AsString() if sheetnum else '-',
                detnum.AsString() if detnum else '-',
            ))


views = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
view_refs = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ReferenceViewer).WhereElementIsNotElementType().ToElements()

view_refs_names = set()
for view_ref in view_refs:
    ref_param = view_ref.LookupParameter('Target view')
    view_refs_names.add(ref_param.AsValueString())

dviews = []
mviews = []

for v in views:
    if not v.IsTemplate:
        if v.ViewType == ViewType.DraftingView:
            dviews.append(v)
        else:
            mviews.append(v)

print('UNREFERENCED DRAFTING VIEWS'.ljust(100, '-'))
find_unrefed_views(dviews)
print('\n\n\n' + 'UNREFERENCED MODEL VIEWS'.ljust(100, '-'))
find_unrefed_views(mviews)
