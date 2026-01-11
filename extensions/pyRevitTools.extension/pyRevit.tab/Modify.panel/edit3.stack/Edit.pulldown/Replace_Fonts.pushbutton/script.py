# -*- coding: UTF-8 -*-
import System
import re

from rpw.ui.forms import (
    FlexForm,
    Label,
    ComboBox,
    Separator,
    Button,
    CheckBox,
)

from pyrevit import script, DB, HOST_APP, revit
from pyrevit.forms import alert, ProgressBar
from pyrevit.revit.db.create import FamilyLoaderOptionsHandler
from pyrevit.compat import get_elementid_value_func

output = script.get_output()
logger = script.get_logger()

get_elementid_value = get_elementid_value_func()


def rename_element_type_if_needed(element_type, old_font, new_font_name):
    # type: (DB.ElementType, str, str) -> None
    """Renames an element type if its name contains the old font name (case-insensitive).
    Args:
        element_type (DB.ElementType): The element type to rename.
        old_font (str): The old font name.
        new_font_name (str): The new font name.
    Returns:
        None
    """
    current_name = DB.Element.Name.GetValue(element_type)
    # Use case-insensitive check to see if the old font name is part of the type name
    if old_font.lower() in current_name.lower():
        # Use case-insensitive replace
        new_name = current_name  # fallback value
        try:
            new_name = re.sub(re.escape(old_font), new_font_name, current_name, flags=re.IGNORECASE)
            if new_name != current_name:
                DB.Element.Name.SetValue(element_type, new_name)
                logger.debug("Renamed type from '{}' to '{}'".format(current_name, new_name))
        except Exception as e:
            # Log error if renaming fails, but don't stop the script
            logger.error("Failed to rename type '{}' to '{}': {}".format(current_name, new_name, e))


def update_nested_generic_annotations(host_family_doc, font_name):
    # type: (DB.Document, str) -> tuple[list[tuple[str, str, str]], bool]
    """
    Recursively finds and updates fonts in nested generic annotation families.
    Args:
        host_family_doc (DB.Document): The host family document.
        font_name (str): The new font name.
    Returns:
        tuple: A tuple containing:
            - result (list): A list of tuples with details of updated elements.
            - found (bool): A boolean indicating if any updates were made.
    """
    results = []
    found_in_any_nested = False

    # Find nested families of category "Generic Annotation"
    nested_families = [
        f
        for f in DB.FilteredElementCollector(host_family_doc)
        .OfClass(DB.Family)
        .ToElements()
        if f.FamilyCategory
        and get_elementid_value(f.FamilyCategory.Id)
        == int(DB.BuiltInCategory.OST_GenericAnnotation)
    ]

    for nested_family in nested_families:
        if not nested_family.IsEditable:
            continue
        nested_family_doc = None
        try:
            nested_family_doc = host_family_doc.EditFamily(nested_family)
            found_in_this_nested = False

            # Update text types within this nested family
            bip = DB.BuiltInParameter.TEXT_FONT
            element_types = (
                DB.FilteredElementCollector(nested_family_doc)
                .OfClass(DB.ElementType)
                .ToElements()
            )

            with revit.Transaction("Update Font in Nested Family", nested_family_doc):
                for et in element_types:
                    param = et.get_Parameter(bip)
                    if param and param.HasValue:
                        old_font = param.AsString()
                        if old_font != font_name:
                            rename_element_type_if_needed(et, old_font, font_name)
                            param.Set(font_name)
                            found_in_this_nested = True
                            results.append(
                                (DB.Element.Name.GetValue(et), old_font, font_name)
                            )

                # Recursive call for families nested even deeper
                nested_results, nested_found = update_nested_generic_annotations(
                    nested_family_doc, font_name
                )
                if nested_found:
                    results.extend(nested_results)
                    found_in_this_nested = True

            if found_in_this_nested:
                found_in_any_nested = True
                # Load the updated nested family back into its host family
                nested_family_doc.LoadFamily(host_family_doc, FamilyLoaderOptionsHandler())

        except Exception as e:
            logger.error(
                "Error processing nested family '{}' in '{}': {}".format(
                    nested_family.Name, host_family_doc.Title, e
                )
            )
        finally:
            if nested_family_doc is not None:
                try:
                    nested_family_doc.Close(False)
                except:
                    pass

    return results, found_in_any_nested


def process_family_document(family_doc, new_font_name):
    # type: (DB.Document, str) -> tuple[list[tuple[str, str, str]], bool]
    """
    Updates all applicable fonts in the given family document, including nested ones.
    Args:
        family_doc (DB.Document): The family document to process.
        new_font_name (str): The new font name.
    Returns:
        tuple: A tuple containing:
            - result (list): A list of tuples with details of updated elements.
            - found (bool): A boolean indicating if any updates were made.
    """
    result = []
    found = False
    bip = DB.BuiltInParameter.TEXT_FONT

    with revit.TransactionGroup("Update Font in Family and Nested", family_doc):
        # Update types in the main family document
        with revit.Transaction("Update Font in Family", family_doc):
            element_types = (
                DB.FilteredElementCollector(family_doc)
                .OfClass(DB.ElementType)
                .ToElements()
            )

            for element_type in element_types:
                try:
                    param = element_type.get_Parameter(bip)
                    if param and param.HasValue:
                        old_font = param.AsString()
                        if old_font != new_font_name:
                            rename_element_type_if_needed(element_type, old_font, new_font_name)
                            param.Set(new_font_name)
                            found = True
                            result.append(
                                (
                                    DB.Element.Name.GetValue(element_type),
                                    old_font,
                                    new_font_name,
                                )
                            )
                except Exception as e:
                    logger.error(
                        "Error updating type '{}' in family '{}': {}".format(
                            DB.Element.Name.GetValue(element_type),
                            family_doc.Title,
                            str(e),
                        )
                    )
                    continue

        # Process nested generic annotations
        nested_results, nested_found = update_nested_generic_annotations(
            family_doc, new_font_name)
        if nested_found:
            found = True
            result.extend(nested_results)

    return result, found


def update_text_font_in_family(doc, family, font_name):
    # type: (DB.Document, DB.Family, str) -> tuple[list[tuple[str, str, str]], bool]
    """
    Updates the text font in a Revit family to the specified font name.
    Also processes nested generic annotation families.
    Args:
        doc (DB.Document): The current Revit document.
        family (DB.Family): The Revit family to update.
        font_name (str): The new font name to set for text elements in the family.
    Returns:
        tuple: A tuple containing:
            - result (list): A list of tuples with details of updated elements in the format
              (element type name, old font name, new font name).
            - found (bool): A boolean indicating whether any text font parameters were found and updated.
    Raises:
        SystemError: If a system-level error occurs during the operation.
        ValueError: If an invalid value is encountered during the operation.
    """
    try:
        family_doc = doc.EditFamily(family)
        result, found = process_family_document(family_doc, font_name)

        if found:
            family_doc.LoadFamily(doc, FamilyLoaderOptionsHandler())
        family_doc.Close(False)
        return result, found
    except (SystemError, ValueError) as e:
        logger.error("Could not process family '{}': {}".format(family.Name, e))
        return [], False


def update_text_types(doc, element_types, font_name):
    # type: (DB.Document, list[DB.ElementType], str) -> list[tuple]
    """
    Updates the font of specified text element types in a Revit document.
    Args:
        doc (DB.Document): The Revit document where the text types are located.
        element_types (list[DB.ElementType]): A list of text element types to update.
        font_name (str): The new font name to set for the text types.
    Returns:
        list[tuple]: A list of tuples containing the element type name, the old font name,
                     and the new font name for each successfully updated text type.
    Raises:
        Exception: Logs an error message if updating a specific element type fails.
    """
    results = []
    bip = DB.BuiltInParameter.TEXT_FONT
    with revit.Transaction("Update Font in Types", doc):
        for elem_type in element_types:
            try:
                # Get the font parameter
                param = elem_type.get_Parameter(bip)
                if param and param.HasValue:
                    old_font = param.AsString()
                    if old_font != font_name:
                        rename_element_type_if_needed(elem_type, old_font, font_name)
                        param.Set(font_name)
                        results.append(
                            (DB.Element.Name.GetValue(elem_type), old_font, font_name)
                        )
            except Exception as e:
                logger.error(
                    "**Error updating {}: {}**".format(
                        DB.Element.Name.GetValue(elem_type), str(e)
                    )
                )
    return results


def main():
    doc = HOST_APP.doc
    uidoc = HOST_APP.uidoc

    # Get list of system fonts
    font_families = System.Drawing.FontFamily.Families
    font_names = [font_family.Name for font_family in font_families]
    font_names.sort()

    # --- LOGIC FOR FAMILY DOCUMENT ---
    if doc.IsFamilyDocument:
        components = [
            Label("Replace all fonts in this family."),
            Separator(),
            Label("Select Target Font:"),
            ComboBox("font", options=font_names, default="Arial"),
            Button("OK"),
        ]
        form = FlexForm("Replace Fonts in Family", components)
        form.show()
        if not form.values:
            return

        selected_font = form.values["font"]
        output.print_md(
            "# Updating fonts in current family to: **{}**".format(selected_font)
        )

        # The current document is a family document
        result, found = process_family_document(doc, selected_font)

        if found:
            output.print_md("## Updated Types:")
            for r in result:
                output.print_md(
                    "- Updated **{}**: from *{}* to **{}**".format(r[0], r[1], r[2])
                )
            output.print_md("\n**Total types updated: {}**".format(len(result)))
            alert("Fonts updated successfully.", title="Success")
        else:
            alert(
                "No text or dimension types with fonts found to update.",
                title="Information",
            )
        return  # End script execution for family document

    # --- LOGIC FOR PROJECT DOCUMENT ---
    components = [
        Label("Change all text fonts in the project to a new font."),
        Label("This will update all text fonts in families, dimensions,"),
        Label("and text notes. This will NOT update fonts in"),
        Label("schedules or tags."),
        Separator(),
        Label("Pick Target Font:"),
        ComboBox("font", options=font_names, default="Arial"),
        Separator(),
        Label("Elements to change:"),
        CheckBox("families", "Fonts used in Families", default=True),
        CheckBox("textnotes", "Text Notes Fonts in Project", default=True),
        CheckBox("dimensions", "Dimensions Fonts in Project", default=True),
        Button("OK"),
    ]

    form = FlexForm("Change Font in Elements", components)
    form.show()
    if not form.values:
        alert("No values selected.")
        return

    selected_font = form.values["font"]
    output.print_md("# Update Fonts To: **{}**".format(selected_font))

    if form.values["families"]:
        families = [
            family
            for family in DB.FilteredElementCollector(doc)
            .OfClass(DB.Family)
            .ToElements()
            if family.IsEditable
        ]
        output.print_md("## Families Updated")
        families_updated = 0
        elements_updated = 0
        with ProgressBar(cancellable=True) as pb:
            i = 0
            with revit.TransactionGroup("Update Font in Families", doc):
                output.print_md(
                    "Updating {} families in the project...".format(len(families))
                )
                for family in families:
                    if family.IsInPlace:
                        continue
                    print("Updating family: {}".format(family.Name))
                    result, found = update_text_font_in_family(
                        doc, family, selected_font
                    )
                    if found:
                        families_updated += 1
                        for r in result:
                            elements_updated += 1
                            logger.debug("Updated {}: {} → {}".format(r[0], r[1], r[2]))
                    if pb.cancelled:
                        break
                    pb.update_progress(i, len(families))
                    i += 1
            output.print_md("\n**Total families updated: {}**".format(families_updated))
            output.print_md(
                "\n**Total elements updated in families: {}**".format(elements_updated)
            )

    text_types = []
    dim_types = []
    if form.values["textnotes"]:
        text_types = (
            DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType).ToElements()
        )
        output.print_md("## Text Note Types Updated")
        result = update_text_types(doc, text_types, selected_font)
        for r in result:
            logger.debug("Updated text note type: {}: {} → {}".format(r[0], r[1], r[2]))
        output.print_md("\n**Total text types updated: {}**".format(len(result)))

    if form.values["dimensions"]:
        dim_types = (
            DB.FilteredElementCollector(doc).OfClass(DB.DimensionType).ToElements()
        )
        output.print_md("## Dimension Types Updated")
        result = update_text_types(doc, dim_types, selected_font)
        for r in result:
            logger.debug("Updated dimension type: {}: {} → {}".format(r[0], r[1], r[2]))
        output.print_md("\n**Total dimension types updated: {}**".format(len(result)))

    uidoc.RefreshActiveView()


if __name__ == "__main__":
    main()
