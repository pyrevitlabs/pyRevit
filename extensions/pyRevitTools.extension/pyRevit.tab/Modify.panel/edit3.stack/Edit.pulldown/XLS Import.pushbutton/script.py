import os
import xlrd
import re

from pyrevit import script, forms, revit, HOST_APP
from pyrevit import DB
from pyrevit.revit import get_parameter_data_type, is_yesno_parameter
from pyrevit.compat import get_elementid_from_value_func

get_elementid_from_value = get_elementid_from_value_func()

logger = script.get_logger()
doc = revit.doc
project_units = doc.GetUnits()

script.get_output().close_others()

unit_postfix_pattern = re.compile(r"\s*\[.*\]$")


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

    param_names = headers[1:]

    with revit.Transaction("Import Parameters from Excel"):
        for row_idx in range(1, sheet.nrows):
            row = sheet.row_values(row_idx)
            try:
                el_id_val = int(row[0])
                el = doc.GetElement(get_elementid_from_value(el_id_val))
                if not el:
                    logger.warning("Element with ID {} not found.".format(el_id_val))
                    continue

                for col_idx, param_name in enumerate(param_names):
                    new_val = row[col_idx + 1]
                    if new_val in (None, ""):
                        continue

                    param_name = unit_postfix_pattern.sub("", param_name).strip()
                    param = el.LookupParameter(param_name)
                    if not param:
                        logger.info(
                            "Parameter '{}' not found on element {}.".format(
                                param_name, el_id_val
                            )
                        )
                        continue

                    if param.IsReadOnly:
                        logger.info(
                            "Parameter '{}' on element {} is read-only.".format(
                                param_name, el_id_val
                            )
                        )
                        continue

                    try:
                        storage_type = param.StorageType
                        if storage_type == DB.StorageType.String:
                            param.Set(str(new_val))
                        elif storage_type == DB.StorageType.Integer:
                            try:
                                if is_yesno_parameter(param.Definition):
                                    # Handle Yes/No as string or numeric
                                    try:
                                        # Check if it's a string-like type
                                        str_val = str(new_val).strip().lower()
                                        int_val = 1 if str_val in ("yes", "1", "true") else 0
                                    except (AttributeError, TypeError):
                                        # Not a string, treat as numeric
                                        int_val = int(float(new_val))
                                    param.Set(int_val)
                                else:
                                    param.Set(int(float(new_val)))
                            except (ValueError, TypeError) as e:
                                logger.warning(
                                    "Invalid integer value '{}' for parameter '{}' on element {}: {}".format(
                                        new_val, param_name, el_id_val, e
                                    )
                                )
                        elif storage_type == DB.StorageType.Double:
                            forge_type_id = get_parameter_data_type(param.Definition)
                            if forge_type_id and DB.UnitUtils.IsMeasurableSpec(forge_type_id):
                                try:
                                    unit_type_id = project_units.GetFormatOptions(
                                        forge_type_id
                                    ).GetUnitTypeId()
                                    new_val = DB.UnitUtils.ConvertToInternalUnits(
                                        float(new_val), unit_type_id
                                    )
                                    param.Set(new_val)
                                except Exception as e:
                                    logger.error(
                                        "Failed to set converted value for '{}': {}".format(
                                            param_name, e
                                        )
                                    )
                            else:
                                param.Set(float(new_val))
                        elif storage_type == DB.StorageType.ElementId:
                            logger.info(
                                "Skipping ElementId parameter '{}': not supported.".format(
                                    param_name
                                )
                            )

                        else:
                            logger.warning(
                                "Unknown storage type for parameter '{}'.".format(
                                    param_name
                                )
                            )
                    except Exception as e:
                        logger.error(
                            "Failed to set '{}' on element {}: {}".format(
                                param_name, el_id_val, e
                            )
                        )

            except Exception as e:
                logger.error("Error processing row {}: {}".format(row_idx + 1, e))

    logger.info("Import complete.")


if __name__ == "__main__":
    main()
