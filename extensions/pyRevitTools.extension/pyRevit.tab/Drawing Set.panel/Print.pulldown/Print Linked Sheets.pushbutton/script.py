"""Print Sheets from a linked model."""

import os.path as op
from pyrevit import USER_DESKTOP

from scriptutils import logger
from scriptutils.userinput import WPFWindow

from revitutils import doc, all_docs

import clr
from Autodesk.Revit.DB import Element, FilteredElementCollector, BuiltInCategory, RevitLinkType, ViewSheet


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
        self.print_b.Content = 'Print Selected Sheets (To: {})'.format(open_doc.PrintManager.PrinterName)

    def linked_model_selected(self, sender, args):
        self._list_sheets()
        self._get_printer()

    def print_sheets(self, sender, args):
        open_doc = self._get_linked_model_doc()
        printManager = open_doc.PrintManager
        printManager.PrintToFile = True
        # printManager.SelectNewPrintDriver("CutePDF Writer")
        for sheet in self.linkedsheets_lb.SelectedItems:
            printManager.PrintToFileName = op.join(USER_DESKTOP, '{} - {}.pdf'.format(sheet.SheetNumber, sheet.Name))
            printManager.SubmitPrint(sheet)


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    PrintLinkedSheets('PrintLinkedSheets.xaml').ShowDialog()
