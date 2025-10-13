# -*- coding: UTF-8 -*-

__cleanengine__ = True
__fullframeengine__ = True
__persistentengine__ = True

from traceback import format_exc
from csv import writer, reader
from os.path import isfile
from datetime import datetime, timedelta
from operator import attrgetter
from collections import OrderedDict
from System.Collections.Generic import HashSet

from pyrevit.coreutils import Timer
from pyrevit import HOST_APP
from pyrevit import DB
from pyrevit.script import get_config, get_logger
from pyrevit.forms import alert, show_balloon
from pyrevit.output.cards import card_builder, create_frame
from pyrevit.revit.db import ProjectInfo as RevitProjectInfo
from pyrevit.preflight import PreflightTestCase
import pyrevit.revit.db.query as q
import pyrevit.revit.db.count as cnt

logger = get_logger()

BODY_CSS = '<style>.grid-container { display: grid; justify-content: center; align-items: center; }</style><div class="grid-container">'

config = get_config()
try:
    CURRENT_FOLDER = config.get_option("current_folder")
    CRITICAL_WARNINGS = config.get_option("critical_warnings")
    EXPORT_FILE_PATH = config.get_option("export_file_path")
except:
    alert(
        "No configuration set, run the Preflight Checks configuration mode using SHIFT+Click. ",
        exitscript=True,
    )

FILE_INFO_HEADERS = [
    "Project Name",
    "Project Number",
    "Client Name",
    "Project Phases",
    "Worksets",
    "Linked File Name",
    "Instance Name",
    "Loaded Status",
    "Pinned status",
]

VALID_VIEW_TYPES = [
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.Elevation,
    DB.ViewType.ThreeD,
    DB.ViewType.Schedule,
    DB.ViewType.DrawingSheet,
    DB.ViewType.Report,
    DB.ViewType.DraftingView,
    DB.ViewType.Legend,
    DB.ViewType.EngineeringPlan,
    DB.ViewType.AreaPlan,
    DB.ViewType.Section,
    DB.ViewType.Detail,
    DB.ViewType.CostReport,
    DB.ViewType.LoadsReport,
    DB.ViewType.PresureLossReport,
    DB.ViewType.ColumnSchedule,
    DB.ViewType.PanelSchedule,
    DB.ViewType.Walkthrough,
    DB.ViewType.Rendering,
    DB.ViewType.SystemsAnalysisReport,
]

INVALID_VIEW_TYPES = [
    DB.ViewType.Undefined,
    DB.ViewType.ProjectBrowser,
    DB.ViewType.SystemBrowser,
    DB.ViewType.Internal,
]


class Metadata:
    """Encapsulates user and date metadata."""

    def __init__(self):
        self.user = HOST_APP.username
        self.date = datetime.today().strftime("%d-%m-%Y")


class DocumentInfo:
    """Handles document-specific information."""

    def __init__(self, document):
        self.clean_name = q.get_document_clean_name(document)
        self.revit_version_build = HOST_APP.build


class ProjectInfoData:
    """Encapsulates project metadata from Revit."""

    def __init__(self, document):
        revit_project_info = RevitProjectInfo(document)
        self.name = revit_project_info.name
        self.number = revit_project_info.number
        self.client = revit_project_info.client_name
        self.phases = q.get_phases_names(document)
        self.worksets_names = q.get_worksets_names(document)


class ElementCounts:
    """Manages element-related counts."""

    def __init__(self, document):
        self.element_count = (
            DB.FilteredElementCollector(document)
            .WhereElementIsNotElementType()
            .GetElementCount()
        )
        self.purgeable_elements_count = len(
            document.GetUnusedElements(HashSet[DB.ElementId]())
        )
        self.activated_analytical_model_elements_count = (
            cnt.count_analytical_model_activated(document)
        )


class WarningsInfo:
    """Handles warning metrics."""

    def __init__(self, document):
        warnings = document.GetWarnings()
        self.all_warnings_count = len(warnings)
        self.critical_warnings_count = q.get_critical_warnings_count(
            warnings, CRITICAL_WARNINGS
        )


class RoomInfo:
    """Manages room-related data."""

    def __init__(self, document):
        rooms = q.get_elements_by_categories(
            [DB.BuiltInCategory.OST_Rooms], doc=document
        )
        self.rooms_count = len(rooms)
        self.unplaced_rooms_count = cnt.count_unplaced_rooms(rooms)
        self.unbounded_rooms = cnt.count_unbounded_rooms(rooms)


class SheetViewInfo:
    """Handles sheets and views metrics."""

    def __init__(self, document, sheets_set, views):
        schedules = [
            schedule for schedule in views if schedule.ViewType == DB.ViewType.Schedule
        ]
        self.sheets_count = len(sheets_set)
        self.views_count = len(views)
        self.views_floorplans_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.FloorPlan
        )
        self.views_ceilingplans_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.CeilingPlan
        )
        self.views_elevations_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.Elevation
        )
        self.views_threed_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.ThreeD
        )
        self.schedules_count = len(schedules)
        self.views_drawingsheet_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.DrawingSheet
        )
        self.reports_count = sum(1 for x in views if x.ViewType == DB.ViewType.Report)
        self.views_drafting_view_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.DraftingView
        )
        self.views_legend_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.Legend
        )
        self.views_engineering_plan_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.EngineeringPlan
        )
        self.views_area_plan_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.AreaPlan
        )
        self.views_sections_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.Section
        )
        self.views_detail_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.Detail
        )
        self.views_cost_report_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.CostReport
        )
        self.views_loads_report_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.LoadsReport
        )
        self.views_presure_loss_report_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.PresureLossReport
        )
        self.views_column_schedule_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.ColumnSchedule
        )
        self.views_panel_schedule_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.PanelSchedule
        )
        self.views_walkthrough_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.Walkthrough
        )
        self.views_rendering_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.Rendering
        )
        self.views_systems_analysis_report_count = sum(
            1 for x in views if x.ViewType == DB.ViewType.SystemsAnalysisReport
        )
        self.views_not_on_sheets = sum(
            1
            for x in views
            if x.GetPlacementOnSheetStatus() == DB.ViewPlacementOnSheetStatus.NotPlaced
        )
        self.schedules_not_sheeted_count = sum(
            1
            for x in schedules
            if x.GetPlacementOnSheetStatus() == DB.ViewPlacementOnSheetStatus.NotPlaced
        )
        self.copied_views_count = cnt.count_copied_views(views)


class ViewTemplateFilterInfo:
    """Manages view templates and filters."""

    def __init__(self, document, views):
        view_template_list = q.get_all_view_templates(document)
        self.view_templates_count = len(view_template_list)
        self.unused_view_templates_count = cnt.count_unused_view_templates(
            views, document
        )
        filters_list = q.get_elements_by_class(DB.ParameterFilterElement, doc=document)
        self.all_filters_count = len(filters_list)
        self.unused_view_filters_count = cnt.count_unused_filters_in_views(
            views, filters_list
        )


class MaterialsLinePatternInfo:
    """Handles materials and line patterns."""

    def __init__(self, document):
        self.materials_count = len(
            q.get_elements_by_categories(
                [DB.BuiltInCategory.OST_Materials], doc=document
            )
        )
        self.line_patterns_count = len(
            q.get_elements_by_class(DB.LinePatternElement, doc=document)
        )


class LinksInfo:
    """Manages linked files data."""

    def __init__(self, document, rvtlinks_elements_items):
        self.rvtlinks_count = len(q.get_all_linkeddocs(document))
        self.dwgs_count = len(q.get_elements_by_class(DB.ImportInstance, doc=document))
        self.linked_dwg_count = cnt.count_linked_dwg_files(document)
        self.imported_dwg = self.dwgs_count - self.linked_dwg_count
        self.rvtlinks_unpinned_count = cnt.count_unpinned_revit_links(
            rvtlinks_elements_items
        )


class FamilyInfo:
    """Handles family-related metrics."""

    def __init__(self, document):
        self.family_count = cnt.count_total_families(document)
        self.inplace_family_count = cnt.count_in_place_families(document)
        self.not_parametric_families_count = sum(
            1
            for family in q.get_families(document, only_editable=True)
            if not family.IsParametric
        )
        self.imports_subcats_count = len(
            [
                sb
                for sb in document.Settings.Categories.get_Item(
                    DB.BuiltInCategory.OST_ImportObjectStyles
                ).SubCategories
            ]
        )
        self.generic_models_types_count = (
            DB.FilteredElementCollector(document)
            .OfCategory(DB.BuiltInCategory.OST_GenericModel)
            .WhereElementIsElementType()
            .GetElementCount()
        )
        self.detail_components_count = len(
            q.get_elements_by_categories(
                [DB.BuiltInCategory.OST_DetailComponents], doc=document
            )
        )
        self.detail_lines_count = sum(
            1
            for line in q.get_elements_by_categories(
                [DB.BuiltInCategory.OST_Lines], doc=document
            )
            if line.CurveElementType is DB.CurveElementType.DetailCurve
        )


class TextNotesInfo:
    """Manages text note metrics."""

    def __init__(self, document):
        text_notes = q.get_elements_by_class(DB.TextNote, doc=document)
        text_notes_types = q.get_types_by_class(DB.TextNoteType, doc=document)
        self.text_notes_count = len(text_notes)
        self.text_notes_types_count = len(text_notes_types)
        self.text_notes_types_wf_count = (
            cnt.count_textnote_types_with_changed_width_factor(text_notes_types)
        )
        self.text_bg_count = cnt.count_textnote_types_with_opaque_background(
            text_notes_types
        )
        self.text_notes_caps_count = cnt.count_text_notes_with_all_caps(text_notes)


class GroupInfo:
    """Handles group-related data."""

    def __init__(self, document):
        (
            model_groups_instances_count,
            model_groups_types_count,
            detail_groups_instances_count,
            detail_groups_types_count,
        ) = cnt.count_groups(document)
        self.detail_groups_instances_count = detail_groups_instances_count
        self.detail_groups_types_count = detail_groups_types_count
        self.model_groups_instances_count = model_groups_instances_count
        self.model_groups_types_count = model_groups_types_count


class ReferencePlaneInfo:
    """Manages reference plane metrics."""

    def __init__(self, document):
        reference_planes = q.get_elements_by_class(DB.ReferencePlane, doc=document)
        self.reference_planes_count = len(reference_planes)
        self.unnamed_ref_planes_count = cnt.count_unnamed_reference_planes(
            reference_planes
        )


class DimensionsInfo:
    """Handles dimension-related data."""

    def __init__(self, document):
        dimensions = [
            d
            for d in q.get_elements_by_categories(
                [DB.BuiltInCategory.OST_Dimensions], doc=document
            )
            if d.OwnerViewId and d.ViewSpecific and d.View
        ]
        dimensions_types = (
            DB.FilteredElementCollector(document)
            .OfClass(DB.DimensionType)
            .WhereElementIsElementType()
            .ToElements()
        )
        self.dim_types_count = len(dimensions_types)
        self.dim_count = len(dimensions)
        self.dim_overrides_count = cnt.count_dimension_overrides(dimensions)


class RevisionsInfo:
    """Manages revision clouds count."""

    def __init__(self, document):
        self.revision_clouds_count = cnt.count_revision_clouds(document)


class ReportData:
    """
    ReportData class is responsible for collecting and organizing various pieces of information
    about a Revit document and its associated metadata, project information, element counts, warnings,
    links, families, text notes, groups, reference planes, dimensions, and revisions.

    Attributes:
        _KEY_MAPPING (OrderedDict): A mapping of keys to attribute paths for various pieces of information.

    Methods:
        __init__(self, document=None):
            Initializes the ReportData instance with the provided Revit document.
        COLUMNS(self):
            Returns a list of column names based on the keys in _KEY_MAPPING.
        to_list(self):
        export_to_csv(self, export_file_path=EXPORT_FILE_PATH, headers=None):
    """

    _KEY_MAPPING = OrderedDict(
        [
            ("user", "metadata.user"),
            ("date", "metadata.date"),
            ("doc_clean_name", "document_info.clean_name"),
            ("revit_version_build", "document_info.revit_version_build"),
            ("project_name", "project_info.name"),
            ("project_number", "project_info.number"),
            ("project_client", "project_info.client"),
            ("project_phases", "project_info.phases"),
            ("worksets_names", "project_info.worksets_names"),
            ("element_count", "element_counts.element_count"),
            ("purgeable_elements_count", "element_counts.purgeable_elements_count"),
            ("all_warnings_count", "warnings_info.all_warnings_count"),
            ("critical_warnings_count", "warnings_info.critical_warnings_count"),
            ("rvtlinks_count", "links_info.rvtlinks_count"),
            (
                "activated_analytical_model_elements_count",
                "element_counts.activated_analytical_model_elements_count",
            ),
            ("rooms_count", "room_info.rooms_count"),
            ("unplaced_rooms_count", "room_info.unplaced_rooms_count"),
            ("unbounded_rooms", "room_info.unbounded_rooms"),
            ("sheets_count", "sheet_view_info.sheets_count"),
            ("views_count", "sheet_view_info.views_count"),
            ("views_floorplans_count", "sheet_view_info.views_floorplans_count"),
            ("views_ceilingplans_count", "sheet_view_info.views_ceilingplans_count"),
            ("views_elevations_count", "sheet_view_info.views_elevations_count"),
            ("views_threed_count", "sheet_view_info.views_threed_count"),
            ("schedules", "sheet_view_info.schedules_count"),
            ("views_drawingsheet_count", "sheet_view_info.views_drawingsheet_count"),
            ("views_reports_count", "sheet_view_info.reports_count"),
            ("views_drafting_view_count", "sheet_view_info.views_drafting_view_count"),
            ("views_legend_count", "sheet_view_info.views_legend_count"),
            (
                "views_engineering_plan_count",
                "sheet_view_info.views_engineering_plan_count",
            ),
            ("views_area_plan_count", "sheet_view_info.views_area_plan_count"),
            ("views_sections_count", "sheet_view_info.views_sections_count"),
            ("views_detail_count", "sheet_view_info.views_detail_count"),
            ("views_cost_report_count", "sheet_view_info.views_cost_report_count"),
            ("views_loads_report_count", "sheet_view_info.views_loads_report_count"),
            (
                "views_presure_loss_report_count",
                "sheet_view_info.views_presure_loss_report_count",
            ),
            (
                "views_column_schedule_count",
                "sheet_view_info.views_column_schedule_count",
            ),
            (
                "views_panel_schedule_count",
                "sheet_view_info.views_panel_schedule_count",
            ),
            ("views_walkthrough_count", "sheet_view_info.views_walkthrough_count"),
            ("views_rendering_count", "sheet_view_info.views_rendering_count"),
            (
                "views_systems_analysis_report_count",
                "sheet_view_info.views_systems_analysis_report_count",
            ),
            ("views_not_on_sheets", "sheet_view_info.views_not_on_sheets"),
            (
                "schedules_not_sheeted_count",
                "sheet_view_info.schedules_not_sheeted_count",
            ),
            ("copied_views_count", "sheet_view_info.copied_views_count"),
            ("view_templates_count", "view_template_filter_info.view_templates_count"),
            (
                "unused_view_templates_count",
                "view_template_filter_info.unused_view_templates_count",
            ),
            ("all_filters_count", "view_template_filter_info.all_filters_count"),
            (
                "unused_view_filters_count",
                "view_template_filter_info.unused_view_filters_count",
            ),
            ("materials_count", "materials_line_pattern_info.materials_count"),
            ("line_patterns_count", "materials_line_pattern_info.line_patterns_count"),
            ("dwgs_count", "links_info.dwgs_count"),
            ("linked_dwg_count", "links_info.linked_dwg_count"),
            ("imported_dwg", "links_info.imported_dwg"),
            ("inplace_family_count", "family_info.inplace_family_count"),
            (
                "not_parametric_families_count",
                "family_info.not_parametric_families_count",
            ),
            ("family_count", "family_info.family_count"),
            ("imports_subcats_count", "family_info.imports_subcats_count"),
            ("generic_models_types_count", "family_info.generic_models_types_count"),
            ("detail_components_count", "family_info.detail_components_count"),
            ("text_notes_types_count", "text_notes_info.text_notes_types_count"),
            ("text_notes_types_wf_count", "text_notes_info.text_notes_types_wf_count"),
            ("text_bg_count", "text_notes_info.text_bg_count"),
            ("text_notes_count", "text_notes_info.text_notes_count"),
            ("text_notes_caps_count", "text_notes_info.text_notes_caps_count"),
            (
                "detail_groups_instances_count",
                "group_info.detail_groups_instances_count",
            ),
            ("detail_groups_types_count", "group_info.detail_groups_types_count"),
            ("model_groups_instances_count", "group_info.model_groups_instances_count"),
            ("model_groups_types_count", "group_info.model_groups_types_count"),
            ("reference_planes_count", "reference_plane_info.reference_planes_count"),
            (
                "unnamed_ref_planes_count",
                "reference_plane_info.unnamed_ref_planes_count",
            ),
            ("detail_lines_count", "family_info.detail_lines_count"),
            ("dim_types_count", "dimensions_info.dim_types_count"),
            ("dim_count", "dimensions_info.dim_count"),
            ("dim_overrides_count", "dimensions_info.dim_overrides_count"),
            ("revision_clouds_count", "revisions_info.revision_clouds_count"),
        ]
    )

    def __init__(self, document):

        sheets_set = q.get_sheets(doc=document)
        views = q.get_elements_by_categories(
            [
                DB.BuiltInCategory.OST_Views,
                DB.BuiltInCategory.OST_Sections,
                DB.BuiltInCategory.OST_Schedules,
                DB.BuiltInCategory.OST_PipeSchedules,
                DB.BuiltInCategory.OST_HVAC_Load_Schedules,
            ],
            doc=document,
        )
        views_without_templates = []
        for v in views:
            if (
                hasattr(v, "IsTemplate")
                and v.IsTemplate is False
                and v.ViewType not in INVALID_VIEW_TYPES
            ):
                views_without_templates.append(v)
            # else:
            #     print(v.Name, v.Category.Name)
        self.rvtlinks_elements_items = q.get_linked_model_instances(
            document
        ).ToElements()
        # Initialize component classes
        self.metadata = Metadata()
        self.document_info = DocumentInfo(document)
        self.project_info = ProjectInfoData(document)
        self.element_counts = ElementCounts(document)
        self.warnings_info = WarningsInfo(document)
        self.room_info = RoomInfo(document)
        self.sheet_view_info = SheetViewInfo(
            document, sheets_set, views_without_templates
        )
        self.view_template_filter_info = ViewTemplateFilterInfo(document, views)
        self.materials_line_pattern_info = MaterialsLinePatternInfo(document)
        self.links_info = LinksInfo(document, self.rvtlinks_elements_items)
        self.family_info = FamilyInfo(document)
        self.text_notes_info = TextNotesInfo(document)
        self.group_info = GroupInfo(document)
        self.reference_plane_info = ReferencePlaneInfo(document)
        self.dimensions_info = DimensionsInfo(document)
        self.revisions_info = RevisionsInfo(document)

    @property
    def COLUMNS(self):
        """
        Returns the list of column names.
        This method retrieves the keys from the _KEY_MAPPING dictionary and
        returns them as a list of column names.

        Returns:
            list: A list of column names.
        """
        return list(self._KEY_MAPPING.keys())

    def to_list(self):
        """
        Converts the attributes of the instance to a list of formatted string values.
        The method iterates over the columns defined in `self.COLUMNS` and retrieves
        the corresponding attribute values from the instance. Each value is then
        formatted and escaped for HTML.

        Returns:
            list: A list of formatted and HTML-escaped string values corresponding
                  to the instance's attributes defined in `self.COLUMNS`.
        """

        def html_escape(s):
            escape_map = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;",
            }
            return "".join(escape_map.get(c, c) for c in str(s))

        def format_value(value):
            if isinstance(value, list):
                return '"{}"'.format(", ".join(html_escape(v) for v in value))
            return html_escape(value)

        return [
            format_value(attrgetter(attr_path)(self))
            for key, attr_path in self._KEY_MAPPING.items()
        ]

    def export_to_csv(self, export_file_path=EXPORT_FILE_PATH, headers=None):
        """
        Exports the current data to a CSV file.
        If the CSV file does not exist, it creates a new file and writes the headers and data.
        If the CSV file exists, it appends the data only if a row with the same date and document name does not already exist.

        Args:
            export_file_path (str): The path to the CSV file. Defaults to EXPORT_FILE_PATH.
            headers (list, optional): The list of headers for the CSV file. Defaults to self.COLUMNS.

        Returns:
            None
        """
        if headers is None:
            headers = self.COLUMNS
        if export_file_path is None:
            return
        if not isfile(export_file_path):
            with open(export_file_path, mode="wb") as csv_file:
                w = writer(csv_file, lineterminator="\n")
                w.writerow(headers)
                w.writerow(self.to_list())
        else:
            with open(export_file_path, mode="rb") as csv_file:
                r = reader(csv_file, delimiter=",")
                flag = any(
                    row[1] == self.metadata.date
                    and row[2] == self.document_info.clean_name
                    for row in r
                )
            if not flag:
                with open(export_file_path, mode="ab") as csv_file:
                    w = writer(csv_file, lineterminator="\n")
                    w.writerow(self.to_list())


def get_revit_link_pinning_status(rvtlink_instance=None):
    """
    Get the pinning status of a Revit link instance.

    Args:
        rvtlink_instance (object, optional): The Revit link instance to check. Defaults to None.

    Returns:
        str: "Pinned" if the instance is pinned, "Unpinned" if the instance is not pinned,
             and "-" if the instance does not have a "Pinned" attribute.
    """
    return (
        "-"
        if not hasattr(rvtlink_instance, "Pinned")
        else "Unpinned" if not rvtlink_instance.Pinned else "Pinned"
    )


def generate_html_content(data, links_cards=""):
    """
    Generates HTML content for audit reports using the provided data and optional links cards.

    Args:
        data (ReportData): The data source for generating report metrics.
        links_cards (str, optional): HTML content for linked elements. Defaults to an empty string.

    Returns:
        str: Combined HTML content for the report.
    """
    critical_elements_frame = create_frame(
        "Critical Elements",
        card_builder(100000, data.element_counts.element_count, " Elements"),
        card_builder(
            1000, data.element_counts.purgeable_elements_count, " Purgeable (2024+)"
        ),
        card_builder(100, data.warnings_info.all_warnings_count, " Warnings"),
        card_builder(
            5, data.warnings_info.critical_warnings_count, " Critical Warnings"
        ),
        card_builder(
            0,
            data.element_counts.activated_analytical_model_elements_count,
            " Analytical Model ON",
        ),
        links_cards,
    )
    rooms_frame = create_frame(
        "Rooms",
        card_builder(1000, data.room_info.rooms_count, " Rooms"),
        card_builder(0, data.room_info.unplaced_rooms_count, " Unplaced Rooms"),
        card_builder(0, data.room_info.unbounded_rooms, " Unbounded Rooms"),
    )
    sheets_views_graphics_frame = create_frame(
        "Sheets, Views key numbers",
        card_builder(500, data.sheet_view_info.sheets_count, " Sheets"),
        card_builder(1500, data.sheet_view_info.views_count, " Views"),
        card_builder(
            300, data.sheet_view_info.views_not_on_sheets, " Views not on Sheets"
        ),
        card_builder(
            50,
            data.sheet_view_info.schedules_not_sheeted_count,
            " Schedules not on sheet",
        ),
        card_builder(0, data.sheet_view_info.copied_views_count, " Copied Views"),
    )
    view_types_frame = create_frame(
        "View Count per Type",
        card_builder(500, data.sheet_view_info.views_floorplans_count, " Floor Plans"),
        card_builder(
            500, data.sheet_view_info.views_ceilingplans_count, " Ceiling Plans"
        ),
        card_builder(200, data.sheet_view_info.views_elevations_count, " Elevations"),
        card_builder(100, data.sheet_view_info.views_threed_count, " 3D Views"),
        card_builder(100, data.sheet_view_info.schedules_count, " Schedules"),
        card_builder(
            600, data.sheet_view_info.views_drawingsheet_count, " Drawing Sheets"
        ),
        card_builder(100, data.sheet_view_info.reports_count, " Reports"),
        card_builder(
            200, data.sheet_view_info.views_drafting_view_count, " Drafting Views"
        ),
        card_builder(100, data.sheet_view_info.views_legend_count, " Legends"),
        card_builder(
            100, data.sheet_view_info.views_engineering_plan_count, " Engineering Plans"
        ),
        card_builder(100, data.sheet_view_info.views_area_plan_count, " Area Plans"),
        card_builder(200, data.sheet_view_info.views_sections_count, " Sections"),
        card_builder(500, data.sheet_view_info.views_detail_count, " Detail Views"),
        card_builder(
            100, data.sheet_view_info.views_cost_report_count, " Cost Reports"
        ),
        card_builder(
            100, data.sheet_view_info.views_loads_report_count, " Loads Reports"
        ),
        card_builder(
            100,
            data.sheet_view_info.views_presure_loss_report_count,
            " Pressure Loss Reports",
        ),
        card_builder(
            100, data.sheet_view_info.views_column_schedule_count, " Column Schedules"
        ),
        card_builder(
            100, data.sheet_view_info.views_panel_schedule_count, " Panel Schedules"
        ),
        card_builder(
            100, data.sheet_view_info.views_walkthrough_count, " Walkthroughs"
        ),
        card_builder(100, data.sheet_view_info.views_rendering_count, " Renderings"),
        card_builder(
            100,
            data.sheet_view_info.views_systems_analysis_report_count,
            " Systems Analysis Reports",
        ),
    )

    templates_filters_frame = create_frame(
        "Templates & Filters",
        card_builder(
            100, data.view_template_filter_info.view_templates_count, " View Templates"
        ),
        card_builder(
            0,
            data.view_template_filter_info.unused_view_templates_count,
            " Unused View Templates",
        ),
        card_builder(0, data.view_template_filter_info.all_filters_count, " Filters"),
        card_builder(
            0,
            data.view_template_filter_info.unused_view_filters_count,
            " Unused Filters",
        ),
    )
    cad_files_frame = create_frame(
        "CAD Files",
        card_builder(5, data.links_info.dwgs_count, " DWGs"),
        card_builder(5, data.links_info.linked_dwg_count, " Linked DWGs"),
        card_builder(1, data.links_info.imported_dwg, " Imported DWGs"),
    )
    families_frame = create_frame(
        "Families",
        card_builder(500, data.family_info.family_count, " Families"),
        card_builder(0, data.family_info.inplace_family_count, " In-Place Families"),
        card_builder(
            100,
            data.family_info.not_parametric_families_count,
            " Non-Parametric Families",
        ),
        card_builder(
            0, data.family_info.imports_subcats_count, " CAD Layers Imports in Families"
        ),
        card_builder(
            50, data.family_info.generic_models_types_count, " Generic Models Types"
        ),
        card_builder(
            100, data.family_info.detail_components_count, " Detail Components"
        ),
    )
    graphical2d_elements_frame = create_frame(
        "Graphical 2D Elements",
        card_builder(5000, data.family_info.detail_lines_count, " Detail Lines"),
        card_builder(
            30, data.materials_line_pattern_info.line_patterns_count, " Line Patterns"
        ),
        card_builder(
            30, data.text_notes_info.text_notes_types_count, " Text Notes Types"
        ),
        card_builder(
            2000, data.text_notes_info.text_notes_count, " Text Notes Instances"
        ),
        card_builder(
            1, data.text_notes_info.text_bg_count, " Text Notes Types Solid Background"
        ),
        card_builder(
            0,
            data.text_notes_info.text_notes_types_wf_count,
            " Text Notes Width Factor !=1",
        ),
        card_builder(
            100, data.text_notes_info.text_notes_caps_count, " Text Notes allCaps"
        ),
        card_builder(5, data.dimensions_info.dim_types_count, " Dimension Types"),
        card_builder(5000, data.dimensions_info.dim_count, " Dimensions"),
        card_builder(
            0, data.dimensions_info.dim_overrides_count, " Dimension Overrides"
        ),
        card_builder(
            100, data.revisions_info.revision_clouds_count, " Revision Clouds"
        ),
    )
    groups_summary_frame = create_frame(
        "Groups",
        card_builder(
            10, data.group_info.model_groups_instances_count, " Model Group Instances"
        ),
        card_builder(5, data.group_info.model_groups_types_count, " Model Group Types"),
        card_builder(
            10, data.group_info.detail_groups_instances_count, " Detail Group Instances"
        ),
        card_builder(
            20, data.group_info.detail_groups_types_count, " Detail Group Types"
        ),
    )
    reference_planes_frame = create_frame(
        "Reference Planes",
        card_builder(
            100, data.reference_plane_info.reference_planes_count, " Ref Planes"
        ),
        card_builder(
            10,
            data.reference_plane_info.unnamed_ref_planes_count,
            " Ref Planes no_name",
        ),
    )
    materials_frame = create_frame(
        "Materials",
        card_builder(
            100, data.materials_line_pattern_info.materials_count, " Materials"
        ),
    )

    html_content = (
        BODY_CSS
        + critical_elements_frame
        + rooms_frame
        + sheets_views_graphics_frame
        + view_types_frame
        + templates_filters_frame
        + cad_files_frame
        + families_frame
        + graphical2d_elements_frame
        + groups_summary_frame
        + reference_planes_frame
        + materials_frame
    )
    return html_content + "</div>"


def audit_document(doc, output):
    """
    Audits a Revit document and generates a report.

    Parameters:
        doc (Document): The Revit document to audit.
        output (Output): The output object to print the report.

    The function performs the following steps:
        1. Checks if the document is a family document and exits if true.
        2. Collects report data from the document.
        3. Displays a balloon notification if there are warnings in the document.
        4. Configures the output dimensions.
        5. Prints main file information.
        6. Prints linked files information if any linked files are present.
        7. Generates and prints an HTML report.
        8. Exports the report data to a CSV file.
        9. Generates a detailed report for RVTLinks if present.

    Exceptions:
        Logs errors and prints the stack trace if any exception occurs during the process.
    """
    try:
        if doc.IsFamilyDocument:
            alert("This tool is for project files only. Exiting...")
            return
        data = ReportData(doc)
        warnings_count = data.warnings_info.all_warnings_count
        if warnings_count > 0:
            show_balloon(
                header="Warnings",
                text="The file {} contains {} warnings".format(
                    data.document_info.clean_name, warnings_count
                ),
                is_favourite=True,
                is_new=True,
            )

        output.close_others()
        output.set_height(900)
        output.set_width(1400)

        # Main file infos
        project_info = [
            data.project_info.name,
            data.project_info.number,
            data.project_info.client,
            data.project_info.phases,
            data.project_info.worksets_names,
            "N/A",
            "N/A",
            "N/A",
            "N/A",
        ]
        output.print_md("# Main File Infos")
        output.print_table([project_info], columns=FILE_INFO_HEADERS)

        # Linked files infos
        links_cards = ""
        link_data = []
        links_documents_data = []
        for rvt_link_instance in q.get_linked_model_instances(doc).ToElements():
            link_doc = rvt_link_instance.GetLinkDocument()
            link_document_data = ReportData(link_doc)
            link_data.append(
                [
                    link_document_data.project_info.name,
                    link_document_data.project_info.number,
                    link_document_data.project_info.client,
                    link_document_data.project_info.phases,
                    link_document_data.project_info.worksets_names,
                    link_document_data.document_info.clean_name,
                    q.get_rvt_link_instance_name(rvt_link_instance),
                    str(
                        doc.GetElement(
                            rvt_link_instance.GetTypeId()
                        ).GetLinkedFileStatus()
                    ).split(".")[-1],
                    get_revit_link_pinning_status(rvt_link_instance),
                ]
            )
            links_documents_data.append(link_document_data)
        if link_data:
            output.print_md("# Linked Files Infos")
            output.print_table(link_data, columns=FILE_INFO_HEADERS)
            links_cards = card_builder(
                50, data.links_info.rvtlinks_count, " Links"
            ) + card_builder(
                0, data.links_info.rvtlinks_unpinned_count, " Links not pinned"
            )

        output.print_md(
            "# <p style='text-align: center;'>" + data.document_info.clean_name + "</p>"
        )
        html_content = generate_html_content(data, links_cards)
        output.print_html(html_content)

        data.export_to_csv()

        if data.rvtlinks_elements_items:
            output.print_md("# RVTLinks")
            for link_doc_data in links_documents_data:
                generate_rvt_links_report(link_doc_data, output)
    except Exception as e:
        print(format_exc())
        print(e)


def generate_rvt_links_report(link_document_data, output):
    """
    Generates a report for Revit links in a given document and outputs it in markdown and HTML formats.

    Args:
        link_document_data (object): An object containing information about the Revit links in the document.
        output (object): An output object with methods to print markdown and HTML content.

    Returns:
        None
    """
    doc_clean_name = link_document_data.document_info.clean_name
    output.print_md("## " + doc_clean_name)
    output.print_md("___")
    links_data = ""
    if link_document_data.rvtlinks_elements_items:
        links_data = card_builder(
            50, link_document_data.links_info.rvtlinks_count, " Links"
        ) + card_builder(
            0,
            link_document_data.links_info.rvtlinks_unpinned_count,
            " Links not pinned",
        )
    html_content = generate_html_content(link_document_data, links_data)
    output.print_html(html_content)
    link_document_data.export_to_csv()


class ModelChecker(PreflightTestCase):
    """
    Preflight audit of all models, including linked models.
    !!Links must be loaded.!!
    This QC tools returns the following data:
    - project name, number, client, phases, worksets
    - element count
    - purgeable elements count
    - all warnings count
    - critical warnings count
    - rvtlinks count
    - activated analytical model elements count
    - rooms count
    - unplaced rooms count
    - unbounded rooms count
    - sheets count
    - views count per ViewType
    - views not on sheets
    - schedules not sheeted count
    - copied views count
    - view templates count
    - unused view templates count
    - filters count
    - unused view filters count
    - materials count
    - line patterns count
    - dwgs count
    - linked dwg count
    - imported dwg count
    - inplace family count
    - not parametric families count
    - family count
    - imports subcats count
    - generic models types count
    - detail components count
    - text notes types count
    - text notes types with width factor != 1
    - text notes count
    - text notes with allCaps applied
    - text notes with solid background
    - detail groups count
    - detail groups types count
    - model group count
    - model group type count
    - reference planes count
    - unnamed reference planes count
    - detail lines count
    - dimension types count
    - dimension count
    - dimension overrides count
    - revision clouds count
    """

    name = "Audit All (Including Links)"
    author = "Jean-Marc Couffin"

    def setUp(self, doc, output):
        self.timer = Timer()

    def startTest(self, doc, output):
        audit_document(doc, output)

    def tearDown(self, doc, output):
        endtime = self.timer.get_time()
        endtime_hms = str(timedelta(seconds=endtime))
        endtime_hms_claim = " \n\nCheck duration " + endtime_hms[0:7]
        output.print_md(endtime_hms_claim)
