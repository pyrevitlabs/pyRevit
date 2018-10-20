from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import script


__doc__ = 'This is a tool to swap line styles. Run the tool, '\
          'select a line with the style to be replaced, and then '\
          'select a line with the interfacetypes style. '\
          'The script will correct the line styles in the model. '\
          'HOWEVER the lines that are part of a group will not be affected. '\
          'Also see the "Shake Filled Regions" tool.'


logger = script.get_logger()


def get_styles():
    fromStyleLine = \
        revit.pick_element('Pick a line with the style to be replaced.')
    fromStyle = fromStyleLine.LineStyle

    toStyleLine = \
        revit.pick_element('Pick a line with the interfacetypes style.')

    toStyle = toStyleLine.LineStyle

    return fromStyle, toStyle


try:
    fromStyle, toStyle = get_styles()

    line_list = []

    elfilter = DB.ElementMulticategoryFilter(
                    List[DB.BuiltInCategory](
                        [DB.BuiltInCategory.OST_Lines,
                         DB.BuiltInCategory.OST_SketchLines]
                        )
                    )

    detail_lines = DB.FilteredElementCollector(revit.doc)\
                     .WherePasses(elfilter)\
                     .WhereElementIsNotElementType()\
                     .ToElements()

    for detail_line in detail_lines:
        if detail_line.LineStyle.Name == fromStyle.Name:
            line_list.append(detail_line)

    with revit.Transaction('Swap Line Styles'):
        for line in line_list:
            if line.Category.Name != '<Sketch>' \
                    and line.GroupId < DB.ElementId(0):
                line.LineStyle = toStyle
            elif line.Category.Name == '<Sketch>':
                line.LineStyle = toStyle
            elif line.GroupId > DB.ElementId(0):
                logger.debug('Skipping grouped line: {} in group {}'
                             .format(line.Id, line.GroupId))

except Exception as err:
    logger.error(err)
