# -*- coding: utf-8 -*-
"""Print sheets in order from a sheet index.

Note:
When using the `Combine into one file` option,
the tool adds non-printable character u'\u200e'
(Left-To-Right Mark) at the start of the sheet names
to push Revit's interenal printing engine to sort
the sheets correctly per the drawing index order. 

Make sure your drawings indices consider this
when filtering for sheet numbers.

Shift-Click:
Shift-Clicking the tool will remove all
non-printable characters from the sheet numbers,
in case an error in the tool causes these characters
to remain.
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import re
import os.path as op
import codecs
from collections import namedtuple

from pyrevit import HOST_APP
from pyrevit import USER_DESKTOP
from pyrevit import framework
from pyrevit.framework import Windows, Drawing, ObjectModel, Forms
from pyrevit import coreutils
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


__title__ = 'Print\nSheets'

logger = script.get_logger()
config = script.get_config()


# Non Printable Char
NPC = u'\u200e'
INDEX_FORMAT = '{{:0{digits}}}'


AvailableDoc = namedtuple('AvailableDoc', ['name', 'hash', 'linked'])

NamingFormatter = namedtuple('NamingFormatter', ['template', 'desc'])

SheetRevision = namedtuple('SheetRevision', ['number', 'desc', 'date'])


class NamingFormat(forms.Reactive):
    def __init__(self, name, template, builtin=False):
        self._name = name
        self._template = template
        self.builtin = builtin

    @forms.reactive
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @forms.reactive
    def template(self):
        return self._template

    @template.setter
    def template(self, value):
        self._template = value


class ViewSheetListItem(forms.Reactive):
    def __init__(self, view_sheet, view_tblock, print_settings=None):
        self._sheet = view_sheet
        self._tblock = view_tblock
        self.name = self._sheet.Name
        self.number = self._sheet.SheetNumber
        self.issue_date = \
            self._sheet.Parameter[
                DB.BuiltInParameter.SHEET_ISSUE_DATE].AsString()
        self.printable = self._sheet.CanBePrinted

        self._print_index = 0
        self._print_filename = ''

        self._print_settings = print_settings
        self.all_print_settings = print_settings
        if self.all_print_settings:
            self._print_settings = self.all_print_settings[0]

        cur_rev = revit.query.get_current_sheet_revision(self._sheet)
        self.revision = ''
        if cur_rev:
            self.revision = SheetRevision(
                number=revit.query.get_rev_number(cur_rev),
                desc=cur_rev.Description,
                date=cur_rev.RevisionDate
            )

    @property
    def revit_sheet(self):
        return self._sheet

    @property
    def revit_tblock(self):
        return self._tblock

    @forms.reactive
    def print_settings(self):
        return self._print_settings

    @print_settings.setter
    def print_settings(self, value):
        self._print_settings = value

    @forms.reactive
    def print_index(self):
        return self._print_index

    @print_index.setter
    def print_index(self, value):
        self._print_index = value

    @forms.reactive
    def print_filename(self):
        return self._print_filename

    @print_filename.setter
    def print_filename(self, value):
        self._print_filename = \
            coreutils.cleanup_filename(value, windows_safe=True)


class PrintSettingListItem(object):
    def __init__(self, print_settings=None):
        self._psettings = print_settings

    @property
    def name(self):
        if isinstance(self._psettings, DB.InSessionPrintSetting):
            return "<In Session>"
        else:
            return self._psettings.Name

    @property
    def print_settings(self):
        return self._psettings

    @property
    def print_params(self):
        if self.print_settings:
            return self.print_settings.PrintParameters

    @property
    def paper_size(self):
        try:
            if self.print_params:
                return self.print_params.PaperSize
        except Exception:
            pass

    @property
    def allows_variable_paper(self):
        return False


class VariablePaperPrintSettingListItem(PrintSettingListItem):
    def __init__(self):
        PrintSettingListItem.__init__(self, None)

    @property
    def name(self):
        return "<Variable Paper Size>"

    @property
    def allows_variable_paper(self):
        return True


class EditNamingFormatsWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, start_with=None):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._drop_pos = 0
        self._starting_item = start_with
        self._saved = False

        self.reset_naming_formats()
        self.reset_formatters()

    @staticmethod
    def get_default_formatters():
        return [
            NamingFormatter(
                template='{index}',
                desc='Print Index Number e.g. "0001"'
            ),
            NamingFormatter(
                template='{number}',
                desc='Sheet Number e.g. "A1.00"'
            ),
            NamingFormatter(
                template='{name}',
                desc='Sheet Name e.g. "1ST FLOOR PLAN"'
            ),
            NamingFormatter(
                template='{name_dash}',
                desc='Sheet Name (with - for space) e.g. "1ST-FLOOR-PLAN"'
            ),
            NamingFormatter(
                template='{name_underline}',
                desc='Sheet Name (with _ for space) e.g. "1ST_FLOOR_PLAN"'
            ),
            NamingFormatter(
                template='{issue_date}',
                desc='Sheet Issue Date e.g. "2019-10-12"'
            ),
            NamingFormatter(
                template='{rev_number}',
                desc='Revision Number e.g. "01"'
            ),
            NamingFormatter(
                template='{rev_desc}',
                desc='Revision Description e.g. "ASI01"'
            ),
            NamingFormatter(
                template='{rev_date}',
                desc='Revision Date e.g. "2019-10-12"'
            ),
            NamingFormatter(
                template='{proj_name}',
                desc='Project Name e.g. "MY_PROJECT"'
            ),
            NamingFormatter(
                template='{proj_number}',
                desc='Project Number e.g. "PR2019.12"'
            ),
            NamingFormatter(
                template='{proj_building_name}',
                desc='Project Building Name e.g. "BLDG01"'
            ),
            NamingFormatter(
                template='{proj_issue_date}',
                desc='Project Issue Date e.g. "2019-10-12"'
            ),
            NamingFormatter(
                template='{proj_org_name}',
                desc='Project Organization Name e.g. "MYCOMP"'
            ),
            NamingFormatter(
                template='{proj_status}',
                desc='Project Status e.g. "CD100"'
            ),
            NamingFormatter(
                template='{username}',
                desc='Active User e.g. "eirannejad"'
            ),
            NamingFormatter(
                template='{revit_version}',
                desc='Active Revit Version e.g. "2019"'
            ),
            NamingFormatter(
                template='{sheet_param:PARAM_NAME}',
                desc='Value of Given Sheet Parameter e.g. '
                     'Replace PARAM_NAME with target parameter name'
            ),
            NamingFormatter(
                template='{tblock_param:PARAM_NAME}',
                desc='Value of Given TitleBlock Parameter e.g. '
                     'Replace PARAM_NAME with target parameter name'
            ),
            NamingFormatter(
                template='{proj_param:PARAM_NAME}',
                desc='Value of Given Project Information Parameter e.g. '
                     'Replace PARAM_NAME with target parameter name'
            ),
            NamingFormatter(
                template='{glob_param:PARAM_NAME}',
                desc='Value of Given Global Parameter. '
                     'Replace PARAM_NAME with target parameter name'
            ),
        ]

    @staticmethod
    def get_default_naming_formats():
        return [
            NamingFormat(
                name='0001 A1.00 1ST FLOOR PLAN.pdf',
                template='{index} {number} {name}.pdf',
                builtin=True
            ),
            NamingFormat(
                name='0001_A1.00_1ST FLOOR PLAN.pdf',
                template='{index}_{number}_{name}.pdf',
                builtin=True
            ),
            NamingFormat(
                name='0001-A1.00-1ST FLOOR PLAN.pdf',
                template='{index}-{number}-{name}.pdf',
                builtin=True
            ),
        ]

    @staticmethod
    def get_naming_formats():
        naming_formats = EditNamingFormatsWindow.get_default_naming_formats()
        naming_formats_dict = config.get_option('namingformats', {})
        for name, template in naming_formats_dict.items():
            naming_formats.append(NamingFormat(name=name, template=template))
        return naming_formats

    @staticmethod
    def set_naming_formats(naming_formats):
        naming_formats_dict = {
            x.name:x.template for x in naming_formats if not x.builtin
        }
        config.namingformats = naming_formats_dict
        script.save_config()

    @property
    def naming_formats(self):
        return self.formats_lb.ItemsSource

    @property
    def selected_naming_format(self):
        return self.formats_lb.SelectedItem

    @selected_naming_format.setter
    def selected_naming_format(self, value):
        self.formats_lb.SelectedItem = value
        self.namingformat_edit.DataContext = value

    def reset_formatters(self):
        self.formatters_wp.ItemsSource = \
            EditNamingFormatsWindow.get_default_formatters()

    def reset_naming_formats(self):
        self.formats_lb.ItemsSource = \
                ObjectModel.ObservableCollection[object](
                    EditNamingFormatsWindow.get_naming_formats()
                )
        if isinstance(self._starting_item, NamingFormat):
            for item in self.formats_lb.ItemsSource:
                if item.name == self._starting_item.name:
                    self.selected_naming_format = item
                    break

    # https://www.wpftutorial.net/DragAndDrop.html
    def start_drag(self, sender, args):
        name_formatter = args.OriginalSource.DataContext
        Windows.DragDrop.DoDragDrop(
            self.formatters_wp,
            Windows.DataObject("name_formatter", name_formatter),
            Windows.DragDropEffects.Copy
            )

    # https://social.msdn.microsoft.com/Forums/vstudio/en-US/941f6bf2-a321-459e-85c9-501ec1e13204/how-do-you-get-a-drag-and-drop-event-for-a-wpf-textbox-hosted-in-a-windows-form
    def preview_drag(self, sender, args):
        mouse_pos = Forms.Cursor.Position
        mouse_po_pt = Windows.Point(mouse_pos.X, mouse_pos.Y)
        self._drop_pos = \
            self.template_tb.GetCharacterIndexFromPoint(
                point=self.template_tb.PointFromScreen(mouse_po_pt),
                snapToText=True
                )
        self.template_tb.SelectionStart = self._drop_pos
        self.template_tb.SelectionLength = 0
        self.template_tb.Focus()
        args.Effects = Windows.DragDropEffects.Copy
        args.Handled = True

    def stop_drag(self, sender, args):
        name_formatter = args.Data.GetData("name_formatter")
        if name_formatter:
            new_template = \
                str(self.template_tb.Text)[:self._drop_pos] \
                + name_formatter.template \
                + str(self.template_tb.Text)[self._drop_pos:]
            self.template_tb.Text = new_template
            self.template_tb.Focus()

    def namingformat_changed(self, sender, args):
        naming_format = self.selected_naming_format
        self.namingformat_edit.DataContext = naming_format

    def duplicate_namingformat(self, sender, args):
        naming_format = self.selected_naming_format
        new_naming_format = NamingFormat(
            name='<unnamed>',
            template=naming_format.template
            )
        self.naming_formats.Add(new_naming_format)
        self.selected_naming_format = new_naming_format

    def delete_namingformat(self, sender, args):
        naming_format = self.selected_naming_format
        item_index = self.naming_formats.IndexOf(naming_format)
        self.naming_formats.Remove(naming_format)
        next_index = min([item_index, self.naming_formats.Count-1])
        self.selected_naming_format = self.naming_formats[next_index]

    def save_formats(self, sender, args):
        EditNamingFormatsWindow.set_naming_formats(self.naming_formats)
        self._saved = True
        self.Close()

    def cancelled(self, sender, args):
        if not self._saved:
            self.reset_naming_formats()

    def show_dialog(self):
        self.ShowDialog()


class PrintSheetsWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._init_psettings = None
        self._scheduled_sheets = []

        self.project_info = revit.query.get_project_info(doc=revit.doc)
        self.sheet_cat_id = \
            revit.query.get_category(DB.BuiltInCategory.OST_Sheets).Id

        self._setup_docs_list()
        self._setup_naming_formats()

    # doc and schedule
    @property
    def selected_doc(self):
        selected_doc = self.documents_cb.SelectedItem
        for open_doc in revit.docs:
            if open_doc.GetHashCode() == selected_doc.hash:
                return open_doc

    @property
    def selected_schedule(self):
        return self.schedules_cb.SelectedItem

    # misc
    @property
    def has_errors(self):
        return self.errormsg_tb.Text != ''

    # ordering configs
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
    def index_digits(self):
        return int(self.index_slider.Value)

    @property
    def index_start(self):
        return int(self.indexstart_tb.Text or 0) 

    @property
    def include_placeholders(self):
        return self.indexspace_cb.IsChecked

    # print settings
    @property
    def selected_naming_format(self):
        return self.namingformat_cb.SelectedItem

    @property
    def selected_printer(self):
        return self.printers_cb.SelectedItem

    @property
    def selected_print_setting(self):
        return self.printsettings_cb.SelectedItem

    # sheet list
    @property
    def sheet_list(self):
        return self.sheets_lb.ItemsSource

    @sheet_list.setter
    def sheet_list(self, value):
        self.sheets_lb.ItemsSource = value

    @property
    def selected_sheets(self):
        return self.sheets_lb.SelectedItems

    @property
    def printable_sheets(self):
        return [x for x in self.sheet_list if x.printable]

    @property
    def selected_printable_sheets(self):
        return [x for x in self.selected_sheets if x.printable]

    # private utils
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
                return [x.strip() for x in sched_data_file.readlines()]
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
            logger.debug('finding index for: %s', sheet.SheetNumber)
            for line_no, data_line in enumerate(sched_data):
                match_pattern = r'(^|.*\t){}(\t.*|$)'.format(sheet.SheetNumber)
                matches_sheet = re.match(match_pattern, data_line)
                logger.debug('match: %s', matches_sheet)
                try:
                    if matches_sheet:
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
        if self.selected_doc == self.selected_schedule.Document:
            sheets = DB.FilteredElementCollector(self.selected_doc,
                                                 self.selected_schedule.Id)\
                    .OfClass(framework.get_type(DB.ViewSheet))\
                    .WhereElementIsNotElementType()\
                    .ToElements()

            return self._order_sheets_by_schedule_data(
                self.selected_schedule,
                sheets
                )
        return []

    def _is_sheet_index(self, schedule_view):
        return self.sheet_cat_id == schedule_view.Definition.CategoryId \
               and not schedule_view.IsTemplate

    def _get_sheet_index_list(self):
        schedules = DB.FilteredElementCollector(self.selected_doc)\
                      .OfClass(framework.get_type(DB.ViewSchedule))\
                      .WhereElementIsNotElementType()\
                      .ToElements()

        return [sched for sched in schedules if self._is_sheet_index(sched)]

    def _get_printmanager(self):
        try:
            return self.selected_doc.PrintManager
        except Exception as printerr:
            logger.critical('Error getting printer manager from document. '
                            'Most probably there is not a printer defined '
                            'on your system. | %s', printerr)
            return None

    def _setup_docs_list(self):
        if not revit.doc.IsFamilyDocument:
            docs = [AvailableDoc(name=revit.doc.Title,
                                 hash=revit.doc.GetHashCode(),
                                 linked=False)]
            docs.extend([
                AvailableDoc(name=x.Title, hash=x.GetHashCode(), linked=True)
                for x in revit.query.get_all_linkeddocs(doc=revit.doc)
            ])
            self.documents_cb.ItemsSource = docs
            self.documents_cb.SelectedIndex = 0

    def _setup_naming_formats(self):
        self.namingformat_cb.ItemsSource = \
            EditNamingFormatsWindow.get_naming_formats()
        self.namingformat_cb.SelectedIndex = 0

    def _setup_printers(self):
        printers = list(Drawing.Printing.PrinterSettings.InstalledPrinters)
        self.printers_cb.ItemsSource = printers
        print_mgr = self._get_printmanager()
        self.printers_cb.SelectedItem = print_mgr.PrinterName

    def _setup_print_settings(self):
        if not self.selected_doc.IsLinked:
            print_settings = [VariablePaperPrintSettingListItem()]
        else:
            print_settings = []

        print_settings.extend(
            [PrintSettingListItem(self.selected_doc.GetElement(x))
             for x in self.selected_doc.GetPrintSettingIds()]
            )
        self.printsettings_cb.ItemsSource = print_settings

        print_mgr = self._get_printmanager()
        if isinstance(print_mgr.PrintSetup.CurrentPrintSetting,
                      DB.InSessionPrintSetting):
            in_session = PrintSettingListItem(
                print_mgr.PrintSetup.CurrentPrintSetting
                )
            print_settings.append(in_session)
            self.printsettings_cb.SelectedItem = in_session
        else:
            self._init_psettings = print_mgr.PrintSetup.CurrentPrintSetting
            cur_psetting_name = print_mgr.PrintSetup.CurrentPrintSetting.Name
            for psetting in print_settings:
                if psetting.name == cur_psetting_name:
                    self.printsettings_cb.SelectedItem = psetting

        if self.selected_doc.IsLinked:
            self.disable_element(self.printsettings_cb)
        else:
            self.enable_element(self.printsettings_cb)

        self._update_combine_option()

    def _update_combine_option(self):
        self.enable_element(self.combine_cb)
        if self.selected_doc.IsLinked \
                or ((self.selected_schedule and self.selected_print_setting) 
                    and self.selected_print_setting.allows_variable_paper):
            self.disable_element(self.combine_cb)
            self.combine_cb.IsChecked = False

    def _setup_sheet_list(self):
        self.schedules_cb.ItemsSource = self._get_sheet_index_list()
        self.schedules_cb.SelectedIndex = 0
        if self.schedules_cb.ItemsSource:
            self.enable_element(self.schedules_cb)
        else:
            self.disable_element(self.schedules_cb)

    def _print_combined_sheets_in_order(self, target_sheets):
        # make sure we can access the print config
        print_mgr = self._get_printmanager()
        with revit.TransactionGroup('Print Sheets in Order',
                                    doc=self.selected_doc):
            if not print_mgr:
                return
            with revit.Transaction('Set Printer Settings',
                                   doc=self.selected_doc):
                print_mgr.PrintSetup.CurrentPrintSetting = \
                    self.selected_print_setting.print_settings
                print_mgr.SelectNewPrintDriver(self.selected_printer)
                print_mgr.PrintRange = DB.PrintRange.Select
            # add non-printable char in front of sheet Numbers
            # to push revit to sort them per user
            sheet_set = DB.ViewSet()
            original_sheetnums = []
            with revit.Transaction('Fix Sheet Numbers',
                                   doc=self.selected_doc):
                for idx, sheet in enumerate(target_sheets):
                    rvtsheet = sheet.revit_sheet
                    original_sheetnums.append(rvtsheet.SheetNumber)
                    rvtsheet.SheetNumber = \
                        NPC * (idx + 1) + rvtsheet.SheetNumber
                    if sheet.printable:
                        sheet_set.Insert(rvtsheet)

            # Collect existing sheet sets
            cl = DB.FilteredElementCollector(self.selected_doc)
            viewsheetsets = cl.OfClass(framework.get_type(DB.ViewSheetSet))\
                              .WhereElementIsNotElementType()\
                              .ToElements()
            all_viewsheetsets = {vss.Name: vss for vss in viewsheetsets}

            sheetsetname = 'OrderedPrintSet'

            with revit.Transaction('Remove Previous Print Set',
                                   doc=self.selected_doc):
                # Delete existing matching sheet set
                if sheetsetname in all_viewsheetsets:
                    print_mgr.ViewSheetSetting.CurrentViewSheetSet = \
                        all_viewsheetsets[sheetsetname]
                    print_mgr.ViewSheetSetting.Delete()

            with revit.Transaction('Update Ordered Print Set',
                                   doc=self.selected_doc):
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
            print_mgr.PrintToFileName = \
                op.join(r'C:\\', 'Ordered Sheet Set.pdf')
            print_mgr.Apply()
            print_mgr.SubmitPrint()

            # now fix the sheet names
            with revit.Transaction('Restore Sheet Numbers',
                                   doc=self.selected_doc):
                for sheet, sheetnum in zip(target_sheets,
                                           original_sheetnums):
                    rvtsheet = sheet.revit_sheet
                    rvtsheet.SheetNumber = sheetnum

    def _print_sheets_in_order(self, target_sheets):
        # make sure we can access the print config
        print_mgr = self._get_printmanager()
        if not print_mgr:
            return
        print_mgr.PrintToFile = True
        per_sheet_psettings = self.selected_print_setting.allows_variable_paper
        with revit.DryTransaction('Set Printer Settings',
                                  doc=self.selected_doc):
            if not per_sheet_psettings:
                print_mgr.PrintSetup.CurrentPrintSetting = \
                    self.selected_print_setting.print_settings
            print_mgr.SelectNewPrintDriver(self.selected_printer)
            print_mgr.PrintRange = DB.PrintRange.Current
            for sheet in target_sheets:
                if sheet.printable:
                    if sheet.print_filename:
                        print_mgr.PrintToFileName = \
                            op.join(USER_DESKTOP, sheet.print_filename)

                        # set the per-sheet print settings if required
                        if per_sheet_psettings:
                            print_mgr.PrintSetup.CurrentPrintSetting = \
                                sheet.print_settings

                        print_mgr.SubmitPrint(sheet.revit_sheet)
                    else:
                        logger.debug(
                            'Sheet %s does not have a valid file name.',
                            sheet.number)
                else:
                    logger.debug('Sheet %s is not printable. Skipping print.',
                                 sheet.number)

    def _print_linked_sheets_in_order(self, target_sheets):
        # make sure we can access the print config
        print_mgr = self._get_printmanager()
        if not print_mgr:
            return
        print_mgr.PrintToFile = True
        print_mgr.SelectNewPrintDriver(self.selected_printer)
        print_mgr.PrintRange = DB.PrintRange.Current
        # setting print settings needs a transaction
        # can not be done on linked docs
        # print_mgr.PrintSetup.CurrentPrintSetting =
        for sheet in target_sheets:
            if sheet.printable:
                print_mgr.PrintToFileName = \
                    op.join(USER_DESKTOP, sheet.print_filename)
                print_mgr.SubmitPrint(sheet.revit_sheet)
            else:
                logger.debug(
                    'Linked sheet %s is not printable. Skipping print.',
                    sheet.number
                    )

    def _reset_error(self):
        self.enable_element(self.print_b)
        self.hide_element(self.errormsg_block)
        self.errormsg_tb.Text = ''

    def _set_error(self, err_msg):
        if self.errormsg_tb.Text != err_msg:
            self.disable_element(self.print_b)
            self.show_element(self.errormsg_block)
            self.errormsg_tb.Text = err_msg

    def _update_print_indices(self, sheet_list):
        start_idx = self.index_start
        for idx, sheet in enumerate(sheet_list):
            sheet.print_index = INDEX_FORMAT\
                .format(digits=self.index_digits)\
                .format(idx + start_idx)

    def _update_filename_template(self, template, value_type, value_getter):
        finder_pattern = r'{' + value_type + r':(.*?)}'
        for param_name in re.findall(finder_pattern, template):
            param_value = value_getter(param_name)
            repl_pattern = r'{' + value_type + ':' + param_name + r'}'
            if param_value:
                template = re.sub(repl_pattern, str(param_value), template)
            template = re.sub(repl_pattern, '', template)
        return template

    def _update_print_filename(self, template, sheet):
        # resolve sheet-level custom param values
        ## get titleblock param values
        template = self._update_filename_template(
            template=template,
            value_type='tblock_param',
            value_getter=lambda x: revit.query.get_param_value(
                revit.query.get_param(sheet.revit_tblock, x)
                )
        )

        ## get sheet param values
        template = self._update_filename_template(
            template=template,
            value_type='sheet_param',
            value_getter=lambda x: revit.query.get_param_value(
                revit.query.get_param(sheet.revit_sheet, x)
                )
        )

        # resolved the fixed formatters
        try:
            output_fname = \
                template.format(
                    index=sheet.print_index,
                    number=sheet.number,
                    name=sheet.name,
                    name_dash=sheet.name.replace(' ', '-'),
                    name_underline=sheet.name.replace(' ', '_'),
                    issue_date=sheet.issue_date,
                    rev_number=sheet.revision.number if sheet.revision else '',
                    rev_desc=sheet.revision.desc if sheet.revision else '',
                    rev_date=sheet.revision.date if sheet.revision else '',
                    proj_name=self.project_info.name,
                    proj_number=self.project_info.number,
                    proj_building_name=self.project_info.building_name,
                    proj_issue_date=self.project_info.issue_date,
                    proj_org_name=self.project_info.org_name,
                    proj_status=self.project_info.status,
                    username=HOST_APP.username,
                    revit_version=HOST_APP.version,
                )
        except Exception as ferr:
            output_fname = ''
            if isinstance(ferr, KeyError):
                self._set_error('Unknown key in selected naming format')
        # and set the sheet file name
        sheet.print_filename = output_fname

    def _update_print_filenames(self, sheet_list):
        doc = self.selected_doc
        naming_fmt = self.selected_naming_format
        if naming_fmt:
            template = naming_fmt.template
            # resolve project-level custom param values
            ## project info param values
            template = self._update_filename_template(
                template=template,
                value_type='proj_param',
                value_getter=lambda x: revit.query.get_param_value(
                    doc.ProjectInformation.LookupParameter(x)
                    )
            )

            ## global param values
            template = self._update_filename_template(
                template=template,
                value_type='glob_param',
                value_getter=lambda x: revit.query.get_param_value(
                    revit.query.get_global_parameter(x, doc=doc)
                    )
            )

            for sheet in sheet_list:
                self._update_print_filename(template, sheet)

    def _find_sheet_tblock(self, revit_sheet, tblocks):
        for tblock in tblocks:
            view_sheet = revit_sheet.Document.GetElement(tblock.OwnerViewId)
            if view_sheet.Id == revit_sheet.Id:
                return tblock

    def _get_sheet_printsettings(self, tblocks):
        tblock_printsettings = {}
        sheet_printsettings = {}
        doc_printsettings = \
            revit.query.get_all_print_settings(doc=self.selected_doc)
        for tblock in tblocks:
            sheet = self.selected_doc.GetElement(tblock.OwnerViewId)
            # build a unique id for this tblock
            tblock_tform = tblock.GetTotalTransform()
            tblock_tid = tblock.GetTypeId().IntegerValue
            tblock_tid = tblock_tid * 100 \
                         + tblock_tform.BasisX.X * 10 \
                         + tblock_tform.BasisX.Y
            tblock_psetting = tblock_printsettings.get(tblock_tid, None)
            if not tblock_psetting:
                tblock_psetting = \
                    revit.query.get_sheet_print_settings(tblock,
                                                         doc_printsettings)
                tblock_printsettings[tblock_tid] = tblock_psetting
            if tblock_psetting:
                sheet_printsettings[sheet.SheetNumber] = tblock_psetting
        return sheet_printsettings

    def _reset_psettings(self):
        if self._init_psettings:
            print_mgr = self._get_printmanager()
            print_mgr.PrintSetup.CurrentPrintSetting = self._init_psettings

    def _update_index_slider(self):
        index_digits = \
            int(len(str(len(self._scheduled_sheets) + self.index_start)))
        self.index_slider.Minimum = max([index_digits, 2])
        self.index_slider.Maximum = self.index_slider.Minimum + 3

    # event handlers
    def doclist_changed(self, sender, args):
        self.project_info = revit.query.get_project_info(doc=self.selected_doc)
        self._setup_printers()
        self._setup_print_settings()
        self._setup_sheet_list()

    def sheetlist_changed(self, sender, args):
        print_settings = None
        tblocks = revit.query.get_elements_by_categories(
            [DB.BuiltInCategory.OST_TitleBlocks],
            doc=self.selected_doc
        )
        if self.selected_schedule and self.selected_print_setting:
            if self.selected_print_setting.allows_variable_paper:
                sheet_printsettings = self._get_sheet_printsettings(tblocks)
                self.show_element(self.sheetopts_wp)
                self.show_element(self.psettingcol)
                self._scheduled_sheets = [
                    ViewSheetListItem(
                        view_sheet=x,
                        view_tblock=self._find_sheet_tblock(x, tblocks),
                        print_settings=sheet_printsettings.get(
                            x.SheetNumber,
                            None))
                    for x in self._get_ordered_schedule_sheets()
                    ]
            else:
                print_settings = self.selected_print_setting.print_settings
                self.hide_element(self.sheetopts_wp)
                self.hide_element(self.psettingcol)
                self._scheduled_sheets = [
                    ViewSheetListItem(
                        view_sheet=x,
                        view_tblock=self._find_sheet_tblock(x, tblocks),
                        print_settings=[print_settings])
                    for x in self._get_ordered_schedule_sheets()
                    ]
        self._update_combine_option()
        # self._update_index_slider()
        self.options_changed(None, None)

    def options_changed(self, sender, args):
        self._reset_error()

        # update index digit range
        self._update_index_slider()

        # reverse sheet if reverse is set
        sheet_list = [x for x in self._scheduled_sheets]
        if self.reverse_print:
            sheet_list.reverse()

        if self.combine_cb.IsChecked:
            self.hide_element(self.order_sp)
            self.hide_element(self.namingformat_dp)
            self.hide_element(self.pfilename)
        else:
            self.show_element(self.order_sp)
            self.show_element(self.namingformat_dp)
            self.show_element(self.pfilename)

        # decide whether to show the placeholders or not
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

        # update sheet naming formats
        self._update_print_filenames(sheet_list)

    def set_sheet_printsettings(self, sender, args):
        if self.selected_printable_sheets:
            psettings = forms.SelectFromList.show(
                {
                    'Matching Print Settings':
                        self.selected_printable_sheets[0].all_print_settings,
                    'All Print Settings':
                        revit.query.get_all_print_settings(
                            doc=self.selected_doc
                            )
                },
                name_attr='Name',
                group_selector_title='Print Settings:',
                default_group='Matching Print Settings',
                title='Select Print Setting',
                width=350, height=400
                )
            if psettings:
                for sheet in self.selected_printable_sheets:
                    sheet.print_settings = psettings

    def sheet_selection_changed(self, sender, args):
        if self.selected_printable_sheets:
            return self.enable_element(self.sheetopts_wp)
        self.disable_element(self.sheetopts_wp)

    def validate_index_start(self, sender, args):
        args.Handled = re.match(r'[^0-9]+', args.Text)

    def rest_index(self, sender, args):
        self.indexstart_tb.Text = '0'

    def edit_formats(self, sender, args):
        editfmt_wnd = \
            EditNamingFormatsWindow(
                'EditNamingFormats.xaml',
                start_with=self.selected_naming_format
                )
        editfmt_wnd.show_dialog()
        self.namingformat_cb.ItemsSource = editfmt_wnd.naming_formats
        self.namingformat_cb.SelectedItem = editfmt_wnd.selected_naming_format

    def print_sheets(self, sender, args):
        if self.sheet_list:
            selected_only = False
            if self.selected_sheets:
                opts = forms.alert(
                    "You have a series of sheets selected. Do you want to "
                    "print the selected sheets or all sheets?",
                    options=["Only Selected Sheets", "All Scheduled Sheets"]
                    )
                selected_only = opts == "Only Selected Sheets"

            target_sheets = \
                self.selected_sheets if selected_only else self.sheet_list

            if not self.combine_print:
                printable_count = len([x for x in target_sheets if x.printable])
                if printable_count > 5:
                    # prepare warning message
                    sheet_count = len(target_sheets)
                    message = str(printable_count)
                    if printable_count != sheet_count:
                        message += ' (out of {} total)'.format(sheet_count)

                    if not forms.alert('Are you sure you want to print {} '
                                       'sheets individually? The process can '
                                       'not be cancelled.'.format(message),
                                       ok=False, yes=True, no=True):
                        return
            self.Close()
            if self.combine_print:
                self._print_combined_sheets_in_order(target_sheets)
            else:
                if self.selected_doc.IsLinked:
                    self._print_linked_sheets_in_order(target_sheets)
                else:
                    self._print_sheets_in_order(target_sheets)
            self._reset_psettings()


def cleanup_sheetnumbers(doc):
    sheets = revit.query.get_sheets(doc=doc)
    with revit.Transaction('Cleanup Sheet Numbers', doc=doc):
        for sheet in sheets:
            sheet.SheetNumber = sheet.SheetNumber.replace(NPC, '')

# TODO: add copy filenames to sheet list
if __shiftclick__:  #pylint: disable=E0602
    open_docs = forms.select_open_docs()
    for open_doc in open_docs:
        cleanup_sheetnumbers(open_doc)
else:
    PrintSheetsWindow('PrintSheets.xaml').ShowDialog()
