"""Print sheets in order from a sheet index.

Shift-Click:
When using the `Combine into one file` option,
the tool adds invisible characters at the start of
the sheet names to push Revit's interenal printing
engine to sort the sheets correctly per the drawing
index order. Shift-Clicking the tool will remove all
these characters from the sheet numbers, in case an error
in the tool causes these characters to remain.
"""

import os.path as op
import codecs

from pyrevit import USER_DESKTOP
from pyrevit import framework
from pyrevit.framework import Windows
from pyrevit import coreutils
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()
config = script.get_config()


# Non Printable Char
NPC = u'\u200e'


class ViewSheetListItem(object):
    def __init__(self, view_sheet):
        self._sheet = view_sheet
        self.name = self._sheet.Name
        self.number = self._sheet.SheetNumber
        self.printable = self._sheet.CanBePrinted
        self.print_index = 0

    @property
    def revit_sheet(self):
        return self._sheet


class PrintSheetsWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        for cat in revit.doc.Settings.Categories:
            if cat.Name == 'Sheets':
                self.sheet_cat_id = cat.Id

        self.schedules_cb.ItemsSource = self._get_sheet_index_list()
        self.schedules_cb.SelectedIndex = 0

        item_cstyle = self.sheets_lb.ItemContainerStyle

        item_cstyle.Setters.Add(
            Windows.Setter(
                Windows.Controls.ListViewItem.AllowDropProperty,
                True
                )
            )

        item_cstyle.Setters.Add(
            Windows.EventSetter(
                Windows.Controls.ListViewItem.PreviewMouseLeftButtonDownEvent,
                Windows.Input.MouseButtonEventHandler(self.preview_mouse_down)
                )
            )

        item_cstyle.Setters.Add(
            Windows.EventSetter(
                Windows.Controls.ListViewItem.DropEvent,
                Windows.DragEventHandler(self.drop_sheet)
                )
            )

    @property
    def selected_schedule(self):
        return self.schedules_cb.SelectedItem

    @property
    def reverse_print(self):
        return self.reverse_cb.IsChecked

    @property
    def combine_print(self):
        return self.combine_cb.IsChecked

    @property
    def show_placeholders(self):
        return self.placeholder_cb.IsChecked

    @property
    def include_placeholders(self):
        return self.indexspace_cb.IsChecked

    @property
    def sheet_list(self):
        return self.sheets_lb.ItemsSource

    @sheet_list.setter
    def sheet_list(self, value):
        self.sheets_lb.ItemsSource = value

    @property
    def printable_sheets(self):
        return [x for x in self.sheet_list if x.printable]

    def _get_schedule_text_data(self, schedule_view):
        schedule_data_file = \
            script.get_instance_data_file(str(schedule_view.Id.IntegerValue))
        vseop = DB.ViewScheduleExportOptions()
        vseop.TextQualifier = DB.ExportTextQualifier.None
        schedule_view.Export(op.dirname(schedule_data_file),
                             op.basename(schedule_data_file),
                             vseop)

        sched_data = []
        try:
            with codecs.open(schedule_data_file, 'r', 'utf_16_le') \
                    as sched_data_file:
                return sched_data_file.readlines()
        except Exception as open_err:
            logger.error('Error opening sheet index export: %s | %s',
                         schedule_data_file, open_err)
            return sched_data

    def _order_sheets_by_schedule_data(self, schedule_view, sheet_list):
        sched_data = self._get_schedule_text_data(schedule_view)

        if not sched_data:
            return sheet_list

        ordered_sheets_dict = {}
        for sheet in sheet_list:
            for line_no, data_line in enumerate(sched_data):
                try:
                    if sheet.SheetNumber in data_line:
                        ordered_sheets_dict[line_no] = sheet
                        break
                    if not sheet.CanBePrinted:
                        logger.debug('Sheet %s is not printable.',
                                     sheet.SheetNumber)
                except Exception:
                    continue

        sorted_keys = sorted(ordered_sheets_dict.keys())
        return [ordered_sheets_dict[x] for x in sorted_keys]

    def _get_ordered_schedule_sheets(self):
        schedule_view = self.selected_schedule
        cl_sheets = DB.FilteredElementCollector(revit.doc, schedule_view.Id)
        sheets = cl_sheets.OfClass(framework.get_type(DB.ViewSheet))\
                          .WhereElementIsNotElementType()\
                          .ToElements()

        return self._order_sheets_by_schedule_data(schedule_view, sheets)

    def _is_sheet_index(self, schedule_view):
        return self.sheet_cat_id == schedule_view.Definition.CategoryId \
               and not schedule_view.IsTemplate

    def _get_sheet_index_list(self):
        cl_schedules = DB.FilteredElementCollector(revit.doc)
        schedules = cl_schedules.OfClass(framework.get_type(DB.ViewSchedule))\
                                .WhereElementIsNotElementType()\
                                .ToElements()

        return [sched for sched in schedules if self._is_sheet_index(sched)]

    def _get_printmanager(self):
        try:
            return revit.doc.PrintManager
        except Exception as printerr:
            logger.critical('Error getting printer manager from document. '
                            'Most probably there is not a printer defined '
                            'on your system. | %s', printerr)
            return None

    def _print_combined_sheets_in_order(self):
        # make sure we can access the print config
        print_mgr = self._get_printmanager()
        if not print_mgr:
            return
        print_mgr.PrintRange = DB.PrintRange.Select

        with revit.TransactionGroup('Print Sheets in Order') as tg:
            # add non-printable char in front of sheet Numbers
            # to push revit to sort them per user
            sheet_set = DB.ViewSet()
            original_sheetnums = []
            with revit.Transaction('Fix Sheet Numbers') as t:
                for idx, sheet in enumerate(self.sheet_list):
                    rvtsheet = sheet.revit_sheet
                    original_sheetnums.append(rvtsheet.SheetNumber)
                    rvtsheet.SheetNumber = \
                        NPC * (idx + 1) + rvtsheet.SheetNumber
                    if sheet.printable:
                        sheet_set.Insert(rvtsheet)

            # Collect existing sheet sets
            cl = DB.FilteredElementCollector(revit.doc)
            viewsheetsets = cl.OfClass(framework.get_type(DB.ViewSheetSet))\
                              .WhereElementIsNotElementType()\
                              .ToElements()
            all_viewsheetsets = {vss.Name: vss for vss in viewsheetsets}

            sheetsetname = 'OrderedPrintSet'

            with revit.Transaction('Remove Previous Print Set') as t:
                # Delete existing matching sheet set
                if sheetsetname in all_viewsheetsets:
                    print_mgr.ViewSheetSetting.CurrentViewSheetSet = \
                        all_viewsheetsets[sheetsetname]
                    print_mgr.ViewSheetSetting.Delete()

            with revit.Transaction('Update Ordered Print Set') as t:
                try:
                    viewsheet_settings = print_mgr.ViewSheetSetting
                    viewsheet_settings.CurrentViewSheetSet.Views = \
                        sheet_set
                    viewsheet_settings.SaveAs(sheetsetname)
                except Exception as viewset_err:
                    sheet_report = ''
                    for sheet in sheet_set:
                        sheet_report += '{} {}\n'.format(
                            sheet.SheetNumber if isinstance(sheet,
                                                            DB.ViewSheet)
                            else '---',
                            type(sheet)
                            )
                    logger.critical(
                        'Error setting sheet set on print mechanism. '
                        'These items are included in the viewset '
                        'object:\n%s', sheet_report
                        )
                    raise viewset_err

            # set print job configurations
            print_mgr.PrintOrderReverse = self.reverse_print
            try:
                print_mgr.CombinedFile = True
            except Exception as e:
                forms.alert(str(e) +
                            '\nSet printer correctly in Print settings.')
                script.exit()
            print_mgr.PrintToFile = True
            print_mgr.PrintToFileName = op.join(r'C:', 'Ordered Sheet Set.pdf')
            print_mgr.Apply()
            print_mgr.SubmitPrint()

            # now fix the sheet names
            with revit.Transaction('Restore Sheet Numbers') as t:
                for sheet, sheetnum in zip(self.sheet_list,
                                           original_sheetnums):
                    rvtsheet = sheet.revit_sheet
                    rvtsheet.SheetNumber = sheetnum

    def _print_sheets_in_order(self):
        # make sure we can access the print config
        print_mgr = self._get_printmanager()
        if not print_mgr:
            return
        print_mgr.PrintToFile = True
        # print_mgr.CombinedFile = False
        print_mgr.PrintRange = DB.PrintRange.Current
        for sheet in self.sheet_list:
            output_fname = \
                coreutils.cleanup_filename('{:05} {} - {}.pdf'
                                           .format(sheet.print_index,
                                                   sheet.number,
                                                   sheet.name))

            print_mgr.PrintToFileName = op.join(USER_DESKTOP, output_fname)
            if sheet.printable:
                print_mgr.SubmitPrint(sheet.revit_sheet)
            else:
                logger.debug('Sheet %s is not printable. Skipping print.',
                             sheet.number)

    def _update_print_indices(self, sheet_list):
        for idx, sheet in enumerate(sheet_list):
            sheet.print_index = idx

    def selection_changed(self, sender, args):
        if self.selected_schedule:
            sheet_list = [ViewSheetListItem(x)
                          for x in self._get_ordered_schedule_sheets()]

            # reverse sheet if reverse is set
            if self.reverse_print:
                sheet_list.reverse()

            if not self.show_placeholders:
                self.indexspace_cb.IsEnabled = True
                # update print indices with placeholder sheets
                self._update_print_indices(sheet_list)
                # remove placeholders if requested
                printable_sheets = []
                for sheet in sheet_list:
                    if sheet.printable:
                        printable_sheets.append(sheet)

                # update print indices without placeholder sheets
                if not self.include_placeholders:
                    self._update_print_indices(printable_sheets)

                self.sheet_list = printable_sheets

            else:
                self.indexspace_cb.IsChecked = True
                self.indexspace_cb.IsEnabled = False
                # update print indices
                self._update_print_indices(sheet_list)
                # Show all sheets
                self.sheet_list = sheet_list

    def print_sheets(self, sender, args):
        if self.sheet_list:
            if not self.combine_print:
                sheet_count = len(self.sheet_list)
                if sheet_count > 5:
                    if not forms.alert('Are you sure you want to print {} '
                                       'sheets individually? The process can '
                                       'not be cancelled.'.format(sheet_count),
                                       ok=False, yes=True, no=True):
                        return
            self.Close()
            if self.combine_print:
                self._print_combined_sheets_in_order()
            else:
                self._print_sheets_in_order()

    def handle_url_click(self, sender, args):
        script.open_url('https://github.com/McCulloughRT/PrintFromIndex')

    def preview_mouse_down(self, sender, args):
        if isinstance(sender, Windows.Controls.ListViewItem):
            if sender.DataContext.printable:
                Windows.DragDrop.DoDragDrop(sender,
                                            sender.DataContext,
                                            Windows.DragDropEffects.Move)

            sender.IsSelected = False

    def drop_sheet(self, sender, args):
        dropped_data = args.Data.GetData(ViewSheetListItem)
        target = sender.DataContext

        dropped_idx = self.sheets_lb.Items.IndexOf(dropped_data)
        target_idx = self.sheets_lb.Items.IndexOf(target)

        sheet_list = self.sheet_list
        sheet_list.remove(dropped_data)
        sheet_list.insert(target_idx, dropped_data)
        self._update_print_indices(sheet_list)
        self.sheets_lb.Items.Refresh()


def cleanup_sheetnumbers():
    sheets = revit.query.get_sheets(doc=revit.doc)
    with revit.Transaction('Cleanup Sheet Numbers'):
        for sheet in sheets:
            sheet.SheetNumber = sheet.SheetNumber.replace(NPC, '')


if __shiftclick__:  # noqa
    cleanup_sheetnumbers()
else:
    PrintSheetsWindow('PrintOrderedSheets.xaml').ShowDialog()
