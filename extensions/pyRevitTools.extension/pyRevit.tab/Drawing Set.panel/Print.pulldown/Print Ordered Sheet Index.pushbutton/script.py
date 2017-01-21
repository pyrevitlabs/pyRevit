"""Print sheets in order from a sheet index."""

import os.path as op
import codecs
import clr

from pyrevit.coreutils import verify_directory
from scriptutils import this_script, open_url, logger
from scriptutils.userinput import WPFWindow
from revitutils import doc

import clr
from Autodesk.Revit.DB import Element, FilteredElementCollector, ViewSchedule, ViewSheet,\
                              ViewScheduleExportOptions, ExportTextQualifier

clr.AddReference('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")

# noinspection PyUnresolvedReferences
from System.Windows import DragDrop, DragDropEffects
# noinspection PyUnresolvedReferences
from System.Windows import Setter, EventSetter, DragEventHandler, Style
# noinspection PyUnresolvedReferences
from System.Windows.Input import MouseButtonEventHandler
# noinspection PyUnresolvedReferences
from System.Windows.Controls import ListViewItem


class PrintSheetsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.schedules_cb.ItemsSource = self._get_schedules_list()
        self.schedules_cb.SelectedIndex = 0

        itemContainerStyle = Style(clr.GetClrType(ListViewItem))
        itemContainerStyle.Setters.Add(Setter(ListViewItem.AllowDropProperty, True))
        itemContainerStyle.Setters.Add(EventSetter(ListViewItem.PreviewMouseLeftButtonDownEvent,
                                                   MouseButtonEventHandler(self.preview_mouse_down)))
        itemContainerStyle.Setters.Add(EventSetter(ListViewItem.DropEvent,
                                                   DragEventHandler(self.drop_sheet)))
        self.linkedsheets_lb.ItemContainerStyle = itemContainerStyle

    @property
    def selected_schedule(self):
        return self.schedules_cb.SelectedItem

    @property
    def reverse_print(self):
        return self.reverse_cb.IsChecked

    @staticmethod
    def _get_schedule_text_data(schedule_view):
        schedule_data_file = this_script.get_instance_data_file(str(schedule_view.Id.IntegerValue))
        vseop = ViewScheduleExportOptions()
        vseop.TextQualifier = ExportTextQualifier.None
        schedule_view.Export(op.dirname(schedule_data_file), op.basename(schedule_data_file), vseop)

        sched_data = []
        try:
            with codecs.open(schedule_data_file, 'r', 'utf_16_le') as sched_data_file:
                return sched_data_file.readlines()
        except:
            return sched_data

    @staticmethod
    def _order_sheets_by_schedule_data(schedule_view, sheet_list):
        sched_data = PrintSheetsWindow._get_schedule_text_data(schedule_view)

        if not sched_data:
            return sheet_list

        ordered_sheets_dict = {}
        for sheet in sheet_list:
            for line_no, data_line in enumerate(sched_data):
                try:
                    if sheet.SheetNumber in data_line.split('\t'):
                        ordered_sheets_dict[line_no] = sheet
                        break
                except:
                    continue

        sorted_keys = sorted(ordered_sheets_dict.keys())
        return [ordered_sheets_dict[x] for x in sorted_keys]

    @staticmethod
    def _get_ordered_schedule_sheets(schedule_view):
        cl_sheets = FilteredElementCollector(doc, schedule_view.Id)
        sheets = cl_sheets.OfClass(clr.GetClrType(ViewSheet)).WhereElementIsNotElementType().ToElements()

        return PrintSheetsWindow._order_sheets_by_schedule_data(schedule_view, sheets)

    @staticmethod
    def _is_sheet_index(schedule_view):
        cl_sheets = FilteredElementCollector(doc, schedule_view.Id)
        sheets = cl_sheets.OfClass(clr.GetClrType(ViewSheet)).WhereElementIsNotElementType().ToElements()
        return len(sheets) > 0

    @staticmethod
    def _get_schedules_list():
        cl_schedules = FilteredElementCollector(doc)
        schedules = cl_schedules.OfClass(clr.GetClrType(ViewSchedule)).WhereElementIsNotElementType().ToElements()

        return [sched for sched in schedules if PrintSheetsWindow._is_sheet_index(sched)]

    @staticmethod
    def _print_sheets_in_order(sheet_list):
        print_mgr = doc.PrintManager
        print_mgr.PrintToFile = True
        for index, sheet in enumerate(sheet_list):
            print_mgr.PrintToFileName = op.join(r'C:', '{:05} {} - {}.pdf'.format(index,
                                                                                  sheet.SheetNumber,
                                                                                  sheet.Name))
            print_mgr.SubmitPrint(sheet)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def selection_changed(self, sender, args):
        if self.selected_schedule:
            ordered_sheets = PrintSheetsWindow._get_ordered_schedule_sheets(self.selected_schedule)
            printable_sheets = [x for x in ordered_sheets if x.CanBePrinted]
            if self.reverse_print:
                ordered_sheets.reverse()

            self.linkedsheets_lb.ItemsSource = ordered_sheets

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def print_sheets(self, sender, args):
        if self.linkedsheets_lb.ItemsSource:
            self.Close()
            PrintSheetsWindow._print_sheets_in_order(self.linkedsheets_lb.ItemsSource)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handle_url_click(self, sender, args):
        open_url('https://github.com/McCulloughRT/PrintFromIndex')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def preview_mouse_down(self, sender, args):
       if isinstance(sender, ListViewItem):
           DragDrop.DoDragDrop(sender, sender.DataContext, DragDropEffects.Move)
           sender.IsSelected = False

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def drop_sheet(self, sender, args):
        droppedData = args.Data.GetData(clr.GetClrType(ViewSheet))
        target = sender.DataContext

        removedIdx = self.linkedsheets_lb.Items.IndexOf(droppedData)
        targetIdx = self.linkedsheets_lb.Items.IndexOf(target)

        sheet_list = self.linkedsheets_lb.ItemsSource
        sheet_list[removedIdx], sheet_list[targetIdx] = sheet_list[targetIdx], sheet_list[removedIdx]
        self.linkedsheets_lb.Items.Refresh()


if __name__ == '__main__':
    PrintSheetsWindow('PrintOrderedSheets.xaml').ShowDialog()
