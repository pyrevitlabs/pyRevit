import sys

from scriptutils import logger, this_script
from revitutils import doc as activedoc
from revitutils import uidoc, selection, curview, Action

from System.Collections.Generic import List

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog


__doc__ = 'Copies selected or current sheet(s) to all ' \
          'projects currently open in Revit.'


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


def get_source_sheets():
    sheets_to_be_copied = []
    if selection.is_empty and isinstance(curview, ViewSheet):
        sheets_to_be_copied.append(curview)
    else:
        sheets_to_be_copied = [x for x in selection if isinstance(x, ViewSheet)]

    if not sheets_to_be_copied:
        error_and_close('At least one sheet must be selection or be active.')

    return sheets_to_be_copied


def get_default_type(source_doc, type_group):
    return source_doc.GetDefaultElementTypeId(type_group)


def find_first_legend(dest_doc):
    for v in FilteredElementCollector(dest_doc).OfClass(View):
        if v.ViewType == ViewType.Legend:
            return v
    return None


def find_matching_view(dest_doc, source_view):
    for v in FilteredElementCollector(dest_doc).OfClass(View):
        if v.ViewType == source_view.ViewType \
            and v.ViewName == source_view.ViewName:
            return v
    return None


def copy_view_contents(activedoc, source_view, dest_doc, dest_view):
    logger.debug('Copying view contents: {}'.format(source_view.Name))
    view_elements = \
        FilteredElementCollector(activedoc, source_view.Id).WhereElementIsNotElementType().ToElements()
    elements_ids = []
    for element in view_elements:
        if isinstance(element, Viewport) \
            or 'ExtentElem' in element.Name:
            continue
        else:
            elements_ids.append(element.Id)

    options = CopyPasteOptions()
    options.SetDuplicateTypeNamesHandler(CopyUseDestination())

    if elements_ids:
        t = Transaction(dest_doc, 'Copy View Contents')
        t.Start()
        copiedElement = \
            ElementTransformUtils.CopyElements(source_view,
                                               List[ElementId](elements_ids),
                                               dest_view, None, options)
        t.Commit()


def copy_view(activedoc, source_view, dest_doc):
    matching_view = find_matching_view(dest_doc, source_view)
    if matching_view:
        return matching_view

    logger.debug('Copying view: {}'.format(source_view.Name))
    new_view = None

    if source_view.ViewType == ViewType.DrawingSheet:
        try:
            logger.debug('Source view is a sheet. ' \
                         'Creating destination sheet.')
            t = Transaction(dest_doc, 'Create Sheet')
            t.Start()
            new_view = ViewSheet.Create(dest_doc,
                                        ElementId.InvalidElementId)
            new_view.ViewName = source_view.ViewName
            new_view.SheetNumber = source_view.SheetNumber
            t.Commit()
        except Exception as sheet_err:
            logger.error('Error creating sheet. | {}'.format(sheet_err))
    elif source_view.ViewType == ViewType.DraftingView:
        try:
            logger.debug('Source view is a drafting. ' \
                         'Creating destination drafting view.')
            t = Transaction(dest_doc, 'Create Drafting View')
            t.Start()
            new_view = ViewDrafting.Create(dest_doc,
                          get_default_type(dest_doc,
                                           ElementTypeGroup.ViewTypeDrafting))
            new_view.ViewName = source_view.ViewName
            new_view.Scale = source_view.Scale
            t.Commit()
        except Exception as sheet_err:
            logger.error('Error creating drafting view. | {}'.format(sheet_err))
    elif source_view.ViewType == ViewType.Legend:
        try:
            logger.debug('Source view is a legend. ' \
                         'Creating destination legend view.')
            first_legend = find_first_legend(dest_doc)
            if first_legend:
                t = Transaction(dest_doc, 'Create Legend View')
                t.Start()
                new_view = dest_doc.GetElement(
                               first_legend.Duplicate(
                                   ViewDuplicateOption.Duplicate))
                new_view.ViewName = source_view.ViewName
                new_view.Scale = source_view.Scale
                t.Commit()
            else:
                logger.error('Document must have at least one Legend view. ' \
                             'Skipping legend.')
        except Exception as sheet_err:
            logger.error('Error creating drafting view. | {}'.format(sheet_err))

    if new_view:
        copy_view_contents(activedoc, source_view, dest_doc, new_view)

    return new_view


def copy_sheet_view(*args):
    return copy_view(*args)


def copy_sheet_viewports(activedoc, source_sheet, dest_doc, dest_sheet):
    # uncomment for copy one viewport in testing
    # for vport_id in list(source_sheet.GetAllViewports())[:1]:
    for vport_id in source_sheet.GetAllViewports():
        vport = activedoc.GetElement(vport_id)
        vport_view = activedoc.GetElement(vport.ViewId)

        print('\t\tCopying view: {}'.format(vport_view.ViewName))
        new_view = copy_view(activedoc, vport_view, dest_doc)

        if new_view:
            print('\t\t\tPlacing copied view on sheet.')
            t = Transaction(dest_doc, 'Place View on Sheet')
            t.Start()
            new_vport = Viewport.Create(dest_doc,
                                        dest_sheet.Id,
                                        new_view.Id,
                                        vport.GetBoxCenter())
            t.Commit()


def copy_sheet(activedoc, source_sheet, dest_doc):
    logger.debug('Copying sheet {} to document {}'
                 .format(source_sheet.Name,
                         dest_doc.Title))
    tg = TransactionGroup(dest_doc, 'Import Sheet')
    tg.Start()

    logger.debug('Creating destination sheet...')
    new_sheet = copy_sheet_view(activedoc, source_sheet, dest_doc)

    if new_sheet:
        logger.debug('Copying sheet viewports...')
        copy_sheet_viewports(activedoc, source_sheet, dest_doc, new_sheet)
    else:
        logger.error('Failed copying sheet: {}'.format(source_sheet.Name))

    tg.Assimilate()


dest_docs = get_dest_docs()
doc_count = len(dest_docs)

source_sheets = get_source_sheets()
sheet_count = len(source_sheets)

total_work = doc_count * sheet_count
work_counter = 0

for dest_doc in dest_docs:
    this_script.output.print_md('**Copying Sheet(s) to Document:** {0}'
                                .format(dest_doc.Title))

    for source_sheet in source_sheets:
        print('Copying Sheet: {0} - {1}'.format(source_sheet.SheetNumber,
                                                source_sheet.Name))
        copy_sheet(activedoc, source_sheet, dest_doc)
        work_counter += 1
        this_script.output.update_progress(work_counter, total_work)

    this_script.output.print_md('**Copied {} sheets ' \
                                'to {} documents.**'.format(sheet_count,
                                                            doc_count))
