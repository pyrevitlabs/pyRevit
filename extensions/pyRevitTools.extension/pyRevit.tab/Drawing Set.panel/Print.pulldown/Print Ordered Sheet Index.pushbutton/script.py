"""Print sheets in order from a sheet index."""

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
            logger.error('Error opening sheet index export: {} | {}'
                         .format(schedule_data_file, open_err))
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

    def _print_combined_sheets_in_order(self):
        # todo: Revit does not follow the order of sheets as set by DB.ViewSet
        print_mgr = revit.doc.PrintManager
        print_mgr.PrintRange = DB.PrintRange.Select
        viewsheet_settings = print_mgr.ViewSheetSetting

        sheet_set = DB.ViewSet()

        for sheet in self.sheets_lb.ItemsSource:
            sheet_set.Insert(sheet.revit_sheet)

        # Collect existing sheet sets
        cl = DB.FilteredElementCollector(revit.doc)
        viewsheetsets = cl.OfClass(framework.get_type(DB.ViewSheetSet))\
                          .WhereElementIsNotElementType()\
                          .ToElements()
        all_viewsheetsets = {vss.Name: vss for vss in viewsheetsets}

        sheetsetname = 'OrderedPrintSet'

        with revit.Transaction('Update Ordered Print Set') as t:
            # Delete existing matching sheet set
            if sheetsetname in all_viewsheetsets:
                viewsheet_settings.CurrentViewSheetSet = \
                    all_viewsheetsets[sheetsetname]
                viewsheet_settings.Delete()

            viewsheet_settings.CurrentViewSheetSet.Views = sheet_set
            viewsheet_settings.SaveAs(sheetsetname)

        print_mgr.PrintToFile = True
        print_mgr.CombinedFile = True
        print_mgr.PrintToFileName = op.join(r'C:', 'Ordered Sheet Set.pdf')
        print_mgr.SubmitPrint()

    def _print_sheets_in_order(self):
        print_mgr = revit.doc.PrintManager
        print_mgr.PrintToFile = True
        # print_mgr.CombinedFile = False
        print_mgr.PrintRange = DB.PrintRange.Current
        for sheet in self.sheets_lb.ItemsSource:
            output_fname = \
                coreutils.cleanup_filename('{:05} {} - {}.pdf'
                                           .format(sheet.print_index,
                                                   sheet.number,
                                                   sheet.name))

            print_mgr.PrintToFileName = op.join(USER_DESKTOP, output_fname)
            if sheet.printable:
                print_mgr.SubmitPrint(sheet.revit_sheet)

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

                self.sheets_lb.ItemsSource = printable_sheets

            else:
                self.indexspace_cb.IsChecked = True
                self.indexspace_cb.IsEnabled = False
                # update print indices
                self._update_print_indices(sheet_list)
                # Show all sheets
                self.sheets_lb.ItemsSource = sheet_list

    def print_sheets(self, sender, args):
        if self.sheets_lb.ItemsSource:
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

        sheet_list = self.sheets_lb.ItemsSource
        sheet_list.remove(dropped_data)
        sheet_list.insert(target_idx, dropped_data)
        self._update_print_indices(sheet_list)
        self.sheets_lb.Items.Refresh()


PrintSheetsWindow('PrintOrderedSheets.xaml').ShowDialog()
