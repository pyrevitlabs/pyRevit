import clr

from revitutils import doc

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, FilteredElementCollector, FilledRegionType

def make_filledregion(fillpattern_name, fillpattern_id):
    filledregion_types = FilteredElementCollector(doc).OfClass(clr.GetClrType(FilledRegionType))
    source_fr = filledregion_types.FirstElement()
    with Transaction(doc, 'Create Filled Region') as t:
        t.Start()
        new_fr = source_fr.Duplicate(fillpattern_name)
        new_fr.FillPatternId = fillpattern_id
        t.Commit()
