import clr

from revitutils import doc, uidoc
from scriptutils import logger

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, FilteredElementCollector, BuiltInCategory, ElementId, DetailLine, \
                              ElementMulticategoryFilter, FilledRegion, XYZ, TransactionGroup
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI.Selection import ObjectType


__doc__ = 'This is a tool to swap line styles. Run the tool, select a line with the style to be replaced, and then ' \
          'select a line with the interfacetypes style. The script will correct the line styles in the model. '      \
          'HOWEVER the lines that are part of a group will not be affected. Also see the "Shake Filled Regions" tool.'


def get_styles():
    fromStyleLine = doc.GetElement(uidoc.Selection.PickObject(ObjectType.Element,
                                                              'Pick a line with the style to be replaced.'))
    fromStyle = fromStyleLine.LineStyle

    toStyleLine = doc.GetElement(uidoc.Selection.PickObject(ObjectType.Element,
                                                            'Pick a line with the interfacetypes style.'))
    toStyle = toStyleLine.LineStyle

    return fromStyle, toStyle


def shake_filled_regions():
    cl = FilteredElementCollector(doc)
    fregions = cl.OfClass(clr.GetClrType(FilledRegion)).WhereElementIsNotElementType().ToElements()

    for fr in fregions:
        fr.Location.Move(XYZ(0.01, 0, 0))
        fr.Location.Move(XYZ(-0.01, 0, 0))


try:
    fromStyle, toStyle = get_styles()

    line_list = []

    cl = FilteredElementCollector(doc)
    elfilter = ElementMulticategoryFilter(List[BuiltInCategory]([BuiltInCategory.OST_Lines, BuiltInCategory.OST_SketchLines]))
    detail_lines = cl.WherePasses(elfilter).WhereElementIsNotElementType().ToElements()

    for detail_line in detail_lines:
        if detail_line.LineStyle.Name == fromStyle.Name:
            line_list.append(detail_line)

    with Transaction(doc, 'Swap Line Styles') as t:
        t.Start()
        for line in line_list:
            if line.Category.Name != '<Sketch>' and line.GroupId < ElementId(0):
                line.LineStyle = toStyle
            elif line.Category.Name == '<Sketch>':
                line.LineStyle = toStyle
            elif line.GroupId > ElementId(0):
                logger.debug('Skipping grouped line: {} in group {}'.format(line.Id, line.GroupId))

        # shake_filled_regions()

        t.Commit()
except Exception as err:
    logger.error(err)
