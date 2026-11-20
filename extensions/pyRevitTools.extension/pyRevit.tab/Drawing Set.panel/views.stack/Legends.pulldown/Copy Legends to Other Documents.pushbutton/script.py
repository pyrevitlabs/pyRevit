# pylint: disable=E0401,W0613,C0103,C0111
# -*- coding: utf-8 -*-
from collections import defaultdict
import System
from Autodesk.Revit.DB import Transaction, TransactionGroup
from pyrevit import revit, DB, script, forms
from pyrevit.framework import List

SOURCE_DOC = revit.doc
INVALID_ID = DB.ElementId.InvalidElementId


def id_value(element_id):
    if element_id is None:
        return -1
    try:
        return element_id.Value
    except AttributeError:
        return element_id.IntegerValue


def point_key(point, precision=7):
    if point is None:
        return None
    return (round(point.X, precision), round(point.Y, precision), round(point.Z, precision))


def bbox_key(element, view):
    try:
        box = element.get_BoundingBox(view)
        if box:
            center = (box.Min + box.Max) * 0.5
            size = box.Max - box.Min
            return point_key(center) + point_key(size)
    except Exception:
        pass
    return None


def curve_key(element):
    try:
        curve = element.GeometryCurve
        p0 = point_key(curve.GetEndPoint(0))
        p1 = point_key(curve.GetEndPoint(1))
        # Normalize the endpoint order so reversed curves still match.
        ends = tuple(sorted((p0, p1)))
        return (curve.GetType().Name, ends)
    except Exception:
        return None


def element_signature(element, view):
    category_id = id_value(element.Category.Id) if element.Category else -1
    class_name = element.GetType().FullName
    text_value = None
    try:
        text_value = element.Text
    except Exception:
        pass
    location_key = None
    try:
        location = element.Location
        if isinstance(location, DB.LocationPoint):
            location_key = point_key(location.Point)
        elif isinstance(location, DB.LocationCurve):
            curve = location.Curve
            location_key = (
                curve.GetType().Name,
                tuple(sorted((point_key(curve.GetEndPoint(0)), point_key(curve.GetEndPoint(1))))),
            )
    except Exception:
        pass
    type_name = None
    family_name = None
    try:
        element_type = element.Document.GetElement(element.GetTypeId())
        if element_type:
            type_name = element_type.Name
            try:
                family_name = element_type.FamilyName
            except Exception:
                pass
    except Exception:
        pass
    return (
        class_name,
        category_id,
        text_value,
        family_name,
        type_name,
        curve_key(element),
        location_key,
        bbox_key(element, view),
    )


def match_copied_elements(source_doc, source_view, source_ids, destination_doc, destination_view, destination_ids):
    """Match copied elements by geometry/content, with positional fallback only when unambiguous."""
    source_groups = defaultdict(list)
    destination_groups = defaultdict(list)
    for source_id in source_ids:
        element = source_doc.GetElement(source_id)
        source_groups[element_signature(element, source_view)].append(source_id)
    for destination_id in destination_ids:
        element = destination_doc.GetElement(destination_id)
        destination_groups[element_signature(element, destination_view)].append(destination_id)

    pairs = []
    used_destination_values = set()
    unmatched_source_ids = []
    for signature, grouped_source_ids in source_groups.items():
        grouped_destination_ids = destination_groups.get(signature, [])
        if len(grouped_source_ids) == len(grouped_destination_ids) and grouped_destination_ids:
            grouped_source_ids = sorted(grouped_source_ids, key=id_value)
            grouped_destination_ids = sorted(grouped_destination_ids, key=id_value)
            for source_id, destination_id in zip(grouped_source_ids, grouped_destination_ids):
                pairs.append((source_id, destination_id))
                used_destination_values.add(id_value(destination_id))
        else:
            unmatched_source_ids.extend(grouped_source_ids)

    unmatched_destination_ids = [
        destination_id for destination_id in destination_ids
        if id_value(destination_id) not in used_destination_values
    ]
    if unmatched_source_ids:
        # CopyElements normally preserves input/result order. Use that relationship only
        # for the unresolved remainder and only when the remaining counts match.
        source_position = dict((id_value(source_id), index) for index, source_id in enumerate(source_ids))
        destination_position = dict((index, destination_id) for index, destination_id in enumerate(destination_ids))
        fallback_pairs = []
        for source_id in unmatched_source_ids:
            index = source_position[id_value(source_id)]
            destination_id = destination_position.get(index)
            if destination_id is None or destination_id not in unmatched_destination_ids:
                raise Exception("Unable to safely match copied element {}.".format(id_value(source_id)))
            fallback_pairs.append((source_id, destination_id))
        if len(fallback_pairs) != len(unmatched_destination_ids):
            raise Exception("Source/destination element matching was ambiguous.")
        pairs.extend(fallback_pairs)

    if len(pairs) != len(source_ids) or len(pairs) != len(destination_ids):
        raise Exception(
            "Matched {} source/destination elements, but copied {} of {} source elements.".format(
                len(pairs), len(destination_ids), len(source_ids)
            )
        )
    return pairs


def rounded_number(value):
    return round(float(value), 10)


def line_pattern_signature(pattern_element):
    if not pattern_element:
        return None
    pattern = pattern_element.GetLinePattern()
    segments = []
    for segment in pattern.GetSegments():
        segments.append((str(segment.Type), rounded_number(segment.Length)))
    # Deliberately exclude the element name. Geometry is the safe identity.
    return tuple(segments)


def fill_grid_signature(grid):
    try:
        origin = (rounded_number(grid.Origin.U), rounded_number(grid.Origin.V))
    except Exception:
        origin = None
    try:
        segments = tuple(rounded_number(value) for value in grid.GetSegments())
    except Exception:
        segments = tuple()
    return (
        rounded_number(grid.Angle),
        rounded_number(grid.Offset),
        rounded_number(grid.Shift),
        origin,
        segments,
    )


def fill_pattern_signature(pattern_element):
    if not pattern_element:
        return None
    pattern = pattern_element.GetFillPattern()
    grids = []
    try:
        grids = sorted(fill_grid_signature(grid) for grid in pattern.GetFillGrids())
    except Exception:
        grids = []
    try:
        orientation = str(pattern.HostOrientation)
    except Exception:
        orientation = None
    # Deliberately exclude the name. Target, orientation, solid state, and the
    # complete grid definition determine whether a destination pattern is safe.
    return (
        str(pattern.Target),
        orientation,
        bool(pattern.IsSolidFill),
        tuple(grids),
    )


def lowest_id(ids):
    return sorted(ids, key=id_value)[0] if ids else None


def unique_pattern_name(base_name, names, suffix):
    if base_name not in names:
        return base_name
    candidate = "{} [{}]".format(base_name, suffix)
    index = 2
    while candidate in names:
        candidate = "{} [{} {}]".format(base_name, suffix, index)
        index += 1
    return candidate


def build_pattern_maps(destination_doc):
    line_by_signature = defaultdict(list)
    line_by_name = defaultdict(list)
    fill_by_signature = defaultdict(list)
    fill_by_name = defaultdict(list)
    fill_solid_by_target = defaultdict(list)
    line_names = set()
    fill_names = set()

    for element in DB.FilteredElementCollector(destination_doc).OfClass(DB.LinePatternElement):
        line_by_signature[line_pattern_signature(element)].append(element.Id)
        line_by_name[element.Name].append(element.Id)
        line_names.add(element.Name)

    for element in DB.FilteredElementCollector(destination_doc).OfClass(DB.FillPatternElement):
        signature = fill_pattern_signature(element)
        fill_by_signature[signature].append(element.Id)
        fill_by_name[element.Name].append(element.Id)
        fill_names.add(element.Name)
        try:
            pattern = element.GetFillPattern()
            if pattern.IsSolidFill:
                fill_solid_by_target[str(pattern.Target)].append(element.Id)
        except Exception:
            pass

    return {
        "destination_doc": destination_doc,
        "line_by_signature": line_by_signature,
        "line_by_name": line_by_name,
        "fill_by_signature": fill_by_signature,
        "fill_by_name": fill_by_name,
        "fill_solid_by_target": fill_solid_by_target,
        "line_names": line_names,
        "fill_names": fill_names,
        "line_cache": {},
        "fill_cache": {},
        "created_line_patterns": [],
        "created_fill_patterns": [],
    }


def clone_line_pattern(source_pattern_element, pattern_maps):
    source_pattern = source_pattern_element.GetLinePattern()
    new_name = unique_pattern_name(
        source_pattern_element.Name,
        pattern_maps["line_names"],
        "pyRevit Imported",
    )
    cloned_pattern = DB.LinePattern(new_name)
    cloned_pattern.SetSegments(source_pattern.GetSegments())
    created = DB.LinePatternElement.Create(
        pattern_maps["destination_doc"], cloned_pattern
    )
    signature = line_pattern_signature(created)
    pattern_maps["line_names"].add(created.Name)
    pattern_maps["line_by_name"][created.Name].append(created.Id)
    pattern_maps["line_by_signature"][signature].append(created.Id)
    pattern_maps["created_line_patterns"].append(created.Name)
    return created.Id


def clone_fill_grid(source_grid):
    cloned_grid = DB.FillGrid()
    cloned_grid.Angle = source_grid.Angle
    cloned_grid.Offset = source_grid.Offset
    cloned_grid.Shift = source_grid.Shift
    try:
        cloned_grid.Origin = DB.UV(source_grid.Origin.U, source_grid.Origin.V)
    except Exception:
        pass
    segment_values = List[System.Double]()
    for segment in source_grid.GetSegments():
        segment_values.Add(float(segment))
    cloned_grid.SetSegments(segment_values)
    return cloned_grid


def clone_fill_pattern(source_pattern_element, pattern_maps):
    source_pattern = source_pattern_element.GetFillPattern()
    new_name = unique_pattern_name(
        source_pattern_element.Name,
        pattern_maps["fill_names"],
        "pyRevit Imported",
    )
    cloned_pattern = DB.FillPattern(
        new_name,
        source_pattern.Target,
        source_pattern.HostOrientation,
    )
    cloned_grids = List[DB.FillGrid]()
    for source_grid in source_pattern.GetFillGrids():
        cloned_grids.Add(clone_fill_grid(source_grid))
    cloned_pattern.SetFillGrids(cloned_grids)
    created = DB.FillPatternElement.Create(
        pattern_maps["destination_doc"], cloned_pattern
    )
    signature = fill_pattern_signature(created)
    pattern_maps["fill_names"].add(created.Name)
    pattern_maps["fill_by_name"][created.Name].append(created.Id)
    pattern_maps["fill_by_signature"][signature].append(created.Id)
    pattern_maps["created_fill_patterns"].append(created.Name)
    return created.Id


def resolve_line_pattern_id(source_doc, source_id, pattern_maps):
    value = id_value(source_id)
    if value == id_value(INVALID_ID):
        return INVALID_ID
    if value < 0:
        return source_id
    if value in pattern_maps["line_cache"]:
        return pattern_maps["line_cache"][value]

    source_pattern = source_doc.GetElement(source_id)
    if not source_pattern:
        raise Exception("Source line pattern {} was not found.".format(value))

    exact = pattern_maps["line_by_signature"].get(
        line_pattern_signature(source_pattern), []
    )
    destination_id = lowest_id(exact)
    if destination_id is None:
        destination_id = clone_line_pattern(source_pattern, pattern_maps)

    pattern_maps["line_cache"][value] = destination_id
    return destination_id


def resolve_fill_pattern_id(source_doc, source_id, pattern_maps):
    value = id_value(source_id)
    if value == id_value(INVALID_ID):
        return INVALID_ID
    if value < 0:
        return source_id
    if value in pattern_maps["fill_cache"]:
        return pattern_maps["fill_cache"][value]

    source_pattern_element = source_doc.GetElement(source_id)
    if not source_pattern_element:
        raise Exception("Source fill pattern {} was not found.".format(value))
    source_pattern = source_pattern_element.GetFillPattern()

    # Multiple exact matches are visually equivalent. Select the lowest stable
    # ElementId instead of falling back to an ambiguous name-only match.
    exact = pattern_maps["fill_by_signature"].get(
        fill_pattern_signature(source_pattern_element), []
    )
    destination_id = lowest_id(exact)

    if destination_id is None and source_pattern.IsSolidFill:
        destination_id = lowest_id(
            pattern_maps["fill_solid_by_target"].get(
                str(source_pattern.Target), []
            )
        )

    if destination_id is None:
        destination_id = clone_fill_pattern(
            source_pattern_element, pattern_maps
        )

    pattern_maps["fill_cache"][value] = destination_id
    return destination_id


def expand_group_member_pairs(source_doc, source_view, destination_doc, destination_view, element_pairs):
    """Add source/destination member pairs for copied model/detail groups."""
    expanded = list(element_pairs)
    for source_id, destination_id in list(element_pairs):
        source_element = source_doc.GetElement(source_id)
        destination_element = destination_doc.GetElement(destination_id)
        if isinstance(source_element, DB.Group) and isinstance(destination_element, DB.Group):
            source_member_ids = list(source_element.GetMemberIds())
            destination_member_ids = list(destination_element.GetMemberIds())
            member_pairs = match_copied_elements(
                source_doc,
                source_view,
                source_member_ids,
                destination_doc,
                destination_view,
                destination_member_ids,
            )
            expanded.extend(member_pairs)
    return expanded


def valid_color(color):
    try:
        return color is not None and color.IsValid
    except Exception:
        return False


def record_override_failure(failures, property_name, error):
    failures.append("{}: {}".format(property_name, error))


def copy_color_property(source_ogs, destination_ogs, property_name, applied, failures):
    try:
        color = getattr(source_ogs, property_name)
        if valid_color(color):
            getattr(destination_ogs, "Set" + property_name)(
                DB.Color(color.Red, color.Green, color.Blue)
            )
            applied.append(property_name)
    except Exception as error:
        record_override_failure(failures, property_name, error)


def copy_integer_property(source_ogs, destination_ogs, property_name, unset_value, applied, failures):
    try:
        value = getattr(source_ogs, property_name)
        if value != unset_value:
            getattr(destination_ogs, "Set" + property_name)(value)
            applied.append(property_name)
    except Exception as error:
        record_override_failure(failures, property_name, error)


def copy_boolean_property(source_ogs, destination_ogs, getter_name, setter_name, applied, failures):
    # Boolean OGS properties do not expose an "is explicitly overridden" flag.
    # Copying the current value is the closest API representation of the dialog.
    try:
        value = getattr(source_ogs, getter_name)
        getattr(destination_ogs, setter_name)(value)
        applied.append(getter_name)
    except AttributeError:
        # Property is not available in this Revit API version.
        pass
    except Exception as error:
        record_override_failure(failures, getter_name, error)


def copy_line_pattern_property(source_doc, source_ogs, destination_ogs, property_name, pattern_maps, applied, failures):
    try:
        source_pattern_id = getattr(source_ogs, property_name)
        if id_value(source_pattern_id) != id_value(INVALID_ID):
            destination_pattern_id = resolve_line_pattern_id(
                source_doc, source_pattern_id, pattern_maps
            )
            getattr(destination_ogs, "Set" + property_name)(destination_pattern_id)
            applied.append(property_name)
    except Exception as error:
        record_override_failure(failures, property_name, error)


def copy_fill_pattern_property(source_doc, source_ogs, destination_ogs, property_name, pattern_maps, applied, failures):
    try:
        source_pattern_id = getattr(source_ogs, property_name)
        if id_value(source_pattern_id) != id_value(INVALID_ID):
            destination_pattern_id = resolve_fill_pattern_id(
                source_doc, source_pattern_id, pattern_maps
            )
            getattr(destination_ogs, "Set" + property_name)(destination_pattern_id)
            applied.append(property_name)
    except Exception as error:
        record_override_failure(failures, property_name, error)


def apply_destination_overrides(source_doc, source_view, source_id, destination_view, destination_id, pattern_maps):
    """Apply every supported element override independently.

    A property-level failure is returned to the caller and does not prevent the
    remaining override properties from being transferred.
    """
    source_ogs = source_view.GetElementOverrides(source_id)
    destination_ogs = destination_view.GetElementOverrides(destination_id)
    applied = []
    failures = []

    for property_name in (
        "ProjectionLineColor",
        "CutLineColor",
        "SurfaceForegroundPatternColor",
        "SurfaceBackgroundPatternColor",
        "CutForegroundPatternColor",
        "CutBackgroundPatternColor",
    ):
        copy_color_property(
            source_ogs, destination_ogs, property_name, applied, failures
        )

    for property_name in ("ProjectionLineWeight", "CutLineWeight"):
        copy_integer_property(
            source_ogs, destination_ogs, property_name, -1, applied, failures
        )

    for property_name in ("ProjectionLinePatternId", "CutLinePatternId"):
        copy_line_pattern_property(
            source_doc,
            source_ogs,
            destination_ogs,
            property_name,
            pattern_maps,
            applied,
            failures,
        )

    for property_name in (
        "SurfaceForegroundPatternId",
        "SurfaceBackgroundPatternId",
        "CutForegroundPatternId",
        "CutBackgroundPatternId",
    ):
        copy_fill_pattern_property(
            source_doc,
            source_ogs,
            destination_ogs,
            property_name,
            pattern_maps,
            applied,
            failures,
        )

    # These visibility flags are available in newer Revit APIs. AttributeError
    # is ignored so the same script remains usable in older supported versions.
    for getter_name, setter_name in (
        ("IsSurfaceForegroundPatternVisible", "SetSurfaceForegroundPatternVisible"),
        ("IsSurfaceBackgroundPatternVisible", "SetSurfaceBackgroundPatternVisible"),
        ("IsCutForegroundPatternVisible", "SetCutForegroundPatternVisible"),
        ("IsCutBackgroundPatternVisible", "SetCutBackgroundPatternVisible"),
    ):
        copy_boolean_property(
            source_ogs,
            destination_ogs,
            getter_name,
            setter_name,
            applied,
            failures,
        )

    try:
        destination_ogs.SetSurfaceTransparency(source_ogs.Transparency)
        applied.append("Transparency")
    except Exception as error:
        record_override_failure(failures, "Transparency", error)

    copy_boolean_property(
        source_ogs,
        destination_ogs,
        "Halftone",
        "SetHalftone",
        applied,
        failures,
    )

    try:
        if source_ogs.DetailLevel != DB.ViewDetailLevel.Undefined:
            destination_ogs.SetDetailLevel(source_ogs.DetailLevel)
            applied.append("DetailLevel")
    except Exception as error:
        record_override_failure(failures, "DetailLevel", error)

    try:
        destination_view.SetElementOverrides(destination_id, destination_ogs)
    except Exception as error:
        record_override_failure(failures, "SetElementOverrides", error)
        return applied, failures

    # Element visibility is view state, not part of OverrideGraphicSettings.
    try:
        source_element = source_doc.GetElement(source_id)
        if source_element and source_element.IsHidden(source_view):
            hidden_ids = List[DB.ElementId]()
            hidden_ids.Add(destination_id)
            destination_view.HideElements(hidden_ids)
            applied.append("ElementVisibility")
    except AttributeError:
        # Older API wrappers might not expose Element.IsHidden. Do not report
        # a failure for a capability that is unavailable in that host version.
        pass
    except Exception as error:
        record_override_failure(failures, "ElementVisibility", error)

    return applied, failures


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes




def can_duplicate_legend(view):
    try:
        return view.CanViewBeDuplicated(DB.ViewDuplicateOption.Duplicate)
    except Exception:
        return False


def source_element_label(element):
    if not element:
        return "Unknown"
    try:
        return element.GetType().Name
    except Exception:
        return "Unknown"


def add_result_row(rows, doc_title, legend_name, result, element_count, override_result, message):
    rows.append([
        doc_title,
        legend_name,
        result,
        str(element_count),
        override_result,
        message,
    ])


def main():
    logger = script.get_logger()
    output = script.get_output()

    open_docs = forms.select_open_docs(title="Select Destination Documents")
    if not open_docs:
        script.exit()

    legends = forms.select_views(
        title="Select Legend Views",
        filterfunc=lambda view: view.ViewType == DB.ViewType.Legend,
        use_selection=True,
    )
    if not legends:
        forms.alert("No legend views were selected.")
        script.exit()

    output.close_others()
    output.set_title("Copy Legends to Other Documents")
    output.print_md("# Copy Legends to Other Documents")

    total_operations = len(legends) * len(open_docs)
    output.print_md(
        "**Selected legends:** {}  \n"
        "**Destination documents:** {}  \n"
        "**Total operations:** {}".format(
            len(legends), len(open_docs), total_operations
        )
    )

    result_rows = []
    override_failure_rows = []
    skipped_element_rows = []
    current_operation = 0
    succeeded_count = 0
    warning_count = 0
    failed_count = 0
    skipped_count = 0
    cancelled = False

    with forms.ProgressBar(
        title="Copying legends {value} of {max_value}",
        cancellable=True,
        step=1,
    ) as progress:
        for dest_doc in open_docs:
            if cancelled:
                break

            all_graphviews = revit.query.get_all_views(doc=dest_doc)
            all_legend_names = [
                revit.query.get_name(view)
                for view in all_graphviews
                if view.ViewType == DB.ViewType.Legend
            ]
            base_legend = revit.query.find_first_legend(doc=dest_doc)

            if not base_legend or not can_duplicate_legend(base_legend):
                reason = (
                    "No legend capable of duplication exists in the destination document."
                    if base_legend
                    else "No base legend exists in the destination document."
                )
                logger.warning("Skipping destination document '%s': %s", dest_doc.Title, reason)
                for src_legend in legends:
                    legend_name = revit.query.get_name(src_legend)
                    add_result_row(result_rows, dest_doc.Title, legend_name, "Skipped", 0, "Not attempted", reason)
                    skipped_count += 1
                    current_operation += 1
                    progress.update_progress(current_operation, total_operations)
                continue

            transaction_group = TransactionGroup(dest_doc, "Copy Legends to document")
            transaction_group.Start()
            destination_had_commit = False

            try:
                for src_legend in legends:
                    if progress.cancelled:
                        cancelled = True
                        break

                    legend_name = revit.query.get_name(src_legend)
                    operation_number = current_operation + 1
                    progress.title = "{} of {} | {} | {}".format(
                        operation_number, total_operations, dest_doc.Title, legend_name
                    )
                    progress.update_progress(operation_number, total_operations)
                    logger.info("Copying legend '%s' to document '%s'.", legend_name, dest_doc.Title)

                    view_elements = DB.FilteredElementCollector(SOURCE_DOC, src_legend.Id).ToElements()
                    candidate_ids = set(
                        id_value(element.Id) for element in view_elements if element
                    )
                    source_ids = []
                    grouped_member_count = 0
                    for element in view_elements:
                        # Reference planes copied from a legend can appear in destination
                        # model space. Exclude them intentionally.
                        is_reference_plane = isinstance(element, DB.ReferencePlane)
                        group_id = element.GroupId if element else INVALID_ID
                        is_group_member = (
                            id_value(group_id) != id_value(INVALID_ID)
                            and id_value(group_id) in candidate_ids
                        )
                        if is_group_member:
                            # ElementTransformUtils copies the group members with the
                            # parent Group. Passing both causes a many-to-one ID result.
                            grouped_member_count += 1
                            continue
                        if isinstance(element, DB.Element) and element.Category and not is_reference_plane:
                            source_ids.append(element.Id)
                        else:
                            element_id = id_value(element.Id) if element else -1
                            skipped_element_rows.append([
                                dest_doc.Title,
                                legend_name,
                                str(element_id),
                                "Reference plane or unsupported/view element",
                            ])
                    if grouped_member_count:
                        logger.info(
                            "Legend '%s': %s group member(s) will be copied through their parent group.",
                            legend_name,
                            grouped_member_count,
                        )

                    if not source_ids:
                        reason = "The source legend contains no supported elements to copy."
                        logger.warning("Skipping legend '%s' for '%s': %s", legend_name, dest_doc.Title, reason)
                        add_result_row(result_rows, dest_doc.Title, legend_name, "Skipped", 0, "Not attempted", reason)
                        skipped_count += 1
                        current_operation += 1
                        progress.update_progress(current_operation, total_operations)
                        continue

                    transaction = Transaction(dest_doc, "Copy legend and graphic overrides")
                    transaction.Start()
                    copied_ids = []
                    transferred_count = 0
                    failed_override_count = 0

                    try:
                        dest_view = dest_doc.GetElement(
                            base_legend.Duplicate(DB.ViewDuplicateOption.Duplicate)
                        )

                        options = DB.CopyPasteOptions()
                        options.SetDuplicateTypeNamesHandler(CopyUseDestination())
                        ordered_source_ids = List[DB.ElementId]()
                        for source_id in source_ids:
                            ordered_source_ids.Add(source_id)

                        copied_collection = DB.ElementTransformUtils.CopyElements(
                            src_legend,
                            ordered_source_ids,
                            dest_view,
                            None,
                            options,
                        )
                        copied_ids = [element_id for element_id in copied_collection]
                        source_ids = [element_id for element_id in ordered_source_ids]

                        if len(source_ids) != len(copied_ids):
                            raise Exception(
                                "CopyElements returned {} destination IDs for {} source IDs.".format(
                                    len(copied_ids), len(source_ids)
                                )
                            )

                        pattern_maps = build_pattern_maps(dest_doc)
                        element_pairs = match_copied_elements(
                            SOURCE_DOC,
                            src_legend,
                            source_ids,
                            dest_doc,
                            dest_view,
                            copied_ids,
                        )
                        element_pairs = expand_group_member_pairs(
                            SOURCE_DOC,
                            src_legend,
                            dest_doc,
                            dest_view,
                            element_pairs,
                        )

                        for source_id, destination_id in element_pairs:
                            try:
                                applied_properties, property_failures = apply_destination_overrides(
                                    SOURCE_DOC,
                                    src_legend,
                                    source_id,
                                    dest_view,
                                    destination_id,
                                    pattern_maps,
                                )
                                if applied_properties:
                                    transferred_count += 1
                                if property_failures:
                                    failed_override_count += 1
                                    source_element = SOURCE_DOC.GetElement(source_id)
                                    for property_failure in property_failures:
                                        override_failure_rows.append([
                                            dest_doc.Title,
                                            legend_name,
                                            str(id_value(source_id)),
                                            str(id_value(destination_id)),
                                            source_element_label(source_element),
                                            property_failure,
                                        ])
                                        logger.warning(
                                            "Graphic override property failed for legend '%s', source element %s, "
                                            "destination element %s in '%s': %s",
                                            legend_name,
                                            id_value(source_id),
                                            id_value(destination_id),
                                            dest_doc.Title,
                                            property_failure,
                                        )
                            except Exception as override_error:
                                failed_override_count += 1
                                source_element = SOURCE_DOC.GetElement(source_id)
                                override_failure_rows.append([
                                    dest_doc.Title,
                                    legend_name,
                                    str(id_value(source_id)),
                                    str(id_value(destination_id)),
                                    source_element_label(source_element),
                                    str(override_error),
                                ])
                                logger.warning(
                                    "Graphic override failed for legend '%s', source element %s, "
                                    "destination element %s in '%s': %s",
                                    legend_name,
                                    id_value(source_id),
                                    id_value(destination_id),
                                    dest_doc.Title,
                                    override_error,
                                )

                        new_name = legend_name
                        counter = 0
                        while new_name in all_legend_names:
                            counter += 1
                            new_name = legend_name + " (Duplicate {})".format(counter)

                        revit.update.set_name(dest_view, new_name)
                        dest_view.Scale = src_legend.Scale
                        all_legend_names.append(new_name)
                        transaction.Commit()
                        destination_had_commit = True

                        if failed_override_count:
                            warning_count += 1
                            result_label = "Copied with warnings"
                            message = "Created as '{}'. Some element overrides could not be transferred.".format(new_name)
                            logger.warning(
                                "Legend '%s' copied to '%s' with %s override failure(s).",
                                legend_name,
                                dest_doc.Title,
                                failed_override_count,
                            )
                        else:
                            succeeded_count += 1
                            result_label = "Copied"
                            message = "Created as '{}'.".format(new_name)
                            logger.info(
                                "Legend '%s' copied successfully to '%s' as '%s'.",
                                legend_name,
                                dest_doc.Title,
                                new_name,
                            )

                        add_result_row(
                            result_rows,
                            dest_doc.Title,
                            legend_name,
                            result_label,
                            len(copied_ids),
                            "{} applied / {} failed".format(
                                transferred_count, failed_override_count
                            ),
                            message,
                        )

                    except Exception as legend_error:
                        if transaction.GetStatus() == DB.TransactionStatus.Started:
                            transaction.RollBack()
                        failed_count += 1
                        add_result_row(
                            result_rows,
                            dest_doc.Title,
                            legend_name,
                            "Failed",
                            0,
                            "Not completed",
                            str(legend_error),
                        )
                        logger.exception(
                            "Legend '%s' could not be copied to '%s'.",
                            legend_name,
                            dest_doc.Title,
                        )

                    current_operation += 1
                    progress.update_progress(current_operation, total_operations)

                if cancelled:
                    if destination_had_commit:
                        transaction_group.Assimilate()
                    else:
                        transaction_group.RollBack()
                else:
                    transaction_group.Assimilate()

            except Exception:
                if transaction_group.GetStatus() == DB.TransactionStatus.Started:
                    transaction_group.RollBack()
                logger.exception("Unexpected destination-level failure in '%s'.", dest_doc.Title)
                raise

    output.print_table(
        table_data=result_rows,
        columns=["Destination", "Legend", "Result", "Elements", "Overrides", "Message"],
        title="Copy Results",
    )

    if override_failure_rows:
        output.print_table(
            table_data=override_failure_rows,
            columns=[
                "Destination",
                "Legend",
                "Source ID",
                "Destination ID",
                "Element Type",
                "Failure",
            ],
            title="Graphic Override Failures",
        )

    if skipped_element_rows:
        output.print_table(
            table_data=skipped_element_rows,
            columns=["Destination", "Legend", "Element ID", "Reason"],
            title="Elements Intentionally Skipped",
        )

    # CommandCustomResults is not dictionary-subscriptable in IronPython.
    # The structured output tables above are the command result record.

    completed_count = succeeded_count + warning_count
    status_message = (
        "Copy operation cancelled."
        if cancelled
        else "Legend copy operation complete."
    )
    summary = (
        "Completed: {}\n"
        "Copied successfully: {}\n"
        "Copied with warnings: {}\n"
        "Failed: {}\n"
        "Skipped: {}\n"
        "Override failures: {}\n\n"
        "See the pyRevit output window for details."
    ).format(
        completed_count,
        succeeded_count,
        warning_count,
        failed_count,
        skipped_count,
        len(override_failure_rows),
    )
    forms.alert(status_message, sub_msg=summary)


if __name__ == "__main__":
    main()
