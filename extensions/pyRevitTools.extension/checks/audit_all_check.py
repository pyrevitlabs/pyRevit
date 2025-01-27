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

from pyrevit.coreutils import Timer
from pyrevit import HOST_APP
from pyrevit import DB
from pyrevit.script import get_config, get_logger
from pyrevit.forms import alert, show_balloon
from pyrevit.output.cards import card_builder, create_frame
from pyrevit.revit.db import ProjectInfo as RevitProjectInfo
from pyrevit.revit.db.query import (
    get_phases_names,
    get_worksets_names,
    get_warnings_count,
    get_critical_warnings_count,
    get_document_clean_name,
    get_sheets,
    get_all_views,
    get_all_view_templates,
    get_elements_by_categories,
    get_families,
    get_elements_by_class,
    get_all_linkeddocs,
    get_linked_model_instances,
    get_rvt_link_instance_name,
)
from pyrevit.preflight import PreflightTestCase
from pyrevit.revit.db.count import (
    count_unpinned_revit_links,
    count_rooms,
    count_unplaced_rooms,
    count_unbounded_rooms,
    count_unplaced_views,
    count_analytical_model_activated,
    count_total_schedules,
    count_unplaced_schedules,
    count_copied_views,
    count_unused_view_templates,
    count_filters,
    count_unused_filters_in_views,
    count_total_dwg_files,
    count_linked_dwg_files,
    count_in_place_families,
    count_non_parametric_families,
    count_total_families,
    count_import_subcategories,
    count_detail_components,
    count_total_textnote_types,
    count_textnote_types_with_changed_width_factor,
    count_textnote_types_with_opaque_background,
    count_text_notes,
    count_text_notes_with_all_caps,
    count_detail_groups_types,
    count_detail_group_instances,
    count_model_groups_types,
    count_model_group_instances,
    count_reference_planes,
    count_unnamed_reference_planes,
    count_elements,
    count_detail_lines,
    count_dimensions,
    count_dimension_types,
    count_dimension_overrides,
    count_revision_clouds,
    count_purgeable_elements,
)

logger = get_logger()

BODY_CSS = '<style>.grid-container { display: grid; justify-content: center; align-items: center; }</style><div class="grid-container">'

config = get_config()
if config is None:
    alert(
        "No configuration set, run the Preflight Checks clicking \
        on the tool while maintaining ALT key to configurate. Exiting...",
        exitscript=True,
    )

CURRENT_FOLDER = config.get_option("current_folder")
CRITICAL_WARNINGS = config.get_option("critical_warnings")
EXPORT_FILE_PATH = config.get_option("export_file_path")
if EXPORT_FILE_PATH is None:
    alert(
        "No export file path set, run the Preflight Checks clicking \
        on the tool while maintaining ALT key to configurate. Exiting...",
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


class Metadata:
    """Encapsulates user and date metadata."""

    def __init__(self):
        self.user = HOST_APP.username
        self.date = datetime.today().strftime("%d-%m-%Y")


class DocumentInfo:
    """Handles document-specific information."""

    def __init__(self, document):
        self.clean_name = get_document_clean_name(document) if document else ""
        self.revit_version_build = HOST_APP.build


class ProjectInfoData:
    """Encapsulates project metadata from Revit."""

    def __init__(self, document):
        revit_project_info = RevitProjectInfo(document) if document else None
        self.name = revit_project_info.name if revit_project_info else ""
        self.number = revit_project_info.number if revit_project_info else ""
        self.client = revit_project_info.client_name if revit_project_info else ""
        self.phases = get_phases_names(document) if document else []
        self.worksets_names = get_worksets_names(document) if document else []


class ElementCounts:
    """Manages element-related counts."""

    def __init__(self, document):
        self.element_count = count_elements(document) if document else 0
        self.purgeable_elements_count = (
            count_purgeable_elements(document) if document else 0
        )
        self.activated_analytical_model_elements_count = (
            count_analytical_model_activated(document) if document else 0
        )


class WarningsInfo:
    """Handles warning metrics."""

    def __init__(self, document):
        self.all_warnings_count = get_warnings_count(document) if document else 0
        self.critical_warnings_count = (
            get_critical_warnings_count(document, CRITICAL_WARNINGS) if document else 0
        )


class RoomInfo:
    """Manages room-related data."""

    def __init__(self, document):
        self.rooms_count = count_rooms(document) if document else 0
        self.unplaced_rooms_count = count_unplaced_rooms(document) if document else 0
        self.unbounded_rooms = count_unbounded_rooms(document) if document else 0


class SheetViewInfo:
    """Handles sheets and views metrics."""

    def __init__(self, document, sheets_set, views):
        self.sheets_count = len(sheets_set) if sheets_set else 0
        self.views_count = len(views) if views else 0
        self.views_not_on_sheets = (
            count_unplaced_views(sheets_set, self.views_count)
            if sheets_set and views
            else 0
        )
        self.schedule_count = count_total_schedules(document) if document else 0
        self.schedules_not_sheeted_count = (
            count_unplaced_schedules(document) if document else 0
        )
        self.copied_views_count = count_copied_views(views) if views else 0


class ViewTemplateFilterInfo:
    """Manages view templates and filters."""

    def __init__(self, document, views):
        self.view_templates_count = (
            len(get_all_view_templates(document)) if document else 0
        )
        self.unused_view_templates_count = (
            count_unused_view_templates(views) if views else 0
        )
        self.all_filters_count = count_filters(document) if document else 0
        self.unused_view_filters_count = (
            count_unused_filters_in_views(views) if views else 0
        )


class MaterialsLinePatternInfo:
    """Handles materials and line patterns."""

    def __init__(self, document):
        self.materials_count = (
            len(
                get_elements_by_categories(
                    [DB.BuiltInCategory.OST_Materials], doc=document
                )
            )
            if document
            else 0
        )
        self.line_patterns_count = (
            len(get_elements_by_class(DB.LinePatternElement, doc=document))
            if document
            else 0
        )


class LinksInfo:
    """Manages linked files data."""

    def __init__(self, document, rvtlinks_elements_items):
        self.rvtlinks_count = len(get_all_linkeddocs(document)) if document else 0
        self.dwgs_count = count_total_dwg_files(document) if document else 0
        self.linked_dwg_count = count_linked_dwg_files(document) if document else 0
        self.rvtlinks_unpinned_count = (
            count_unpinned_revit_links(rvtlinks_elements_items)
            if rvtlinks_elements_items
            else 0
        )


class FamilyInfo:
    """Handles family-related metrics."""

    def __init__(self, document):
        self.inplace_family_count = count_in_place_families(document) if document else 0
        self.not_parametric_families_count = (
            count_non_parametric_families(document) if document else 0
        )
        self.family_count = count_total_families(document) if document else 0
        self.imports_subcats_count = (
            count_import_subcategories(document) if document else 0
        )
        self.generic_models_types_count = len(get_families(document)) if document else 0
        self.detail_components_count = (
            count_detail_components(document) if document else 0
        )
        self.detail_lines_count = count_detail_lines(document) if document else 0


class TextNotesInfo:
    """Manages text note metrics."""

    def __init__(self, document):
        self.text_notes_types_count = (
            count_total_textnote_types(document) if document else 0
        )
        self.text_notes_types_wf_count = (
            count_textnote_types_with_changed_width_factor(document) if document else 0
        )
        self.text_bg_count = (
            count_textnote_types_with_opaque_background(document) if document else 0
        )
        self.text_notes_count = count_text_notes(document) if document else 0
        self.text_notes_caps_count = (
            count_text_notes_with_all_caps(document) if document else 0
        )


class GroupInfo:
    """Handles group-related data."""

    def __init__(self, document):
        self.detail_groups_count = (
            count_detail_group_instances(document) if document else 0
        )
        self.detail_groups_types_count = (
            count_detail_groups_types(document) if document else 0
        )
        self.model_group_count = count_model_group_instances(document) if document else 0
        self.model_group_type_count = (
            count_model_groups_types(document) if document else 0
        )


class ReferencePlaneInfo:
    """Manages reference plane metrics."""

    def __init__(self, document):
        self.reference_planes_count = (
            count_reference_planes(document) if document else 0
        )
        self.unnamed_ref_planes_count = (
            count_unnamed_reference_planes(document) if document else 0
        )


class DimensionsInfo:
    """Handles dimension-related data."""

    def __init__(self, document):
        self.dim_types_count = count_dimension_types(document) if document else 0
        self.dim_count = count_dimensions(document) if document else 0
        self.dim_overrides_count = (
            count_dimension_overrides(document) if document else 0
        )


class RevisionsInfo:
    """Manages revision clouds count."""

    def __init__(self, document):
        self.revision_clouds_count = count_revision_clouds(document) if document else 0


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
            ("views_not_on_sheets", "sheet_view_info.views_not_on_sheets"),
            ("schedules", "sheet_view_info.schedule_count"),
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
            ("detail_groups_count", "group_info.detail_groups_count"),
            ("detail_groups_types_count", "group_info.detail_groups_types_count"),
            ("model_group_count", "group_info.model_group_count"),
            ("model_group_type_count", "group_info.model_group_type_count"),
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

    def __init__(self, document=None):
        sheets_set = get_sheets(document) if document else None
        views = get_all_views(document) if document else None
        self.rvtlinks_elements_items = (
            get_linked_model_instances(document).ToElements() if document else None
        )

        # Initialize component classes
        self.metadata = Metadata()
        self.document_info = DocumentInfo(document)
        self.project_info = ProjectInfoData(document)
        self.element_counts = ElementCounts(document)
        self.warnings_info = WarningsInfo(document)
        self.room_info = RoomInfo(document)
        self.sheet_view_info = SheetViewInfo(document, sheets_set, views)
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
        If the CSV file does not exist, it creates a new file with the specified headers and writes the data.
        If the CSV file already exists, it checks if the data for the current date and document name already exists.
        If the data does not exist, it appends the new data to the file.

        Args:
            export_file_path (str): The path to the CSV file. Defaults to EXPORT_FILE_PATH.
            headers (list, optional): The list of headers for the CSV file. Defaults to None, in which case self.COLUMNS is used.

        Returns:
            None
        """
        if headers is None:
            headers = self.COLUMNS
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
        "Sheets, Views, Graphics",
        card_builder(500, data.sheet_view_info.sheets_count, " Sheets"),
        card_builder(1500, data.sheet_view_info.views_count, " Views"),
        card_builder(
            300, data.sheet_view_info.views_not_on_sheets, " Views not on Sheets"
        ),
        card_builder(20, data.sheet_view_info.schedule_count, " Schedules"),
        card_builder(
            5,
            data.sheet_view_info.schedules_not_sheeted_count,
            " Schedules not on sheet",
        ),
        card_builder(0, data.sheet_view_info.copied_views_count, " Copied Views"),
        card_builder(
            100, data.view_template_filter_info.view_templates_count, " View Templates"
        ),
        card_builder(
            0, data.view_template_filter_info.unused_view_templates_count, " Unused VT"
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
        card_builder(0, data.family_info.imports_subcats_count, " Imports in Families"),
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
            1, data.text_notes_info.text_bg_count, " Text Notes w/ White Background"
        ),
        card_builder(
            0,
            data.text_notes_info.text_notes_types_wf_count,
            " Text Notes Width Factor !=1",
        ),
        card_builder(2000, data.text_notes_info.text_notes_count, " Text Notes"),
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
        card_builder(10, data.group_info.model_group_count, " Model Group Instances"),
        card_builder(5, data.group_info.model_group_type_count, " Model Group Types"),
        card_builder(10, data.group_info.detail_groups_count, " Detail Group Instances"),
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
            alert("This tool is for project files only. Exiting...", exitscript=True)
        data = ReportData(doc)
        warnings_count = data.warnings_info.all_warnings_count
        if warnings_count > 0:
            try:
                show_balloon(
                    header="Warnings",
                    text="The file {} contains {} warnings".format(
                        data.document_info.clean_name, warnings_count
                    ),
                    is_favourite=True,
                    is_new=True,
                )
            except Exception as e:
                logger.error(
                    "Failed to show balloon notification, Exception: {}".format(e),
                    exc_info=True,
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
        if data.links_info.rvtlinks_count > 0:
            link_data = []
            rvtlinks_instances = get_linked_model_instances(doc).ToElements()
            rvtlinks_documents = (link.GetLinkDocument() for link in rvtlinks_instances)
            links_documents_data = [
                ReportData(link_doc) for link_doc in rvtlinks_documents
            ]
            for rvt_link_instance, link_document_data in zip(
                rvtlinks_instances, links_documents_data
            ):
                link_data.append(
                    [
                        link_document_data.project_info.name,
                        link_document_data.project_info.number,
                        link_document_data.project_info.client,
                        link_document_data.project_info.phases,
                        link_document_data.project_info.worksets_names,
                        link_document_data.document_info.clean_name,
                        get_rvt_link_instance_name(rvt_link_instance),
                        str(
                            doc.GetElement(
                                rvt_link_instance.GetTypeId()
                            ).GetLinkedFileStatus()
                        ).split(".")[-1],
                        get_revit_link_pinning_status(rvt_link_instance),
                    ]
                )
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
    - views count
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
