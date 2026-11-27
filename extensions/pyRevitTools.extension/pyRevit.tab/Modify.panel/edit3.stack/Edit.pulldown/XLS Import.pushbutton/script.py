import os
import xlrd
import re
from collections import Counter, namedtuple

from pyrevit import script, forms, revit, HOST_APP
from pyrevit import DB
from pyrevit.revit import get_parameter_data_type
from pyrevit.revit.units import ValueRefused, decimal_symbol
from pyrevit.revit.valuecodec import UNIT_NUMBER, ValueCodec, as_text
from pyrevit.compat import get_elementid_from_value_func

get_elementid_from_value = get_elementid_from_value_func()

logger = script.get_logger()
output = script.get_output()
doc = HOST_APP.doc
project_units = doc.GetUnits()

output.close_others()

unit_postfix_pattern = re.compile(r"\s*\[.*\]$")
unit_tag_pattern = re.compile(r"\s*\[(.*)\]$")

SKIP_READ_ONLY = "read-only"
SKIP_NOT_FOUND = "parameter not found"
SKIP_INVALID = "invalid value"

Column = namedtuple("Column", ["name", "unit_tag"])


def load_metadata(workbook):
    """
    Load unit metadata from the _metadata sheet if it exists.
    Returns a dict {param_name: (forge_type_id, unit_type_id, symbol_type_id, is_schedule_override)}
    """
    metadata = {}
    try:
        metadata_sheet = workbook.sheet_by_name("_metadata")
        for row_idx in range(1, metadata_sheet.nrows):
            row = metadata_sheet.row_values(row_idx)
            if len(row) < 5:
                continue

            param_name = row[0]
            forge_type_id_str = row[1]
            unit_type_id_str = row[2]
            symbol_type_id_str = row[3]
            is_override = row[4]

            forge_type_id = None
            unit_type_id = None
            symbol_type_id = None

            if forge_type_id_str:
                try:
                    forge_type_id = DB.ForgeTypeId(str(forge_type_id_str))
                except Exception:
                    logger.warning(
                        "Could not reconstruct ForgeTypeId for '{}': {}".format(
                            param_name, forge_type_id_str
                        )
                    )

            if unit_type_id_str:
                try:
                    unit_type_id = DB.ForgeTypeId(str(unit_type_id_str))
                except Exception:
                    logger.warning(
                        "Could not reconstruct UnitTypeId for '{}': {}".format(
                            param_name, unit_type_id_str
                        )
                    )

            if symbol_type_id_str:
                try:
                    symbol_type_id = DB.ForgeTypeId(str(symbol_type_id_str))
                except Exception:
                    pass

            metadata[param_name] = (
                forge_type_id,
                unit_type_id,
                symbol_type_id,
                str(is_override).lower() in ("yes", "true", "1"),
            )

        logger.info("Loaded metadata for {} parameters".format(len(metadata)))
    except Exception as e:
        logger.info("No metadata sheet found or error reading it: {}".format(e))

    return metadata


def parse_column(header):
    """Split a header cell into the parameter name and its unit tag."""
    header = as_text(header)
    tag_match = unit_tag_pattern.search(header)
    unit_tag = tag_match.group(1).strip() if tag_match else ""
    return Column(unit_postfix_pattern.sub("", header).strip(), unit_tag)


class ImportSummary(object):
    """Counts what an import did so that it can be reported once at the end."""

    def __init__(self):
        self.rows_read = 0
        self.rows_without_element = 0
        self.values_set = 0
        self.blank_cells = 0
        self.skipped = {
            SKIP_READ_ONLY: Counter(),
            SKIP_NOT_FOUND: Counter(),
            SKIP_INVALID: Counter(),
        }

    def skip(self, reason, param_name):
        self.skipped[reason][param_name] += 1

    def print_report(self):
        lines = [
            "**Import complete.**",
            "",
            "- Rows read: {}".format(self.rows_read),
            "- Values set: {}".format(self.values_set),
        ]
        if self.rows_without_element:
            lines.append(
                "- Rows skipped, element not found: {}".format(
                    self.rows_without_element
                )
            )
        for reason in (SKIP_READ_ONLY, SKIP_NOT_FOUND, SKIP_INVALID):
            counts = self.skipped[reason]
            if counts:
                names = ", ".join(
                    "`{}` ({})".format(name.replace("`", "'"), count)
                    for name, count in sorted(counts.items(), key=lambda item: item[0])
                )
                lines.append(
                    "- Cells skipped, {}: {} - {}".format(
                        reason, sum(counts.values()), names
                    )
                )
        lines.append(
            "- Blank cells: {} (ignored, a blank cell never clears a value)".format(
                self.blank_cells
            )
        )
        lines.append(
            "- Units: from the `_metadata` sheet where it lists one for the "
            "parameter, otherwise from the column header symbol, otherwise "
            "project units"
        )
        lines.append(
            "- Numbers in text cells: the project's decimal symbol (`{}`) "
            "applies, and text with a unit is read by Revit".format(decimal_symbol(doc))
        )
        output.print_md("\n".join(lines))


class ParameterWriter(object):
    """Writes an Excel cell into a parameter through the shared value codec.

    The script only adds what the workbook knows: the unit that a number is
    expressed in. A rejected value raises ``ValueRefused`` and leaves the
    parameter untouched; any other exception comes from Revit.
    """

    def __init__(self, metadata):
        self.metadata = metadata
        self.codec = ValueCodec(doc, UNIT_NUMBER)
        self.unit_ids_by_symbol = {}
        self.warned_unit_tags = set()

    def write(self, param, column, cell_value):
        unit_type_id = None
        if param.StorageType == DB.StorageType.Double:
            unit_type_id = self.get_unit_type_id(param, column)
        self.codec.write(param, cell_value, unit_id=unit_type_id)

    def get_unit_type_id(self, param, column):
        """Pick the unit the cell is expressed in.

        Order: the ``_metadata`` sheet, then the unit symbol in the column
        header. Each counts only if it is a unit of this parameter. None means
        the project units.
        """
        forge_type_id = get_parameter_data_type(param.Definition)
        if not (forge_type_id and DB.UnitUtils.IsMeasurableSpec(forge_type_id)):
            return None

        metadata_entry = self.metadata.get(column.name)
        if (
            metadata_entry
            and metadata_entry[1]
            and DB.UnitUtils.IsValidUnit(forge_type_id, metadata_entry[1])
        ):
            return metadata_entry[1]

        if not column.unit_tag:
            return None
        project_unit_id = project_units.GetFormatOptions(forge_type_id).GetUnitTypeId()
        header_unit_id = self.find_unit_by_symbol(
            forge_type_id, column.unit_tag, project_unit_id
        )
        if header_unit_id:
            return header_unit_id
        if (column.name, column.unit_tag) not in self.warned_unit_tags:
            self.warned_unit_tags.add((column.name, column.unit_tag))
            logger.warning(
                "Unit '[{}]' in the header of '{}' is not a unit of this "
                "parameter. Project units are assumed.".format(
                    column.unit_tag, column.name
                )
            )
        return None

    def find_unit_by_symbol(self, forge_type_id, unit_tag, project_unit_id):
        cache_key = (forge_type_id.TypeId, unit_tag)
        if cache_key not in self.unit_ids_by_symbol:
            matching_unit_ids = []
            for unit_id in DB.UnitUtils.GetValidUnits(forge_type_id):
                for symbol_id in DB.FormatOptions.GetValidSymbols(unit_id):
                    if self.get_symbol_label(symbol_id) == unit_tag:
                        matching_unit_ids.append(unit_id)
                        break
            project_matches = [
                unit_id
                for unit_id in matching_unit_ids
                if unit_id.TypeId == project_unit_id.TypeId
            ]
            chosen = project_matches or matching_unit_ids
            self.unit_ids_by_symbol[cache_key] = chosen[0] if chosen else None
        return self.unit_ids_by_symbol[cache_key]

    @staticmethod
    def get_symbol_label(symbol_id):
        if symbol_id.Empty():
            return None
        try:
            return DB.LabelUtils.GetLabelForSymbol(symbol_id)
        except Exception:
            return None


def main():
    file_path = forms.pick_file(file_ext="xlsx", restore_dir=True)
    if not file_path or not os.path.exists(file_path):
        return

    try:
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_name("Export")
    except Exception as e:
        logger.error("Failed to open Excel file: {}".format(e))
        return

    headers = sheet.row_values(0)
    if not headers or headers[0] != "ElementId":
        logger.error("First column must be 'ElementId'.")
        return

    columns = [parse_column(header) for header in headers[1:]]

    metadata = load_metadata(workbook)
    writer = ParameterWriter(metadata)
    summary = ImportSummary()

    with revit.Transaction("Import Parameters from Excel"):
        for row_idx in range(1, sheet.nrows):
            summary.rows_read += 1
            row = sheet.row_values(row_idx)
            try:
                el_id_val = int(row[0])
                el = doc.GetElement(get_elementid_from_value(el_id_val))
                if not el:
                    logger.warning("Element with ID {} not found.".format(el_id_val))
                    summary.rows_without_element += 1
                    continue

                for col_idx, column in enumerate(columns):
                    cell_value = row[col_idx + 1]
                    if cell_value in (None, ""):
                        summary.blank_cells += 1
                        continue

                    param = el.LookupParameter(column.name)
                    if not param:
                        logger.info(
                            "Parameter '{}' not found on element {}.".format(
                                column.name, el_id_val
                            )
                        )
                        summary.skip(SKIP_NOT_FOUND, column.name)
                        continue

                    if param.IsReadOnly:
                        logger.info(
                            "Parameter '{}' on element {} is read-only.".format(
                                column.name, el_id_val
                            )
                        )
                        summary.skip(SKIP_READ_ONLY, column.name)
                        continue

                    try:
                        writer.write(param, column, cell_value)
                        summary.values_set += 1
                    except ValueRefused as e:
                        logger.warning(
                            "Cannot set '{}' on element {}: {}".format(
                                column.name, el_id_val, e
                            )
                        )
                        summary.skip(SKIP_INVALID, column.name)
                    except Exception as e:
                        logger.error(
                            "Failed to set '{}' on element {}: {}".format(
                                column.name, el_id_val, e
                            )
                        )
                        summary.skip(SKIP_INVALID, column.name)

            except Exception as e:
                logger.error("Error processing row {}: {}".format(row_idx + 1, e))

    summary.print_report()


if __name__ == "__main__":
    main()
