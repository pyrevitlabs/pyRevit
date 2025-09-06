import os
import xlrd

from pyrevit import script, forms, revit
from pyrevit import DB

logger = script.get_logger()
doc = revit.doc


def main():
    # 1. Ask for file path
    file_path = forms.pick_file(file_ext="xlsx", restore_dir=True)
    if not file_path or not os.path.exists(file_path):
        logger.warning("No valid file selected.")
        return

    # 2. Open workbook using xlrd
    try:
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_name("Export")
    except Exception as e:
        logger.error("Failed to open Excel file: {}".format(e))
        return

    # 3. Read header row
    headers = sheet.row_values(0)
    if not headers or headers[0] != "ElementId":
        logger.error("First column must be 'ElementId'.")
        return

    param_names = headers[1:]

    # 4. Start transaction
    with revit.Transaction("Import Parameters from Excel"):
        for row_idx in range(1, sheet.nrows):
            row = sheet.row_values(row_idx)
            try:
                el_id_val = int(row[0])
                el = doc.GetElement(DB.ElementId(el_id_val))
                if not el:
                    logger.warning("Element with ID {} not found.".format(el_id_val))
                    continue

                for col_idx, param_name in enumerate(param_names):
                    new_val = row[col_idx + 1]
                    if new_val in (None, ""):
                        continue

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

                    # Try to convert and set value
                    try:
                        storage_type = param.StorageType
                        if storage_type == DB.StorageType.String:
                            param.Set(str(new_val))
                        elif storage_type == DB.StorageType.Integer:
                            param.Set(int(float(new_val)))
                        elif storage_type == DB.StorageType.Double:
                            try:
                                param.SetValueString(str(new_val))  # converts from project units string
                            except Exception as e:
                                logger.error("Failed SetValueString for '{}': {}".format(param_name, e))
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
