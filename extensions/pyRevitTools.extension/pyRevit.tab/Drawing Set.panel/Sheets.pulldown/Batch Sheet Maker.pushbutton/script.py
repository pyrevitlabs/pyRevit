import re
from collections import Counter

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()

NUMBER_AND_NAME_PARAMETERS = (
    DB.BuiltInParameter.SHEET_NUMBER,
    DB.BuiltInParameter.SHEET_NAME,
)


class SheetParameterEntry(forms.Reactive):
    """A sheet parameter row in the window, ticked when it should be set.

    Typing a value ticks the row automatically; unticking afterwards keeps
    the value but excludes the parameter from the batch.
    """

    def __init__(self, name, parameter_id):
        self._name = name
        self.parameter_id = parameter_id
        self._value = ""
        self._is_selected = False

    @property
    def name(self):
        """Parameter name."""
        return self._name

    @forms.reactive
    def value(self):
        """Value to set on every sheet."""
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        if new_value:
            self.is_selected = True

    @forms.reactive
    def is_selected(self):
        """Whether the parameter is set on the created sheets."""
        return self._is_selected

    @is_selected.setter
    def is_selected(self, new_value):
        self._is_selected = new_value


def get_sheet_text_parameters(doc):
    """Return (display name, parameter id) pairs of writable text parameters.

    Sheet number and sheet name are excluded, they are always set by the tool.
    Parameters sharing a name get their id appended to the display name so
    each can be told apart and targeted by id.

    Note:
        Parameters are read from a probe sheet created in a transaction that
        is always rolled back, so the list also works in projects without any
        sheet and leaves the model untouched.
    """
    transaction = DB.Transaction(doc, "Probe Sheet Parameters")
    transaction.Start()
    try:
        probe_sheet = DB.ViewSheet.Create(doc, DB.ElementId.InvalidElementId)
        found = []
        for param in probe_sheet.Parameters:
            if param.IsReadOnly or param.StorageType != DB.StorageType.String:
                continue
            if (
                getattr(param.Definition, "BuiltInParameter", None)
                in NUMBER_AND_NAME_PARAMETERS
            ):
                continue
            found.append((param.Definition.Name, param.Id))
        name_counts = Counter(name for name, _ in found)
        return sorted(
            (
                name if name_counts[name] == 1 else "{} ({})".format(name, param_id),
                param_id,
            )
            for name, param_id in found
        )
    finally:
        transaction.RollBack()


class BatchSheetMakerWindow(forms.WPFWindow):
    resolve_theme = True

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._sheet_dict = {}
        self._titleblock_id = None
        self._parameter_values = []
        self._parameter_entries = [
            SheetParameterEntry(name, parameter_id)
            for name, parameter_id in get_sheet_text_parameters(revit.doc)
        ]
        self.parameters_ic.ItemsSource = self._parameter_entries
        self.sheets_tb.Focus()

    def _process_sheet_code(self):
        for sheet_code in str(self.sheets_tb.Text).split("\n"):
            if coreutils.is_blank(sheet_code):
                continue

            if "\t" not in sheet_code:
                logger.warning(
                    "Sheet name must be separated from "
                    "sheet number by a single tab: {}".format(sheet_code)
                )
                return False

            sheet_code = re.sub("\t+", "\t", sheet_code)
            sheet_code = sheet_code.replace("\n", "").replace("\r", "")
            num, name = sheet_code.split("\t")
            try:
                for range_num in coreutils.extract_range(num):
                    self._sheet_dict[range_num] = name
            except Exception as range_err:
                logger.error(range_err)
                return False

        return True

    def _ask_for_titleblock(self):
        tblock = forms.select_titleblocks(doc=revit.doc)
        if tblock is not None:
            self._titleblock_id = tblock
            return True

        return False

    @staticmethod
    def _find_parameter(sheet, parameter_id):
        for param in sheet.Parameters:
            if param.Id == parameter_id:
                return param

    def _apply_parameter_values(self, sheet):
        for entry in self._parameter_values:
            param = self._find_parameter(sheet, entry.parameter_id)
            if param is None or param.IsReadOnly or not param.Set(entry.value):
                logger.warning(
                    "Could not set parameter {} on sheet {}".format(
                        entry.name, sheet.SheetNumber
                    )
                )

    def _create_placeholder(self, sheet_num, sheet_name):
        with DB.Transaction(revit.doc, "Create Placeholder") as t:
            try:
                t.Start()
                new_phsheet = DB.ViewSheet.CreatePlaceholder(revit.doc)
                new_phsheet.Name = sheet_name
                new_phsheet.SheetNumber = sheet_num
                self._apply_parameter_values(new_phsheet)
                t.Commit()
            except Exception as create_err:
                t.RollBack()
                logger.error(
                    "Error creating placeholder sheet {}:{} | {}".format(
                        sheet_num, sheet_name, create_err
                    )
                )

    def _create_sheet(self, sheet_num, sheet_name):
        with DB.Transaction(revit.doc, "Create Sheet") as t:
            try:
                t.Start()
                new_phsheet = DB.ViewSheet.Create(revit.doc, self._titleblock_id)
                new_phsheet.Name = sheet_name
                new_phsheet.SheetNumber = sheet_num
                self._apply_parameter_values(new_phsheet)
                t.Commit()
            except Exception as create_err:
                t.RollBack()
                logger.error(
                    "Error creating sheet sheet {}:{} | {}".format(
                        sheet_num, sheet_name, create_err
                    )
                )

    def create_sheets(self, sender, args):
        self._parameter_values = [
            entry for entry in self._parameter_entries if entry.is_selected
        ]
        self.Close()

        if self._process_sheet_code():
            if self.sheet_cb.IsChecked:
                create_func = self._create_sheet
                transaction_msg = "Batch Create Sheets"
                if not self._ask_for_titleblock():
                    script.exit()
            else:
                create_func = self._create_placeholder
                transaction_msg = "Batch Create Placeholders"

            with DB.TransactionGroup(revit.doc, transaction_msg) as tg:
                tg.Start()
                for sheet_num, sheet_name in self._sheet_dict.items():
                    logger.debug("Creating Sheet: {}:{}".format(sheet_num, sheet_name))
                    create_func(sheet_num, sheet_name)
                tg.Assimilate()
        else:
            logger.error("Aborted with errors.")


BatchSheetMakerWindow("BatchSheetMakerWindow.xaml").ShowDialog()
