#! python3
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import EXEC_PARAMS
from pyrevit import revit, UI


print(EXEC_PARAMS.exec_id)


class CategoriesFilter(UI.Selection.ISelectionFilter):
    __namespace__ = EXEC_PARAMS.exec_id

    def __init__(self, names):
        self.names = names

    def AllowElement(self, element):
        return element.Category.Name in self.names

    def AllowReference(self, refer, point):
        return False


def select_objects_by_category(*names):
    references = \
        revit.uidoc.Selection.PickObjects(
            UI.Selection.ObjectType.Element,
            CategoriesFilter(names),
            'Pick {}'.format(', '.join(names))
            )
    return [revit.doc.GetElement(reference) for reference in references]


def select_objects():
    references = \
        revit.uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element)
    return [revit.doc.GetElement(reference) for reference in references]


def main():
    # rebars = select_objects()
    rebars = select_objects_by_category('Walls')
    print(rebars)


main()
