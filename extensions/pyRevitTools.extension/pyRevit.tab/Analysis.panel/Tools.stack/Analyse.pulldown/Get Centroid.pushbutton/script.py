from __future__ import print_function
from pyrevit import script, revit, DB, forms, EXEC_PARAMS
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

cfg = script.get_config()
logger.debug('loaded config {}'.format(cfg))
line_category = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
line_subcategories = line_category.SubCategories
line_styles = [
    lsc.GetGraphicsStyle(DB.GraphicsStyleType.Projection)
    for lsc in line_subcategories
]
line_styles.sort(key=lambda x: x.Name)
logger.debug('got linestyles: {}'.format([ls.Name for ls in line_styles]))
try:
    logger.debug('searching for line style {}'.format(cfg.line_style))
    line_style = next(
        (ls for ls in line_styles if ls.Name == cfg.line_style),
        None
    )
    logger.debug('line style found')
except AttributeError:
    logger.debug('no line style in config')
    line_style = None
if EXEC_PARAMS.config_mode:
    line_style = forms.SelectFromList.show(
        line_styles,
        name_attr='Name',
        title='Select Line Style to be used'
    )
    if line_style:
        cfg.line_style = line_style.Name
        script.save_config()
        logger.debug('saved selected line style to config')

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

    l1 = doc.Create.NewModelCurve(
        c1, sp1
    )
    l2 = doc.Create.NewModelCurve(
        c2, sp1
    )
    l3 = doc.Create.NewModelCurve(
        c3, sp2
    )

    if line_style:
        for l in [l1, l2, l3]:
            l.LineStyle = line_style
