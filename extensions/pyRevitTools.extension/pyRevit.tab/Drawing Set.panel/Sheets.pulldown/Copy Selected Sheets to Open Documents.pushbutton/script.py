import sys

from scriptutils import logger, this_script
from scriptutils.userinput import SelectFromCheckBoxes
from revitutils import doc as activedoc
from revitutils import uidoc, selection, curview, Action

from System.Collections.Generic import List

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog


__doc__ = 'Copies selected or current sheet(s) to all ' \
          'projects currently open in Revit. Make sure the destination ' \
          'documents have at least one Legend view. (Revit API does not ' \
          'provide a method to create Legend views so this script needs ' \
          'to duplicate an existing one to create a new Legend.'


class Option:
    def __init__(self, op_name, default_state=False):
        self.state = default_state
        self.name = op_name
    def __nonzero__(self):
        return self.state


class OptionSet:
    def __init__(self):
        self.op_copy_vports = Option('Copy Viewports', True)
        self.op_copy_schedules = Option('Copy Schedules', True)
        self.op_copy_titleblock = Option('Copy Sheet Titleblock', True)
        self.op_update_exist_view_contents = Option('Update Existing View Contents')
        # self.op_update_exist_vport_locations = Option('Update Existing Viewport Locations')


class CopyUseDestination(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


def error_and_close(msg):
    TaskDialog.Show('pyrevit', msg)
    sys.exit(0)


def get_user_options():
    op_set = OptionSet()
    return_options = \
        SelectFromCheckBoxes.show([getattr(op_set, x) for x in dir(op_set) if x.startswith('op_')],
                                  title='Select Copy Options',
                                  button_name='Copy Now')

    if not return_options:
        sys.exit(0)

    return op_set


def get_dest_docs():
    class DestDoc:
        def __init__(self, doc):
            self.state = False
            self.dest_doc = doc
            self.name = self.dest_doc.Title
        def __nonzero__(self):
            return self.state

    # find open documents other than the active doc
    open_docs = [d for d in __revit__.Application.Documents if not d.IsLinked]
    open_docs.remove(activedoc)
    if len(open_docs) < 1:
        error_and_close('Only one active document is found. ' \
                        'At least two documents must be open. ' \
                        'Operation cancelled.')

    return_options = \
        SelectFromCheckBoxes.show([DestDoc(x) for x in open_docs],
                                   title='Select Destination Documents',
                                   button_name='OK')

    if return_options:
        return [x.dest_doc for x in return_options if x]
    else:
        sys.exit(0)


def get_source_sheets():
    class SheetToCopy:
        def __init__(self, sheet):
            self.state = False
            self.sheet = sheet
            self.name = '{} - {}'.format(sheet.SheetNumber, sheet.Name)
            self.number = sheet.SheetNumber
        def __nonzero__(self):
            return self.state

    all_sheets = FilteredElementCollector(activedoc) \
                 .OfClass(ViewSheet) \
                 .WhereElementIsNotElementType() \
                 .ToElements()

    return_options = \
        SelectFromCheckBoxes.show(sorted([SheetToCopy(x) for x in all_sheets],
                                  key=lambda x: x.number),
                                  title='Select Sheets to be Copied',
                                  width=500,
                                  button_name='Copy Sheets')

    if return_options:
        return [x.sheet for x in return_options if x]
    else:
        sys.exit(0)


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


def get_view_contents(dest_doc, source_view):
    view_elements = \
        FilteredElementCollector(dest_doc, source_view.Id).WhereElementIsNotElementType().ToElements()
    elements_ids = []
    for element in view_elements:
        if (element.Category and element.Category.Name == 'Title Blocks') \
            and not OPTION_SET.op_copy_titleblock:
            continue
        elif isinstance(element, ScheduleSheetInstance) \
            and not OPTION_SET.op_copy_schedules:
            continue
        elif isinstance(element, Viewport) \
            or 'ExtentElem' in element.Name:
            continue
        else:
            elements_ids.append(element.Id)
    return elements_ids


def clear_view_contents(dest_doc, dest_view):
    logger.debug('Removing view contents: {}'.format(dest_view.Name))
    elements_ids = get_view_contents(dest_doc, dest_view)

    t = Transaction(dest_doc, 'Delete View Contents')
    t.Start()
    for el_id in elements_ids:
        try:
            dest_doc.Delete(el_id)
        except Exception as err:
            continue
    t.Commit()

    return True


def copy_view_contents(activedoc, source_view, dest_doc, dest_view,
                       clear_contents=False):
    logger.debug('Copying view contents: {}'.format(source_view.Name))

    elements_ids = get_view_contents(activedoc, source_view)

    if clear_contents:
        if not clear_view_contents(dest_doc, dest_view):
            return False

    cp_options = CopyPasteOptions()
    cp_options.SetDuplicateTypeNamesHandler(CopyUseDestination())

    if elements_ids:
        t = Transaction(dest_doc, 'Copy View Contents')
        t.Start()
        copiedElement = \
            ElementTransformUtils.CopyElements(source_view,
                                               List[ElementId](elements_ids),
                                               dest_view, None, cp_options)
        t.Commit()
    return True


def copy_view(activedoc, source_view, dest_doc):
    matching_view = find_matching_view(dest_doc, source_view)
    if matching_view:
        print('\t\t\tView/Sheet already exists in document.')
        if OPTION_SET.op_update_exist_view_contents:
            if not copy_view_contents(activedoc, source_view,
                                      dest_doc, matching_view,
                                      clear_contents=OPTION_SET.op_update_exist_view_contents):
                logger.error('Could not copy view contents: {}'.format(source_view.Name))

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
                logger.error('Destination document must have at least one ' \
                             'Legend view. Skipping legend.')
        except Exception as sheet_err:
            logger.error('Error creating drafting view. | {}'.format(sheet_err))

    if new_view:
        copy_view_contents(activedoc, source_view, dest_doc, new_view)

    return new_view


def copy_sheet_view(*args):
    return copy_view(*args)


def copy_sheet_viewports(activedoc, source_sheet,
                         dest_doc, dest_sheet):

    existing_views = [dest_doc.GetElement(x).ViewId for x in dest_sheet.GetAllViewports()]

    for vport_id in source_sheet.GetAllViewports():
        vport = activedoc.GetElement(vport_id)
        vport_view = activedoc.GetElement(vport.ViewId)

        print('\t\tCopying/updating view: {}'.format(vport_view.ViewName))
        new_view = copy_view(activedoc, vport_view, dest_doc)

        if new_view:
            if new_view.Id not in existing_views:
                print('\t\t\tPlacing copied view on sheet.')
                t = Transaction(dest_doc, 'Place View on Sheet')
                t.Start()
                new_vport = Viewport.Create(dest_doc,
                                            dest_sheet.Id,
                                            new_view.Id,
                                            vport.GetBoxCenter())
                t.Commit()
            else:
                print('\t\t\tView already exists on the sheet.')


def copy_sheet(activedoc, source_sheet, dest_doc):
    logger.debug('Copying sheet {} to document {}'
                 .format(source_sheet.Name,
                         dest_doc.Title))
    print('\tCopying/updating Sheet: {}'.format(source_sheet.Name))
    tg = TransactionGroup(dest_doc, 'Import Sheet')
    tg.Start()

    logger.debug('Creating destination sheet...')
    new_sheet = copy_sheet_view(activedoc, source_sheet, dest_doc)

    if new_sheet:
        if OPTION_SET.op_copy_vports:
            logger.debug('Copying sheet viewports...')
            copy_sheet_viewports(activedoc, source_sheet,
                                 dest_doc, new_sheet)
        else:
            print('Skipping viewports...')
    else:
        logger.error('Failed copying sheet: {}'.format(source_sheet.Name))

    tg.Assimilate()


dest_docs = get_dest_docs()
doc_count = len(dest_docs)

source_sheets = get_source_sheets()
sheet_count = len(source_sheets)

OPTION_SET = get_user_options()

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
