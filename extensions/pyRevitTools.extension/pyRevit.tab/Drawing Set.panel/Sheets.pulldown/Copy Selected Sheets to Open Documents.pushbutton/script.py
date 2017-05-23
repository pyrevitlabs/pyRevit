"""Copies selected or current sheet(s) to all projects currently open in Revit."""

import sys

from revitutils import doc as activedoc
from revitutils import uidoc, selection, curview, Action

from System.Collections.Generic import List

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog


class CopyUseDestination(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


def error_and_close(msg):
    TaskDialog.Show('pyrevit', msg)
    sys.exit(0)


def get_dest_docs():
    # find open documents other than the active doc
    open_docs = [d for d in __revit__.Application.Documents if not d.IsLinked]
    open_docs.remove(activedoc)
    if len(open_docs) < 1:
        error_and_close('Only one active document is found. ' \
                        'At least two documents must be open. ' \
                        'Operation cancelled.')
    return open_docs


def copy_sheet_view(activedoc, source_sheet, dest_doc):
    print('copy_sheet_view')

    t = Transaction(dest_doc, 'Create Sheet')
    t.Start()
    new_sheet = ViewSheet.Create(dest_doc, ElementId.InvalidElementId)
    new_sheet.Name = source_sheet.Name
    new_sheet.SheetNumber = source_sheet.SheetNumber
    t.Commit()

    return new_sheet


def copy_viewport_contents(activedoc, source_view, dest_doc, new_view):
    print('copy_sheet_contents')
    view_elements = FilteredElementCollector(activedoc, source_view.Id).ToElements()
    elements_ids_to_copy = []
    for element in view_elements:
        if isinstance(element, Viewport):
            continue
        else:
            elements_ids_to_copy.append(element.Id)

    options = CopyPasteOptions()
    options.SetDuplicateTypeNamesHandler(CopyUseDestination())

    t = Transaction(dest_doc, 'Copy Legends to this document')
    t.Start()
    copiedElement = ElementTransformUtils.CopyElements(source_view,
                                                       List[ElementId](elements_ids_to_copy),
                                                       new_view, None, options)
    t.Commit()


def copy_sheet_contents(*args):
    copy_viewport_contents(*args)


def copy_sheet_viewports(activedoc, source_sheet, dest_doc, new_sheet):
    print('copy_sheet_viewports')
    for vp in source_sheet.GetAllViewports():
        


for dest_doc in get_dest_docs():
    print('\nCopying Sheet to Document: {0}'.format(dest_doc.Title))
    sheets_to_be_copied = []
    if selection.is_empty and isinstance(curview, ViewSheet):
        sheets_to_be_copied.append(curview)
    else:
        sheets_to_be_copied = [x for x in selection if isinstance(x, ViewSheet)]

    if not sheets_to_be_copied:
        error_and_close('At least one sheet must be selection or be active.')

    for source_sheet in sheets_to_be_copied:
        new_sheet = copy_sheet_view(activedoc, source_sheet, dest_doc)
        copy_sheet_contents(activedoc, source_sheet, dest_doc, new_sheet)
        copy_sheet_viewports(activedoc, source_sheet, dest_doc, new_sheet)
