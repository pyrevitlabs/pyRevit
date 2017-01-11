"""Print Sheets from a linked model."""

import os.path as op
from pyrevit import USER_DESKTOP

from scriptutils import logger
from scriptutils.userinput import WPFWindow

from revitutils import doc, all_docs

import clr
from Autodesk.Revit.DB import Element, FilteredElementCollector, BuiltInCategory, RevitLinkType, ViewSheet, \
                              ViewSet, PrintRange, Transaction


class PrintLinkedSheets(WPFWindow):
    def __init__(self, xaml_file_name):
        self.linked_models = []

        WPFWindow.__init__(self, xaml_file_name)
        self._find_linked_models()

    def _find_linked_models(self):
        cl = FilteredElementCollector(doc)
        self.linked_models = cl.OfClass(clr.GetClrType(RevitLinkType)).ToElements()
        self.linkedmodels_lb.ItemsSource = self.linked_models
        self.linkedmodels_lb.SelectedIndex = 0

    def _get_linked_model_doc(self):
        linked_model = self.linkedmodels_lb.SelectedItem
        for open_doc in all_docs:
            if open_doc.Title == Element.Name.GetValue(linked_model):
                return open_doc

    def _list_sheets(self):
        open_doc = self._get_linked_model_doc()
        if open_doc:
            cl_sheets = FilteredElementCollector(open_doc)
            sheetsnotsorted = cl_sheets.OfClass(clr.GetClrType(ViewSheet)).WhereElementIsNotElementType().ToElements()
            linked_sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)
            self.linkedsheets_lb.ItemsSource = linked_sheets

    def _get_printer(self):
        open_doc = self._get_linked_model_doc()
        self.print_l.Text = 'Select Sheets to be Printed (To: {})'.format(open_doc.PrintManager.PrinterName)

    def _print_sheets(self, combined=False):
        open_doc = self._get_linked_model_doc()
        print_mgr = open_doc.PrintManager
        print_mgr.PrintToFile = True

        if combined:
            # fixme: list sheets sets and let user decide which one to print. Changing sets is not possible
            pass
            # print_mgr.CombinedFile = combined
            # print_mgr.PrintRange = PrintRange.Select
            # myviewset = ViewSet()
            # viewsheetsetting = print_mgr.ViewSheetSetting
            # for sheet in self.linkedsheets_lb.SelectedItems:
            #     myviewset.Insert(sheet)
            # viewsheetsetting.CurrentViewSheetSet.Views = myviewset
            # print_mgr.PrintToFileName = op.join(USER_DESKTOP, '{}.pdf'.format(open_doc.Title))
            # print_mgr.SubmitPrint()

        else:
            # print_mgr.SelectNewPrintDriver("CutePDF Writer")
            for sheet in self.linkedsheets_lb.SelectedItems:
                print_mgr.PrintToFileName = op.join(USER_DESKTOP, '{} - {}.pdf'.format(sheet.SheetNumber, sheet.Name))
                print_mgr.SubmitPrint(sheet)

    def selection_changed(self, sender, args):
        if self.linkedsheets_lb.SelectedItem:
            self.print_b.IsEnabled = True
            self.printcombined_b.IsEnabled = False
        else:
            self.print_b.IsEnabled = False
            self.printcombined_b.IsEnabled = False

    def linked_model_selected(self, sender, args):
        self._list_sheets()
        self._get_printer()

    def print_sheets(self, sender, args):
        self.Close()
        self._print_sheets()

    def print_sheetscombined(self, sender, args):
        self.Close()
        self._print_sheets(combined=True)


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    PrintLinkedSheets('PrintLinkedSheets.xaml').ShowDialog()
