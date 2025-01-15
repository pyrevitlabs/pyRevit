# -*- coding: UTF-8 -*-

""" Counting functions for Revit elements. """

from System.Collections.Generic import HashSet
from pyrevit import DB
from pyrevit.revit.db.query import get_name
from pyrevit.revit.db import ProjectInfo
from pyrevit.revit.db.query import (
    get_elements_by_categories,
    get_elements_by_class,
    get_types_by_class,
    get_all_schedules,
)


def count_unpinned_revit_links(revitlinks_elements):
    """
    Returns the number of unpinned Revit links in the document.

    Args:
        rvtlinks_elements (list): A list of Revit link elements.

    Returns:
        int: The number of unpinned Revit links in the document.
    """
    return sum(
        1
        for rvt_link in revitlinks_elements
        if hasattr(rvt_link, "Pinned") and not rvt_link.Pinned
    )


def count_rooms(document):
    """
    Returns a list of all the rooms in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: A list of rooms, the number of rooms, and the number of unplaced rooms, and the number of unbounded rooms.
    """
    rooms = get_elements_by_categories(
        [DB.BuiltInCategory.OST_Rooms], doc=document
    )
    rooms_count = len(rooms)
    if not rooms:
        return 0, 0, 0
    unbounded_rooms = sum(1 for room in rooms if room.Area == 0)
    unplaced_rooms_count = sum(1 for room in rooms if room.Location is None)
    return rooms_count, unplaced_rooms_count, unbounded_rooms


def count_unplaced_views(sheets_set=None, views_count=0):
    """
    Returns the number of views not on a sheet.

    Args:
        sheets_set (list): A list of sheets.
        views_count (int): The number of views in the document.

    Returns:
        int: The number of views not on a sheet.
    """
    # FIXME: Numbers need to be checked
    views_on_sheet = []
    if not sheets_set:
        return views_count
    for sheet in sheets_set:
        try:
            for view in sheet.GetAllPlacedViews():
                if view not in views_on_sheet:
                    views_on_sheet.append(view)
        except AttributeError:
            pass
    views_not_on_sheets = views_count - len(views_on_sheet)
    return views_not_on_sheets


def count_analytical_model_activated(document):
    """
    Returns the number of activated analytical models in the document.

    Args:
    document (Document): A Revit document.

    Returns:
    int: The number of elements with the analytical model activated in the document.
    """
    param = DB.BuiltInParameter.STRUCTURAL_ANALYTICAL_MODEL
    provider = DB.ParameterValueProvider(DB.ElementId(param))
    evaluator = DB.FilterNumericEquals()
    rule = DB.FilterIntegerRule(provider, evaluator, 1)
    elem_param_filter = DB.ElementParameterFilter(rule)
    return DB.FilteredElementCollector(document).WherePasses(elem_param_filter).GetElementCount()


def count_schedules(document):
    """
    Counts the total number of schedules in the given document and the number of schedules that are not placed on a sheet.
    
    Args:
        document (DB.Document): The Revit document to query for schedules.
    
    Returns:
        tuple: A tuple containing two integers:
            - The total number of schedules in the document.
            - The number of schedules that are not placed on a sheet.
    """
    schedules_elements = get_all_schedules(document)
    return len(schedules_elements), sum(
        1
        for v in schedules_elements
        if v.GetPlacementOnSheetStatus() == DB.ViewPlacementOnSheetStatus.NotPlaced
    )


def count_copied_views(views_set):
    """
    Returns the number of views in the given set that have "Copy" or "Copie" in their name.

    Args:
    views_set (set): A set of views to check for copied views. Defaults to None.

    Returns:
    int: The number of views in the set that have "Copy" or "Copie" in their name.
    """
    copied_views_count = 0
    for view in views_set:
        view_name = get_name(view)
        try:
            # FIXME French compatibility, make it universal
            if "Copy" in view_name or "Copie" in view_name:
                copied_views_count += 1
        except Exception as e:
            print(e)
    return copied_views_count


def count_unused_view_templates(views_list):
    """
    Returns the count of unused view templates in the given list of views.

    Args:
        views (list): A list of views to check for unused view templates.

    Returns:
        int: The count of unused view templates.
    """
    if not views_list:
        return 0
    applied_templates = [v.ViewTemplateId for v in views_list]
    view_templates_list = [v for v in views_list if v.IsTemplate]
    unused_view_templates = []
    for v in view_templates_list:
        if v.Id not in applied_templates:
            unused_view_templates.append(v.Name)
    unused_view_templates_count = len(unused_view_templates)
    return unused_view_templates_count


def count_filters(document, view_list):
    """
    This function takes in a Revit document and a list of views, and returns the count of all parameter filters in the document
    and the count of unused parameter filters in the views.

    Args:
    - document (DB.Document): The Revit document to search for parameter filters. Defaults to the active document.
    - views (list of DB.View): The list of views to check for unused parameter filters.

    Returns:
    - tuple: A tuple containing two integers:
        - all_filters_count: The count of all parameter filters in the document.
        - unused_view_filters_count: The count of unused parameter filters in the views.
    """
    filters_collection = (
        get_elements_by_class(DB.ParameterFilterElement, doc=document)
    )
    if not filters_collection:
        return 0, 0
    used_filters_set = set()
    all_filters = set()
    for flt in filters_collection:
        all_filters.add(flt.Id.IntegerValue)
    total_filters_count = len(all_filters)
    for v in view_list:
        if v.AreGraphicsOverridesAllowed():
            view_filters = v.GetFilters()
            for filter_id in view_filters:
                used_filters_set.add(filter_id.IntegerValue)
    unused_view_filters_count = 0
    unused_view_filters_count = len(all_filters - used_filters_set)
    return total_filters_count, unused_view_filters_count


def count_dwg_files(document):
    """
    Returns the total number of DWG files in the document and the number of linked DWG files.

    Args:
        document (DB.Document, optional): The Revit document to search for DWG files. Defaults to the active document.

    Returns:
        tuple: A tuple containing two integers. The first integer is the total number of DWG files in the document. The second integer is the number of linked DWG files.
    """
    dwg_collector = get_elements_by_class(DB.ImportInstance, doc=document)
    if not dwg_collector:
        return 0, 0
    dwg_files_count = len(dwg_collector)
    dwg_imported = 0
    dwg_not_in_current_view = 0
    for dwg in dwg_collector:
        if not dwg.IsLinked:
            dwg_imported += 1
        if not dwg.ViewSpecific:
            dwg_not_in_current_view += 1
    count_of_linked_dwg_files = dwg_files_count - dwg_imported
    return dwg_files_count, count_of_linked_dwg_files


def count_families_by_type(document):
    """
    This function collects all the families in the given document and returns the count of three types of families:
    - In-place families
    - Non-parametric families
    - Total families

    Args:
    - document: The Revit document to search for families in. Defaults to the active document.

    Returns:
    - Tuple[int, int, int]: A tuple of three integers representing the count of each type of family.
    """
    families_collection = get_elements_by_class(DB.Family, doc=document)
    if not families_collection:
        return 0, 0, 0
    in_place_family_count = 0
    not_parametric_families_count = 0
    family_count = len(families_collection)
    for family in families_collection:
        if family.IsInPlace:
            in_place_family_count += 1
        if not family.IsParametric:
            not_parametric_families_count += 1
    return in_place_family_count, not_parametric_families_count, family_count


def count_import_subcategories(document):
    """
    Returns the number of subcategories in the Import category of the given document.

    Args:
        document (DB.Document): The document to check. Defaults to the active document.

    Returns:
        int: The number of subcategories in the Import category.
    """
    return len(
        [
            c.Id
            for c in document.Settings.Categories.get_Item(
                DB.BuiltInCategory.OST_ImportObjectStyles
            ).SubCategories
        ]
    )


def count_detail_components(document):
    """
    Returns the count of detail components in the given document.

    Args:
    - document: The document to search for detail components. Defaults to the active document.

    Returns:
    - int: The count of detail components in the document.
    """
    return len(
        get_elements_by_categories(
            [DB.BuiltInCategory.OST_DetailComponents], doc=document
        )
    )


def count_textnote_types(document):
    """
    Counts the total number of TextNoteType elements in the given Revit document,
    as well as the number of TextNoteType elements with a changed width factor
    and the number of TextNoteType elements with an opaque background.
    
    Args:
        document (DB.Document): The Revit document to search for TextNoteType elements.
    
    Returns:
        tuple: A tuple containing three integers:
            - total_text_note_types (int): The total number of TextNoteType elements.
            - changed_width_factor (int): The number of TextNoteType elements with a width factor not equal to 1.
            - text_opaque_background (int): The number of TextNoteType elements with an opaque background.
    """
    text_note_type_collector = get_types_by_class(DB.TextNoteType, doc=document)
    if not text_note_type_collector:
        return 0, 0, 0
    total_text_note_types = len(text_note_type_collector)
    changed_width_factor = 0
    text_opaque_background = 0
    for textnote in text_note_type_collector:
        width_factor = textnote.get_Parameter(
            DB.BuiltInParameter.TEXT_WIDTH_SCALE
        ).AsDouble()
        text_background = textnote.get_Parameter(
            DB.BuiltInParameter.TEXT_BACKGROUND
        ).AsInteger()
        if width_factor != 1:
            changed_width_factor += 1
        if text_background == 0:
            text_opaque_background += 1
    return total_text_note_types, changed_width_factor, text_opaque_background


def count_text_notes(document):
    """
    Returns the count of all text notes in the given document and the count of text notes that have all caps formatting.

    Args:
        document (DB.Document): The document to search for text notes. Defaults to the active document.

    Returns:
        Tuple[int, int]: A tuple containing the count of all text notes and the count of text notes with all caps formatting.
    """
    text_notes = get_elements_by_class(DB.TextNote, doc=document)
    if not text_notes:
        return 0, 0
    text_notes_count = len(text_notes)
    caps_count = 0
    for text_note in text_notes:
        caps_status = text_note.GetFormattedText().GetAllCapsStatus()
        if str(caps_status) != "None":
            caps_count += 1
    return text_notes_count, caps_count


def count_detail_groups(document):
    """
    Returns the number of detail groups and detail group types in the given document.

    Args:
        document (DB.Document): The document to search for detail groups. Defaults to the active document.

    Returns:
        Tuple[int, int]: A tuple containing the number of detail groups and detail group types, respectively.
    """
    detail_group_count = 0
    detail_groups_elements = (
        DB.FilteredElementCollector(document)
        .OfClass(DB.Group)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .ToElements()
    )
    for i in detail_groups_elements:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            detail_group_count += 1
    detail_group_type_count = 0
    detail_group_types = (
        DB.FilteredElementCollector(document)
        .OfClass(DB.GroupType)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .ToElements()
    )
    for i in detail_group_types:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            detail_group_type_count += 1
    return detail_group_count, detail_group_type_count


def count_model_groups(document):
    """
    Returns the number of model group instances and model group types in the given document.

    Args:
        document (DB.Document): The document to search for model groups. Defaults to the current document.

    Returns:
        Tuple[int, int]: A tuple containing the number of model group instances and the number of model group types.
    """
    model_group_count = 0
    model_group_elements = (
        DB.FilteredElementCollector(document)
        .OfClass(DB.Group)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .ToElements()
    )
    for i in model_group_elements:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            model_group_count += 1
    model_group_type_count = 0
    model_group_types = (
        DB.FilteredElementCollector(document)
        .OfClass(DB.GroupType)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .ToElements()
    )
    for i in model_group_types:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            model_group_type_count += 1
    return model_group_count, model_group_type_count


def count_reference_planes(document):
    """
    Returns the count of all reference planes and the count of unnamed reference planes in the given document.

    Args:
        document (DB.Document): The document to search for reference planes. Defaults to the active document.

    Returns:
        Tuple[int, int]: A tuple containing the count of all reference planes and the count of unnamed reference planes.
    """
    ref_planes = get_elements_by_class(DB.ReferencePlane, doc=document)
    if not ref_planes:
        return 0, 0
    ref_planes_count = len(ref_planes)
    unnamed_ref_planes_count = 0
    for ref_plane in ref_planes:
        # FIXME French compatibility, make it universal
        if ref_plane.Name == "Reference Plane" or ref_plane.Name == "Plan de référence":
            unnamed_ref_planes_count += 1
    return ref_planes_count, unnamed_ref_planes_count


def count_elements(document):
    """
    Returns the number of non-element type elements in the given document.

    Args:
    - document (DB.Document): The document to count elements in. Defaults to the current document.

    Returns:
    - int: The number of non-element type elements in the document.
    """
    return (
        DB.FilteredElementCollector(document)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )


def count_detail_lines(document):
    """
    Returns the number of detail lines in the given document.

    Args:
        document (DB.Document): The document to search for detail lines in.

    Returns:
        int: The number of detail lines in the document.
    """
    lines = get_elements_by_categories(
        [DB.BuiltInCategory.OST_Lines], doc=document
    )
    if not lines:
        return 0
    detail_line_count = 0
    for line in lines:
        if line.CurveElementType.ToString() == "DetailCurve":
            detail_line_count += 1
    return detail_line_count


def count_dimension_types(document):
    """
    Returns the count of dimension types in the given document.

    Args:
        document (DB.Document): The document to search for dimension types in.

    Returns:
        int: The count of dimension types in the document.
    """
    dimension_types = get_types_by_class(DB.DimensionType, doc=document)
    if not dimension_types:
        return 0
    dimension_types_count = 0
    for dt in dimension_types:
        try:
            if dt.LookupParameter("Nom du type"):
                dimension_types_count += 1
            elif dt.LookupParameter("Type name"):
                dimension_types_count += 1
        except AttributeError:
            pass
    return dimension_types_count


def count_dimensions(document):
    """
    Returns the count of dimensions in the given document.

    Args:
        document (DB.Document): The document to search for dimensions in.

    Returns:
        int: The count of dimensions in the document.
    """
    dimensions = get_elements_by_categories(
        [DB.BuiltInCategory.OST_Dimensions], doc=document
    )
    if not dimensions:
        return 0
    dimension_count = 0
    for d in dimensions:
        if d.OwnerViewId and d.ViewSpecific and d.View:
            dimension_count += 1
    return dimension_count


def count_dimension_overrides(document):
    """
    Returns the count of dimension overrides in the given document.

    Args:
        document (DB.Document): The document to search for dimension overrides in.

    Returns:
        int: The count of dimension overrides in the document.
    """
    dimensions = get_elements_by_categories(
        [DB.BuiltInCategory.OST_Dimensions], doc=document
    )
    if not dimensions:
        return 0
    dim_overrides_count = 0
    for d in dimensions:
        if d.OwnerViewId and d.ViewSpecific and d.View:
            if d.ValueOverride is not None:
                dim_overrides_count += 1
            if d.Segments:
                for seg in d.Segments:
                    if seg.ValueOverride:
                        dim_overrides_count += 1
    return dim_overrides_count


def count_revision_clouds(document):
    """
    Returns the number of revision clouds in the given document.

    Args:
        document (DB.Document): The document to search for revision clouds in. Defaults to the active document.

    Returns:
        int: The number of revision clouds in the document.
    """
    return (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )


def count_purgeable_elements(document):
    """
    Returns the count of purgeable elements in the given document.

    Args:
    document (DB.Document): The document to check for purgeable elements. Defaults to the current document.

    Returns:
    int: The count of purgeable elements in the document.
    """
    if not hasattr(document, "GetUnusedElements"):
        return 0
    return len(document.GetUnusedElements(HashSet[DB.ElementId]()))
