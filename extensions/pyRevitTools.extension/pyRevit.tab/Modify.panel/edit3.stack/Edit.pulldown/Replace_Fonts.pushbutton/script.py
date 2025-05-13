# encoding: utf-8
import System

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

output = script.get_output()
logger = script.get_logger()


def update_text_font_in_family(doc, family, font_name):
    """
    Updates the text font in a Revit family to the specified font name.
    Args:
        doc (DB.Document): The current Revit document.
        family (DB.Family): The Revit family to update.
        font_name (str): The new font name to set for text elements in the family.
    Returns:
        tuple: A tuple containing:
            - result (list): A list of tuples with details of updated elements in the format
              (element family name, old font name, new font name).
            - found (bool): A boolean indicating whether any text font parameters were found and updated.
    Raises:
        SystemError: If a system-level error occurs during the operation.
        ValueError: If an invalid value is encountered during the operation.
    """
    try:
        result = []
        bip = DB.BuiltInParameter.TEXT_FONT
        family_doc = doc.EditFamily(family)
        element_types = (
            DB.FilteredElementCollector(family_doc).OfClass(DB.ElementType).ToElements()
        )
        with revit.Transaction("Update Font", family_doc):
            found = False
            for element_type in element_types:
                try:
                    param = element_type.get_Parameter(bip)
                    if param and param.HasValue:
                        old_font = param.AsString()
                        param.Set(font_name)
                        found = True
                        result.append((element_type.FamilyName, old_font, font_name))
                except Exception as e:
                    logger.error(
                        "Error updating {}: {}".format(element_type.FamilyName, str(e))
                    )
                    continue
        if found:
            family_doc.LoadFamily(doc, FamilyLoaderOptionsHandler())
        family_doc.Close(False)
        return result, found
    except (SystemError, ValueError):
        return [], False


def update_text_types(doc, element_types, font_name):
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

    font_families = System.Drawing.FontFamily.Families
    font_names = [font_family.Name for font_family in font_families]
    font_names.sort()

    components = [
        Label(
            "Change all text fonts in the project to a new font. This will update all text fonts in families, dimensions and text notes. This will not update fonts in schedules or tags."
        ),
        Separator(),
        Label("Pick Target Font:"),
        ComboBox("font", options=font_names, default="Arial"),
        Separator(),
        Label("Elements to change:"),
        CheckBox("families", "Fonts used in Families", default=True),
        CheckBox("textnotes", "Text Notes Fonts in Project", default=True),
        CheckBox("dimensions", "Dimensions Fonts in Project", default=True),
        Button("Select"),
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
