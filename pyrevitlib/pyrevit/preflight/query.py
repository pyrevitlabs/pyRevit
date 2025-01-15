# -*- coding: UTF-8 -*-

""" Preflight query functions. """

from System.Collections.Generic import HashSet
from pyrevit import DB, script, forms
from pyrevit.revit.db.query import get_name
from pyrevit.revit.db import ProjectInfo
from pyrevit.framework import get_type


def clean_name(document):
    """
    Return the name of the given document without the file path or file
    extension.

    Args:
        document (Document): A Revit document.

    Returns:
        str: The name of the given document without the file path or file
        extension.
    """
    document_name = ProjectInfo(document).path
    # If the document hasn't been saved, then print "File Not Saved"
    if len(document_name) == 0:
        printed_name = "File Not Saved"
    # If the document is a BIM 360 document, then print the file name without
    # the file extension
    elif document_name.startswith("BIM 360://"):
        printed_name = document_name.split("/")[-1]
        printed_name = printed_name.split(".")[0]
    # If the document is a local document, then print the file name without
    # the file path or file extension
    else:
        printed_name = document_name.split("\\")[-1]
    return printed_name


def rvt_links(document):
    """
    Returns a list of all rvt_links instances in a document

    Args:
        document (Document): A Revit document.

    Returns:
        list: A list of Revit link instances.
    """
    return (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_RvtLinks)
        .WhereElementIsNotElementType()
    )


def rvtlinks_types(document, rvt_links_instances):
    """
    Returns a list of all the Revit links types in the document.

    Args:
        document (Document): A Revit document.
        rvt_links_instances (list): A list of Revit link instances.

    Returns:
        list: A list of Revit link types.
    """
    return [document.GetElement(rvtlink.GetTypeId()) for rvtlink in rvt_links_instances]


def rvtlinks_elements(document):
    """
    Returns a list of all the Revit links elements in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: Revit link elements, the number of Revit links, Revit link status, and Revit link documents.
    """
    rvtlinks_instances = rvt_links(document)
    rvtlinks_types_items = rvtlinks_types(document, rvtlinks_instances)
    revitlinks_elements = rvtlinks_instances.ToElements()
    rvtlinks_count = len(revitlinks_elements)
    type_status = [
        rvtlinktype.GetLinkedFileStatus() for rvtlinktype in rvtlinks_types_items
    ]
    rvtlink_docs = [
        rvtlinks_instance.GetLinkDocument() for rvtlinks_instance in rvtlinks_instances
    ]
    return revitlinks_elements, rvtlinks_count, type_status, rvtlink_docs


def rvt_links_docs(document):
    """
    Returns a list of all the Revit links documents in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: A list of Revit link documents.
    """
    return [
        i.GetLinkDocument()
        for i in DB.FilteredElementCollector(document).OfClass(DB.RevitLinkInstance)
    ]


def rvt_links_name(revitlinks_elements):
    """
    Returns two lists of all the Revit links names in the document.

    Args:
        revitlinks_elements (list): A list of Revit link elements.

    Returns:
        tuple: Two lists of Revit document names and Revit link instances names.
    """
    rvt_links_docs_name, rvt_links_instances_name = [], []
    for rvtlinks_element in revitlinks_elements:
        revit_link_name_parts = get_name(rvtlinks_element).split(" : ")
        rvt_links_docs_name.append(revit_link_name_parts[0].split(".rvt")[0])
        rvt_links_instances_name.append(revit_link_name_parts[1])
    return rvt_links_docs_name, rvt_links_instances_name


def rvt_links_unpinned_count(revitlinks_elements):
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


def rvt_links_unpinned_str(revitlinks_elements):
    """
    Returns a list of all the Revit links unpinned status in the document.

    Args:
        revitlinks_elements (list): A list of Revit link elements.

    Returns:
        list: A list of Revit link unpinned status.
    """
    return [
        (
            "-"
            if not hasattr(rvt_link, "Pinned")
            else "Unpinned" if not rvt_link.Pinned else "Pinned"
        )
        for rvt_link in revitlinks_elements
    ]


def analytical_model_activated_count(document):
    """
    Returns the number of activated analytical models in the document.

    Args:
    document (Document): A Revit document.

    Returns:
    int: The number of elements with the analytical model activated in the document.
    """
    param = DB.BuiltInParameter.STRUCTURAL_ANALYTICAL_MODEL
    analytical_elements = (
        DB.FilteredElementCollector(document)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    count = 0
    for element in analytical_elements:
        if (
            element.get_Parameter(param)
            and element.get_Parameter(param).AsInteger() == 1
        ):
            count += 1
    return count


def rooms(document):
    """
    Returns a list of all the rooms in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: A list of rooms, the number of rooms, and the number of unplaced rooms, and the number of unbounded rooms.
    """
    rooms_collector = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Rooms)
        .WhereElementIsNotElementType()
    )
    rooms_elements = rooms_collector.ToElements()
    rooms_count = len(rooms_elements)
    if not rooms_elements:
        return 0, 0, 0
    unbounded_rooms = sum(1 for room in rooms_elements if room.Area == 0)
    unplaced_rooms_count = sum(1 for room in rooms_elements if room.Location is None)
    return rooms_count, unplaced_rooms_count, unbounded_rooms


def sheets(document):
    """
    Returns a list of all the sheets in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: A list of sheets and the number of sheets.
    """
    sheets_collector = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Sheets)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return len(sheets_collector), sheets_collector


def views_bucket(document):
    """
    Returns a list of all the views in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: A list of views and the number of views.
    """

    views_collector = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Views)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return len(views_collector), views_collector


def views_not_sheeted(sheets_set=None, views_count=0):
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


def schedules(document):
    """
    Returns a list of all schedule views in the given document.

    Args:
        document (DB.Document): The document to search for schedule views in.

    Returns:
        List[DB.ViewSchedule]: A list of all schedule views in the document.
    """
    schedule_views = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Schedules)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return [v for v in schedule_views if not v.IsTemplate]


def sheeted_view_ids(document, sheets_set):
    """
    Returns a list of all view IDs associated with the given set of sheets.

    Args:
    - sheets_set: A set of sheets

    Returns:
    - A list of view IDs associated with the given set of sheets.
    """
    all_sheeted_view_ids = []
    for sht in sheets_set:
        try:
            vp_ids = [document.GetElement(x).ViewId for x in sht.GetAllViewports()]
            all_sheeted_view_ids.extend(vp_ids)
        except AttributeError:
            pass
    all_sheeted_view_ids = list(set(all_sheeted_view_ids))
    return all_sheeted_view_ids


def schedules_instances_on_sheet(document):
    """
    Returns all the sheeted schedules in the given document.

    Args:
        document (DB.Document): The document to search for sheeted schedules. Defaults to the current document.

    Returns:
        list: A list of all the sheeted schedules in the document.
    """
    return (
        DB.FilteredElementCollector(document)
        .OfClass(DB.ScheduleSheetInstance)
        .ToElements()
    )


def schedules_count(document):
    """
    Counts the total number of schedules in the given document and the number of schedules that are not placed on a sheet.
    Args:
        document (DB.Document): The Revit document to query for schedules.
    Returns:
        tuple: A tuple containing two integers:
            - The total number of schedules in the document.
            - The number of schedules that are not placed on a sheet.
    """
    schedules_elements = schedules(document)
    return len(schedules_elements), sum(
        1
        for v in schedules_elements
        if v.GetPlacementOnSheetStatus() == DB.ViewPlacementOnSheetStatus.NotPlaced
    )


def copied_views(views_set):
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
            if "Copy" in view_name or "Copie" in view_name:
                copied_views_count += 1
        except Exception as e:
            print(e)
    return copied_views_count


def view_templates(document):
    """
    Returns a list of view templates in the given document and the count of view templates.

    Args:
        document (DB.Document, optional): The document to search for view templates. Defaults to doc.

    Returns:
        - int: The count of view templates in the document.
    """
    view_templates_collector = [
        v
        for v in DB.FilteredElementCollector(document)
        .OfClass(DB.View)
        .WhereElementIsNotElementType()
        .ToElements()
        if v.IsTemplate
    ]

    return len(view_templates_collector)


def unused_view_templates(views_list):
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


def filters(document, view_list):
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
        DB.FilteredElementCollector(document)
        .OfClass(DB.ParameterFilterElement)
        .ToElements()
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


def materials(document):
    """
    Returns the number of materials in the given document.

    Args:
        document (DB.Document): The document to count materials in. Defaults to the active document.

    Returns:
        int: The number of materials in the document.
    """
    return (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Materials)
        .GetElementCount()
    )


def line_patterns(document):
    """
    Returns the number of line patterns in the given document.

    Args:
        document (DB.Document): The document to search for line patterns in.
            Defaults to the active document.

    Returns:
        int: The number of line patterns in the document.
    """
    return (
        DB.FilteredElementCollector(document)
        .OfClass(DB.LinePatternElement)
        .GetElementCount()
    )


def dwgs(document):
    """
    Returns the total number of DWG files in the document and the number of linked DWG files.

    Args:
        document (DB.Document, optional): The Revit document to search for DWG files. Defaults to the active document.

    Returns:
        tuple: A tuple containing two integers. The first integer is the total number of DWG files in the document. The second integer is the number of linked DWG files.
    """
    dwg_collector = (
        DB.FilteredElementCollector(document)
        .OfClass(DB.ImportInstance)
        .WhereElementIsNotElementType()
        .ToElements()
    )
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


def families(document):
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
    families_collection = DB.FilteredElementCollector(document).OfClass(DB.Family)
    if not families_collection:
        return 0, 0, 0
    in_place_family_count = 0
    not_parametric_families_count = 0
    count = families_collection.GetElementCount()
    for family in families_collection:
        if family.IsInPlace:
            in_place_family_count += 1
        if not family.IsParametric:
            not_parametric_families_count += 1
    return in_place_family_count, not_parametric_families_count, count


def subcategories_imports(document):
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


def generic_models(document):
    """
    Returns the count of generic model types in the given document.

    Args:
        document (DB.Document): The document to search for generic model types. Defaults to the active document.

    Returns:
        int: The count of generic model types in the document.
    """
    return (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_GenericModel)
        .WhereElementIsElementType()
        .GetElementCount()
    )


def details_components(document):
    """
    Returns the count of detail components in the given document.

    Args:
    - document: The document to search for detail components. Defaults to the active document.

    Returns:
    - int: The count of detail components in the document.
    """
    return (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_DetailComponents)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )


def text_notes_types(document):
    """
    Returns the total number of text note types and the number of text note types with a non-default width factor in the given document.

    Args:
        document (DB.Document, optional): The document to search for text note types. Defaults to the active document.

    Returns:
        Tuple[int, int]: A tuple containing the total number of text note types and the number of text note types with a non-default width factor.
    """
    text_note_type_collector = (
        DB.FilteredElementCollector(document).OfClass(DB.TextNoteType).ToElements()
    )
    if not text_note_type_collector:
        return 0, 0, 0
    total_text_note_types = len(text_note_type_collector)
    wf_count = 0
    text_opaque_background = 0
    for textnote in text_note_type_collector:
        width_factor = textnote.get_Parameter(
            DB.BuiltInParameter.TEXT_WIDTH_SCALE
        ).AsDouble()
        text_bg = textnote.get_Parameter(
            DB.BuiltInParameter.TEXT_BACKGROUND
        ).AsInteger()
        if width_factor != 1:
            wf_count += 1
        if text_bg == 0:
            text_opaque_background += 1
    return total_text_note_types, wf_count, text_opaque_background


def text_notes_instances(document):
    """
    Returns the count of all text notes in the given document and the count of text notes that have all caps formatting.

    Args:
        document (DB.Document): The document to search for text notes. Defaults to the active document.

    Returns:
        Tuple[int, int]: A tuple containing the count of all text notes and the count of text notes with all caps formatting.
    """
    text_notes = DB.FilteredElementCollector(document).OfClass(DB.TextNote).ToElements()
    if not text_notes:
        return 0, 0
    text_notes_count = len(text_notes)
    caps_count = 0
    for text_note in text_notes:
        caps_status = text_note.GetFormattedText().GetAllCapsStatus()
        if str(caps_status) != "None":
            caps_count += 1
    return text_notes_count, caps_count


def collect_groups(document):
    """
    Collects all group elements from the given Revit document.
    Args:
        document (DB.Document): The Revit document from which to collect group elements.
    Returns:
        DB.FilteredElementCollector: A filtered element collector containing all group elements in the document.
    """
    return DB.FilteredElementCollector(document).OfClass(DB.Group)


def collect_group_types(document):
    """
    Collects all group types from the given Revit document.
    Args:
        document (DB.Document): The Revit document from which to collect group types.
    Returns:
        DB.FilteredElementCollector: A filtered element collector containing all group types in the document.
    """
    return DB.FilteredElementCollector(document).OfClass(DB.GroupType)


def detail_groups(document):
    """
    Returns the number of detail groups and detail group types in the given document.

    Args:
        document (DB.Document): The document to search for detail groups. Defaults to the active document.

    Returns:
        Tuple[int, int]: A tuple containing the number of detail groups and detail group types, respectively.
    """
    detail_group_count = 0
    detail_groups_elements = (
        collect_groups(document)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .ToElements()
    )
    for i in detail_groups_elements:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            detail_group_count += 1
    detail_group_type_count = 0
    detail_group_types = (
        collect_group_types(document)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .ToElements()
    )
    for i in detail_group_types:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            detail_group_type_count += 1
    return detail_group_count, detail_group_type_count


def groups(document):
    """
    Returns the number of model group instances and model group types in the given document.

    Args:
        document (DB.Document): The document to search for model groups. Defaults to the current document.

    Returns:
        Tuple[int, int]: A tuple containing the number of model group instances and the number of model group types.
    """
    model_group_count = 0
    model_group_elements = (
        collect_groups(document)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .ToElements()
    )
    for i in model_group_elements:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            model_group_count += 1
    model_group_type_count = 0
    model_group_types = (
        collect_group_types(document)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .ToElements()
    )
    for i in model_group_types:
        if any(["Groupe de réseaux", "Array group"]) not in DB.Element.Name.GetValue(i):
            model_group_type_count += 1
    return model_group_count, model_group_type_count


def reference_planes(document):
    """
    Returns the count of all reference planes and the count of unnamed reference planes in the given document.

    Args:
        document (DB.Document): The document to search for reference planes. Defaults to the active document.

    Returns:
        Tuple[int, int]: A tuple containing the count of all reference planes and the count of unnamed reference planes.
    """
    ref_planes = (
        DB.FilteredElementCollector(document).OfClass(DB.ReferencePlane).ToElements()
    )
    if not ref_planes:
        return 0, 0
    ref_planes_count = len(ref_planes)
    unnamed_ref_planes_count = 0
    for ref_plane in ref_planes:
        # FIXME French compatibility, make it universal
        if ref_plane.Name == "Reference Plane" or ref_plane.Name == "Plan de référence":
            unnamed_ref_planes_count += 1
    return ref_planes_count, unnamed_ref_planes_count


def elements_count(document):
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


def detail_lines(document):
    """
    Returns the number of detail lines in the given document.

    Args:
        document (DB.Document): The document to search for detail lines in.

    Returns:
        int: The number of detail lines in the document.
    """
    all_lines = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Lines)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    if not all_lines:
        return 0
    count = 0
    for line in all_lines:
        if line.CurveElementType.ToString() == "DetailCurve":
            count += 1
    return count


def count_dimension_types(document):
    """
    Returns the count of dimension types in the given document.

    Args:
        document (DB.Document): The document to search for dimension types in.

    Returns:
        int: The count of dimension types in the document.
    """
    dimension_types = (
        DB.FilteredElementCollector(document).OfClass(DB.DimensionType).ToElements()
    )
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
    dimension_instances = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Dimensions)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    if not dimension_instances:
        return 0
    dim_count = 0
    for d in dimension_instances:
        if d.OwnerViewId and d.ViewSpecific and d.View:
            dim_count += 1
    return dim_count


def count_dimension_overrides(document):
    """
    Returns the count of dimension overrides in the given document.

    Args:
        document (DB.Document): The document to search for dimension overrides in.

    Returns:
        int: The count of dimension overrides in the document.
    """
    dimension_instances = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Dimensions)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    if not dimension_instances:
        return 0
    dim_overrides_count = 0
    for d in dimension_instances:
        if d.OwnerViewId and d.ViewSpecific and d.View:
            if d.ValueOverride is not None:
                dim_overrides_count += 1
            if d.Segments:
                for seg in d.Segments:
                    if seg.ValueOverride:
                        dim_overrides_count += 1
    return dim_overrides_count


def revisions_clouds(document):
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


def get_purgeable_count(document):
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
