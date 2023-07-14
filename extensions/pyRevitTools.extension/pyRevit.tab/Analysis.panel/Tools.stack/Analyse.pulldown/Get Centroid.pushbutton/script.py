from __future__ import print_function
from pyrevit import script, revit, DB
from Autodesk.Revit.Exceptions import InvalidOperationException

doc = revit.doc
uidoc = revit.uidoc

logger = script.get_logger()
output = script.get_output()


def merge_solids(solids):
    """Merges the provided list of solids into a single unified solid

    Args:
        solids (list(DB.Solid)): The solids to merge

    Raises:
        ValueError: If the input is an empty list

    Returns:
        DB.Solid: The union of the solids
    """
    union = None
    if not solids:
        raise ValueError('List of provided solids was empty.')
    for solid in solids:
        if not union:
            union = solid
        else:
            try:
                union = DB.BooleanOperationsUtils.ExecuteBooleanOperation(
                    union,
                    solid,
                    DB.BooleanOperationsType.Union
                )
            except InvalidOperationException:
                ref = solid.Faces[0].Reference.ConvertToStableRepresentation(doc)
                uid = ref.split(':')[0]
                e = doc.GetElement(uid)
                logger.error(
                    'Failed to merge solid from element {}, '
                    'it will be excluded from the calculation'.format(
                        revit.ElementWrapper(e).name
                    )
                )
    return union


selection = revit.get_selection()
if not selection:
    forms.alert('You must select one element.', exitscript=True)
logger.debug('selection: {}'.format(selection))

extracted_solids = []

for element in selection:
    logger.debug('processing {}'.format(element.Name))
    extracted_solids.extend([
        g for g in revit.query.get_geometry(element, compute_references=True)
        if isinstance(g, DB.Solid) and g.Faces.Size > 0
    ])

logger.debug('extracted_solids: {}'.format(extracted_solids))

merged_solid = merge_solids(extracted_solids)
logger.debug('merged_solid: {}'.format(merged_solid))

centroid = merged_solid.ComputeCentroid()
logger.debug('centroid: {}'.format(centroid))

with revit.Transaction('Get Centroid'):
    sp1 = DB.SketchPlane.Create(
        doc,
        DB.Plane.CreateByNormalAndOrigin(
            DB.XYZ.BasisZ,
            centroid
        )
    )
    sp2 = DB.SketchPlane.Create(
        doc,
        DB.Plane.CreateByNormalAndOrigin(
            DB.XYZ.BasisY,
            centroid
        )
    )
    c1 = DB.Line.CreateBound(
        centroid - DB.XYZ.BasisX,
        centroid + DB.XYZ.BasisX
    )
    c2 = DB.Line.CreateBound(
        centroid - DB.XYZ.BasisY,
        centroid + DB.XYZ.BasisY
    )
    c3 = DB.Line.CreateBound(
        centroid - DB.XYZ.BasisZ,
        centroid + DB.XYZ.BasisZ
    )

    doc.Create.NewModelCurve(
        c1, sp1
    )
    doc.Create.NewModelCurve(
        c2, sp1
    )
    doc.Create.NewModelCurve(
        c3, sp2
    )
