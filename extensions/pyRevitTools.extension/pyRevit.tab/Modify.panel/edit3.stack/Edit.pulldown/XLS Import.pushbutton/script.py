import os
import xlrd
import re

from pyrevit import script, forms, revit, HOST_APP
from pyrevit import DB
from pyrevit.revit import get_parameter_data_type, is_yesno_parameter
from pyrevit.compat import get_elementid_value_func, get_elementid_from_value_func

get_elementid_value = get_elementid_value_func()
get_elementid_from_value = get_elementid_from_value_func()

logger = script.get_logger()
doc = HOST_APP.doc
project_units = doc.GetUnits()

script.get_output().close_others()

unit_postfix_pattern = re.compile(r"\s*\[.*\]$")


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

    metadata = load_metadata(workbook)

    with revit.Transaction("Import Parameters from Excel"):
        for row_idx in range(1, sheet.nrows):
            row = sheet.row_values(row_idx)
            try:
                el_id_val = int(row[0])
                el = doc.GetElement(get_elementid_from_value(el_id_val))
                if not el:
                    logger.warning("Element with ID {} not found.".format(el_id_val))
                    continue

                for col_idx, param_name_raw in enumerate(param_names):
                    new_val = row[col_idx + 1]
                    if new_val in (None, ""):
                        continue

                    param_name = unit_postfix_pattern.sub("", param_name_raw).strip()
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
                                if get_elementid_value(param.Id) == int(
                                    DB.BuiltInParameter.ELEM_PARTITION_PARAM
                                ):
                                    try:
                                        ws_name = str(new_val)
                                        ws = revit.query.find_workset(ws_name)
                                        if ws:
                                            param.Set(ws.Id.IntegerValue)
                                        else:
                                            logger.warning("Workset {} not found".format(ws_name))
                                    except Exception:
                                        logger.warning("Failed to set Workset for {}".format(el_id_val))
                                elif is_yesno_parameter(param.Definition):
                                    try:
                                        str_val = str(new_val).strip().lower()
                                        int_val = (
                                            1 if str_val in ("yes", "1", "true") else 0
                                        )
                                    except (AttributeError, TypeError):
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
                            unit_type_id = None
                            if param_name in metadata:
                                forge_type_id, meta_unit_id, _, is_override = metadata[
                                    param_name
                                ]
                                if meta_unit_id:
                                    unit_type_id = meta_unit_id
                                    logger.debug(
                                        "Using metadata unit for '{}': {} (override: {})".format(
                                            param_name, unit_type_id.TypeId, is_override
                                        )
                                    )

                            # Fallback to project units if no metadata
                            if not unit_type_id:
                                forge_type_id = get_parameter_data_type(
                                    param.Definition
                                )
                                if forge_type_id and DB.UnitUtils.IsMeasurableSpec(
                                    forge_type_id
                                ):
                                    try:
                                        unit_type_id = project_units.GetFormatOptions(
                                            forge_type_id
                                        ).GetUnitTypeId()
                                        logger.debug(
                                            "Using project unit for '{}': {}".format(
                                                param_name,
                                                (
                                                    unit_type_id.TypeId
                                                    if unit_type_id
                                                    else "none"
                                                ),
                                            )
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            "Could not get project unit for '{}': {}".format(
                                                param_name, e
                                            )
                                        )

                            if unit_type_id:
                                try:
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
                            try:
                                bic = doc.GetElement(param.AsElementId()).Category.BuiltInCategory
                                collector = revit.query.get_elements_by_categories([bic])
                                for bic_el in collector:
                                    if bic_el.Name == new_val:
                                        found_id = bic_el.Id
                                        break
                                if found_id:
                                    param.Set(found_id)
                                else:
                                    raise Exception
                            except Exception:
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
