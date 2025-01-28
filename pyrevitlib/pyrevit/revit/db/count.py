# -*- coding: UTF-8 -*-

""" Counting functions for Revit elements. """

from pyrevit import DB
from pyrevit.compat import get_elementid_value_func
import pyrevit.revit.db.query as q


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


def count_unplaced_rooms(rooms):
    """
    Counts the number of unplaced rooms in a given list of rooms.
    An unplaced room is defined as a room with no location (i.e., room.Location is None).

    Args:
        rooms (list, optional): A list of room objects. Defaults to None.

    Returns:
        int: The number of unplaced rooms in the list.
    """
    return sum(1 for room in rooms if room.Location is None)


def count_unbounded_rooms(rooms):
    """
    Counts the number of unbounded rooms (rooms with an area of 0) in the given list of rooms.

    Args:
        rooms (list, optional): A list of room objects. Each room object should have an 'Area' attribute.

    Returns:
        int: The number of unbounded rooms in the list.
    """
    return sum(1 for room in rooms if room.Area == 0)


def count_unplaced_views(sheets_set=None, views_count=None):
    """
    Returns the number of views not on a sheet.

    Args:
        sheets_set (list): A list of sheets.
        views_count (int): The number of views in the document.

    Returns:
        int: The number of views not on a sheet.
    """
    views_on_sheet = []
    if sheets_set is None or views_count is None:
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
    return (
        DB.FilteredElementCollector(document)
        .WherePasses(elem_param_filter)
        .GetElementCount()
    )


def count_unplaced_schedules(schedules=None):
    """
    Counts the number of schedules that are not placed on a sheet in the given document.

    Args:
        document (DB.Document): The Revit document to query for schedules.

    Returns:
        int: The number of schedules that are not placed on a sheet.
    """
    return sum(
        1
        for v in schedules
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
    copied_view_names = ["Copy", "Copie"]
    copied_views_count = 0
    for view in views_set:
        view_name = q.get_name(view)
        try:
            # FIXME French compatibility, make it universal
            if any(name in view_name for name in copied_view_names):
                copied_views_count += 1
        except Exception as e:
            print(e)
    return copied_views_count


def count_unused_view_templates(views_list, document):
    """
    Returns the count of unused view templates in the given list of views.

    Args:
        views (list): A list of views to check for unused view templates.

    Returns:
        int: The count of unused view templates.
    """
    if views_list is None:
        return 0
    applied_templates = [v.ViewTemplateId for v in views_list]
    view_templates_list = q.get_all_view_templates(doc=document)
    unused_view_templates = []
    for v in view_templates_list:
        if v.Id not in applied_templates:
            unused_view_templates.append(v)
    return len(unused_view_templates)


def count_unused_filters_in_views(view_list, filters):
    """
    Counts the number of unused filters in the given list of views.

    Args:
        view_list (list): A list of Revit view objects to check for filter usage.
        filters (list): A list of filter objects to check against the views.

        Returns:
        int: The number of filters that are not used in any of the provided views.
    """
    used_filters_set = set()
    all_filters = set()
    get_elementid_value = get_elementid_value_func()
    for flt in filters:
        all_filters.add(get_elementid_value(flt.Id))
    for v in view_list:
        if v.AreGraphicsOverridesAllowed():
            view_filters = v.GetFilters()
            for filter_id in view_filters:
                used_filters_set.add(get_elementid_value(filter_id))
    unused_view_filters_count = len(all_filters - used_filters_set)
    return unused_view_filters_count


def count_linked_dwg_files(document):
    """
    Returns the number of linked DWG files in the document.

    Args:
        document (DB.Document): The Revit document to search for linked DWG files.

    Returns:
        int: The number of linked DWG files in the document.
    """
    dwg_collector = q.get_elements_by_class(DB.ImportInstance, doc=document)
    if not dwg_collector:
        return 0
    dwg_imported = 0
    for dwg in dwg_collector:
        if not dwg.IsLinked:
            dwg_imported += 1
    return len(dwg_collector) - dwg_imported


def count_in_place_families(document):
    """
    This function collects all the in-place families in the given document and returns their count.

    Args:
    - document: The Revit document to search for in-place families in.

    Returns:
    - int: The count of in-place families.
    """
    familyinstance_collector = q.get_elements_by_class(DB.FamilyInstance, doc=document)
    in_place_family_count = sum(
        1
        for x in familyinstance_collector
        if x.Symbol and x.Symbol.Family and x.Symbol.Family.IsInPlace
    )
    return in_place_family_count


def count_total_families(document):
    """
    Counts the total number of unique family names in the given Revit document.

    Args:
        document: The Revit document to count families from.

    Returns:
        int: The total number of unique family names in the document.
    """
    families_collection = q.get_families(document, only_editable=True)
    unique_families = []
    for fam in families_collection:
        if fam.Name not in unique_families:
            unique_families.append(fam.Name)
    if not unique_families:
        return 0
    return len(unique_families)


def count_textnote_types_with_changed_width_factor(text_notes_types):
    """
    Counts the number of text note types that have a width factor different from the default value of 1.

    Args:
        text_notes_types (list): A list of text note types to check.

    Returns:
        int: The number of text note types with a changed width factor.
    """
    if text_notes_types is None:
        return 0
    changed_width_factor = 0
    for textnote in text_notes_types:
        width_factor = textnote.get_Parameter(
            DB.BuiltInParameter.TEXT_WIDTH_SCALE
        ).AsDouble()
        if width_factor != 1:
            changed_width_factor += 1
    return changed_width_factor


def count_textnote_types_with_opaque_background(text_notes_types):
    """
    Counts the number of text notes with an opaque background.

    Args:
        text_notes_types (list): A list of text note elements.

    Returns:
        int: The number of text notes with an opaque background.
    """
    if text_notes_types is None:
        return 0
    text_opaque_background = 0
    for textnote in text_notes_types:
        text_background = textnote.get_Parameter(
            DB.BuiltInParameter.TEXT_BACKGROUND
        ).AsInteger()
        if text_background == 0:
            text_opaque_background += 1
    return text_opaque_background


def count_text_notes_with_all_caps(text_notes):
    """
    Counts the number of text notes that have all capital letters.

    Args:
        text_notes (list): A list of text note objects.

    Returns:
        int: The number of text notes with all capital letters.
    """
    if text_notes is None:
        return 0
    caps_count = 0
    for text_note in text_notes:
        caps_status = text_note.GetFormattedText().GetAllCapsStatus()
        if caps_status:
            caps_count += 1
    return caps_count


def count_unnamed_reference_planes(reference_planes):
    """
    Returns the count of unnamed reference planes in the given document.

    Args:
        document (DB.Document): The document to search for reference planes. Defaults to the active document.

    Returns:
        int: The count of unnamed reference planes.
    """
    if reference_planes is None:
        return 0
    unnamed_ref_planes_count = 0
    # Default reference plane label, not the most elegant solution
    reference_plane_default_label = DB.LabelUtils.GetLabelFor(
        DB.BuiltInCategory.OST_CLines
    ).replace("s", "")
    for ref_plane in reference_planes:
        if ref_plane.Name == reference_plane_default_label:
            unnamed_ref_planes_count += 1
    return unnamed_ref_planes_count


def count_dimension_overrides(dimensions):
    """
    Counts the number of dimension overrides in a list of dimensions.
    This function iterates through a list of dimensions and counts how many of them
    have a value override. It also checks for overrides in dimension segments if they exist.

    Args:
        dimensions (list): A list of dimension objects to check for overrides.

    Returns:
        int: The total count of dimension overrides found in the list of dimensions.
    """
    if dimensions is None:
        return 0
    dim_overrides_count = 0
    for d in dimensions:
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


def count_detail_group_instances(doc):
    """
    Counts the number of detail group instances in the given Revit document.
    This function collects all detail group instances in the document and then
    adjusts the count by excluding any groups that are part of an array.

    Args:
        doc: The Revit document to search for detail group instances.

    Returns:
        int: The count of detail group instances not part of an array.
    """
    detail_group_ids = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )
    arrays_groups_ids = [array.IntegerValue for array in q.get_array_group_ids(doc)]
    return len([group_id for group_id in detail_group_ids if group_id.IntegerValue not in arrays_groups_ids])


def count_detail_groups_types(document):
    """
    Counts the number of detail group types in the given Revit document, excluding those that are part of array groups.

    Args:
        document (DB.Document): The Revit document to search for detail group types.

    Returns:
        int: The count of detail group types, excluding array group types.
    """
    detail_group_type_ids = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .WhereElementIsElementType()
        .ToElementIds()
    )
    array_group_type_ids = [array.IntegerValue for array in q.get_array_group_ids_types(document)]
    return len([group_id for group_id in detail_group_type_ids if group_id.IntegerValue not in array_group_type_ids])


def count_model_groups_types(doc):
    """
    Counts the number of model group types in the given Revit document, excluding array group types.

    Args:
        doc: The Revit document to process.

    Returns:
        int: The count of model group types excluding array group types.
    """
    model_group_types_ids = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .WhereElementIsElementType()
        .ToElementIds()
    )
    array_group_type_ids = [array.IntegerValue for array in q.get_array_group_ids_types(doc)]
    return len([model_group_id for model_group_id in model_group_types_ids if model_group_id.IntegerValue not in array_group_type_ids])


def count_model_group_instances(doc):
    """
    Counts the number of model group instances in the given Revit document that are not part of any array.

    Args:
        doc: The Revit document to search for model group instances.

    Returns:
        int: The count of model group instances not part of any array.
    """
    model_groups_instances_ids = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )
    arrays_groups_ids = [array.IntegerValue for array in q.get_array_group_ids(doc)]
    return len([model_group_id for model_group_id in model_groups_instances_ids if model_group_id.IntegerValue not in arrays_groups_ids])
