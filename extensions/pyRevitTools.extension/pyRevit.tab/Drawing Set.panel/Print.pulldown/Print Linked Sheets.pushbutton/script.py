"""Print Sheets from a linked model."""

import os.path as op
from pyrevit import USER_DESKTOP
from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


logger = script.get_logger()


class PrintLinkedSheets(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        self.linked_models = []

        forms.WPFWindow.__init__(self, xaml_file_name)
        self._find_linked_models()

    def _find_linked_models(self):
        cl = DB.FilteredElementCollector(revit.doc)
        all_linked_models = \
            cl.OfClass(framework.get_type(DB.RevitLinkType)).ToElements()
        self.linked_models = [lm for lm in all_linked_models
                              if DB.RevitLinkType.IsLoaded(revit.doc, lm.Id)]
        self.linkedmodels_lb.ItemsSource = self.linked_models
        self.linkedmodels_lb.SelectedIndex = 0

    def _get_linked_model_doc(self):
        linked_model = self.linkedmodels_lb.SelectedItem
        for open_doc in revit.docs:
            if open_doc.Title == revit.ElementWrapper(linked_model).name:
                return open_doc

    def _list_sheets(self):
        open_doc = self._get_linked_model_doc()
        if open_doc:
            cl_sheets = DB.FilteredElementCollector(open_doc)
            sheetsnotsorted = \
                cl_sheets.OfClass(framework.get_type(DB.ViewSheet))\
                         .WhereElementIsNotElementType()\
                         .ToElements()
            linked_sheets = \
                sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)
            self.linkedsheets_lb.ItemsSource = linked_sheets

    def _get_printer(self):
        open_doc = self._get_linked_model_doc()
        if open_doc:
            self.print_l.Text = 'Select Sheets to be Printed (To: {})' \
                                .format(open_doc.PrintManager.PrinterName)

    def _print_sheets(self, combined=False):
        open_doc = self._get_linked_model_doc()
        print_mgr = open_doc.PrintManager
        print_mgr.PrintToFile = True

        if combined:
            # fixme: list sheets sets and let user decide which one to print.
            # Changing sets is not possible
            pass
            # print_mgr.CombinedFile = combined
            # print_mgr.PrintRange = DB.PrintRange.Select
            # myviewset = DB.ViewSet()
            # viewsheetsetting = print_mgr.ViewSheetSetting
            # for sheet in self.linkedsheets_lb.SelectedItems:
            #     myviewset.Insert(sheet)
            # viewsheetsetting.CurrentViewSheetSet.Views = myviewset
            # print_mgr.PrintToFileName = \
            #    op.join(USER_DESKTOP, '{}.pdf'.format(open_doc.Title))
            # print_mgr.SubmitPrint()

        else:
            # print_mgr.SelectNewPrintDriver("CutePDF Writer")
            for sheet in self.linkedsheets_lb.SelectedItems:
                print_mgr.PrintToFileName = \
                    op.join(USER_DESKTOP, '{} - {}.pdf'
                                          .format(sheet.SheetNumber,
                                                  sheet.Name))
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


PrintLinkedSheets('PrintLinkedSheets.xaml').ShowDialog()
