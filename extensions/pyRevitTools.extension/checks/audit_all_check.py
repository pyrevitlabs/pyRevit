# -*- coding: UTF-8 -*-

__cleanengine__ = True
__fullframeengine__ = True
__persistentengine__ = True

from traceback import format_exc
from csv import writer, reader
from os.path import isfile
from datetime import datetime, timedelta
from pyrevit.coreutils import Timer
from pyrevit import HOST_APP, DOCS
from pyrevit import DB
from pyrevit.script import get_config
from pyrevit.forms import alert, show_balloon
from pyrevit.output.cards import card_builder, create_frame
from pyrevit.revit.db import ProjectInfo
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
    get_rvt_link_status,
    get_rvt_link_instance_name,
    get_rvt_link_doc_name,
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
class ReportData:
    COLUMNS = [
        "user",
        "date",
        "doc_clean_name",
        "revit_version_build",
        "project_name",
        "project_number",
        "project_client",
        "project_phases",
        "worksets_names",
        "element_count",
        "purgeable_elements_count",
        "all_warnings_count",
        "critical_warnings_count",
        "rvtlinks_count",
        "activated_analytical_model_elements_count",
        "rooms_count",
        "unplaced_rooms_count",
        "unbounded_rooms",
        "sheets_count",
        "views_count",
        "views_not_on_sheets",
        "schedules",
        "schedules_not_sheeted_count",
        "copied_views_count",
        "view_templates_count",
        "unused_view_templates_count",
        "all_filters_count",
        "unused_view_filters_count",
        "materials_count",
        "line_patterns_count",
        "dwgs_count",
        "linked_dwg_count",
        "inplace_family_count",
        "not_parametric_families_count",
        "family_count",
        "imports_subcats_count",
        "generic_models_types_count",
        "detail_components_count",
        "text_notes_types_count",
        "text_bg_count",
        "text_notes_types_wf_count",
        "text_notes_count",
        "text_notes_caps_count",
        "detail_groups_count",
        "detail_groups_types_count",
        "model_group_count",
        "model_group_type_count",
        "reference_planes_count",
        "unnamed_ref_planes_count",
        "detail_lines_count",
        "dim_types_count",
        "dim_count",
        "dim_overrides_count",
        "revision_clouds_count",
    ]

    def __init__(self, document=None):
        """
        Initializes the audit check with various document metrics and project information.
        
        Args:
            document (Document, optional): The Revit document to audit. Defaults to None.
        
        Attributes:
            user (str): The username of the host application.
            date (str): The current date in "dd-mm-yyyy" format.
            doc_clean_name (str): The cleaned name of the document.
            revit_version_build (str): The build version of the Revit application.
            project_name (str): The name of the project.
            project_number (str): The project number.
            project_client (str): The client name of the project.
            project_phases (list): The phases of the project.
            worksets_names (list): The names of the worksets in the document.
            element_count (int): The total number of elements in the document.
            purgeable_elements_count (int): The number of purgeable elements in the document.
            all_warnings_count (int): The total number of warnings in the document.
            critical_warnings_count (int): The number of critical warnings in the document.
            activated_analytical_model_elements_count (int): The number of activated analytical model elements.
            rooms_count (int): The total number of rooms in the document.
            unplaced_rooms_count (int): The number of unplaced rooms in the document.
            unbounded_rooms (int): The number of unbounded rooms in the document.
            sheets_count (int): The total number of sheets in the document.
            views_count (int): The total number of views in the document.
            views_not_on_sheets (int): The number of views not placed on sheets.
            schedule_count (int): The total number of schedules in the document.
            schedules_not_sheeted_count (int): The number of schedules not placed on sheets.
            copied_views_count (int): The number of copied views in the document.
            view_templates_count (int): The total number of view templates in the document.
            unused_view_templates_count (int): The number of unused view templates.
            all_filters_count (int): The total number of filters in the document.
            unused_view_filters_count (int): The number of unused view filters.
            materials_count (int): The total number of materials in the document.
            line_patterns_count (int): The total number of line patterns in the document.
            dwgs_count (int): The total number of DWG files in the document.
            linked_dwg_count (int): The number of linked DWG files in the document.
            inplace_family_count (int): The number of in-place families in the document.
            not_parametric_families_count (int): The number of non-parametric families in the document.
            family_count (int): The total number of families in the document.
            imports_subcats_count (int): The number of import subcategories in the document.
            generic_models_types_count (int): The total number of generic model types in the document.
            detail_components_count (int): The total number of detail components in the document.
            text_notes_types_count (int): The total number of text note types in the document.
            text_notes_types_wf_count (int): The number of text note types with changed width factor.
            text_bg_count (int): The number of text note types with opaque background.
            text_notes_count (int): The total number of text notes in the document.
            text_notes_caps_count (int): The number of text notes with all caps.
            detail_groups_count (int): The total number of detail group types in the document.
            detail_groups_types_count (int): The number of detail group instances in the document.
            model_group_count (int): The total number of model group types in the document.
            model_group_type_count (int): The number of model group instances in the document.
            reference_planes_count (int): The total number of reference planes in the document.
            unnamed_ref_planes_count (int): The number of unnamed reference planes in the document.
            detail_lines_count (int): The total number of detail lines in the document.
            dim_types_count (int): The total number of dimension types in the document.
            dim_count (int): The total number of dimensions in the document.
            dim_overrides_count (int): The number of dimension overrides in the document.
            revision_clouds_count (int): The total number of revision clouds in the document.
        """

        sheets_set = get_sheets(document)
        views = get_all_views(document)
        project_info = ProjectInfo(document)

        self.user = HOST_APP.username
        self.date = datetime.today().strftime("%d-%m-%Y")
        self.doc_clean_name = get_document_clean_name(document)
        self.revit_version_build = HOST_APP.build
        self.project_name=project_info.name
        self.project_number=project_info.number
        self.project_client=project_info.client_name
        self.project_phases=get_phases_names(document)
        self.worksets_names=get_worksets_names(document)

        self.element_count=count_elements(document)
        self.purgeable_elements_count=count_purgeable_elements(document)
        self.all_warnings_count = get_warnings_count(document)
        self.critical_warnings_count=get_critical_warnings_count(
                document, CRITICAL_WARNINGS
            )
        self.activated_analytical_model_elements_count=count_analytical_model_activated(
                document
            )
        
        self.rooms_count = count_rooms(document)
        self.unplaced_rooms_count = count_unplaced_rooms(document)
        self.unbounded_rooms = count_unbounded_rooms(document)
        
        self.sheets_count = len(sheets_set)
        self.views_count = len(views)
        self.views_not_on_sheets = count_unplaced_views(sheets_set, self.views_count)
        self.schedule_count = count_total_schedules(document)
        self.schedules_not_sheeted_count = count_unplaced_schedules(document)
        self.copied_views_count = count_copied_views(views)
        self.view_templates_count = len(get_all_view_templates(document))
        self.unused_view_templates_count = count_unused_view_templates(views)
        self.all_filters_count = count_filters(document)
        self.unused_view_filters_count = count_unused_filters_in_views(views)
        
        self.materials_count = len(get_elements_by_categories([DB.BuiltInCategory.OST_Materials], doc=document))
        
        self.inplace_family_count = count_in_place_families(document)
        self.not_parametric_families_count = count_non_parametric_families(document)
        self.family_count = count_total_families(document)

        self.line_patterns_count = len(get_elements_by_class(DB.LinePatternElement, doc=document))
        self.detail_lines_count = count_detail_lines(document)
        self.imports_subcats_count = count_import_subcategories(document)
        self.generic_models_types_count = len(get_families(document))
        self.detail_components_count = count_detail_components(document)

        self.text_notes_types_count = count_total_textnote_types(document)
        self.text_notes_types_wf_count = count_textnote_types_with_changed_width_factor(document)
        self.text_bg_count = count_textnote_types_with_opaque_background(document)
        self.text_notes_count = count_text_notes(document)
        self.text_notes_caps_count = count_text_notes_with_all_caps(document)

        self.detail_groups_count = count_detail_groups_types(document)
        self.detail_groups_types_count = count_detail_group_instances(document)
        self.model_group_count = count_model_groups_types(document)
        self.model_group_type_count = count_model_group_instances(document)

        self.reference_planes_count = count_reference_planes(document)
        self.unnamed_ref_planes_count = count_unnamed_reference_planes(document)

        self.dim_types_count = count_dimension_types(document)
        self.dim_count = count_dimensions(document)
        self.dim_overrides_count = count_dimension_overrides(document)

        self.revision_clouds_count = count_revision_clouds(document)

        self.dwgs_count = count_total_dwg_files(document)
        self.linked_dwg_count = count_linked_dwg_files(document)

        self.rvtlinks_count = len(get_all_linkeddocs(document))
        self.rvtlinks_elements_items = get_linked_model_instances(document).ToElements()
        self.rvtlinks_unpinned_count = count_unpinned_revit_links(self.rvtlinks_elements_items)
        self.rvtlink_pinned_status = self.get_revit_link_pinning_status(document)


    def __str__(self):
        return ','.join([str(getattr(self, col, '')) for col in self.COLUMNS])

    def __repr__(self):
        return self.__str__()

    def get_revit_link_pinning_status(self, document=None):
        """
        Determines the pinning status of a Revit link.
        
        Args:
            document (object, optional): The Revit document to check. Defaults to None.
        
        Returns:
            str: "Pinned" if the document is pinned, "Unpinned" if the document is not pinned,
                 and "-" if the document does not have a 'Pinned' attribute.
        """
        return "-" if not hasattr(document, "Pinned") else "Unpinned" if not document.Pinned else "Pinned"
    
    def export_to_csv(self, export_file_path=EXPORT_FILE_PATH, headers=None):
        """
        Export data to a CSV file. If the file does not exist, 
        it will be created. If the file exists, 
        the data will be appended based on the date and document name.
        """
        if headers is None:
            headers = self.COLUMNS
        if not isfile(export_file_path):
            with open(export_file_path, mode="wb") as csv_file:
                w = writer(csv_file, lineterminator="\n")
                w.writerow(headers)
                w.writerow(self.__str__())
        else:
            with open(export_file_path, mode="rb") as csv_file:
                r = reader(csv_file, delimiter=",")
                flag = any(
                    row[1] == self.date and row[2] == self.doc_clean_name for row in r
                )
            if not flag:
                with open(export_file_path, mode="ab") as csv_file:
                    w = writer(csv_file, lineterminator="\n")
                    w.writerow(self.__str__())


def get_rvtlink_docs(document):
    """
    Returns a list of all the Revit link documents in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: Revit link documents.
    """
    return get_all_linkeddocs(document)


def audit_document(doc, output):
    """
    Perform a comprehensive audit of a Revit project file and generate a detailed report.
    Parameters:
    doc (Document): The Revit document to be audited.
    output (Output): The output object to print and display the audit results.
    The function performs the following tasks:
    - Checks if the document is a project file.
    - Gathers project information such as name, number, client, phases, and worksets.
    - Counts various elements in the document including rooms, sheets, views, schedules, families, and more.
    - Identifies and counts warnings, critical warnings, and purgeable elements.
    - Generates a detailed HTML report with various sections including critical elements, rooms, sheets, views, CAD files, families, graphical 2D elements, groups, reference planes, and materials.
    - Exports the audit data to a CSV file.
    - Generates a report for linked Revit files if any are present.
    - Displays a balloon notification if there are warnings in the document.
    - Sets the output window dimensions and closes other output windows.
    Raises:
    Exception: If any error occurs during the audit process, it prints the stack trace and error message.
    """
    try:
        if doc.IsFamilyDocument:
            alert("This tool is for project files only. Exiting...", exitscript=True)
        
        current_doc_report = ReportData(doc)

        warnings_count= current_doc_report.all_warnings_count
        if warnings_count > 0:
            try:
                show_balloon(
                    header="Warnings",
                    text="The file {} contains {} warnings".format(
                        current_doc_report.doc_clean_name, warnings_count
                    ),
                    is_favourite=True,
                    is_new=True,
                )
            except Exception as e:
                print(e)

        # output section
        output.close_others()
        output.set_height(900)
        output.set_width(1400)

        # RVT file dashboard section

        # Main file infos
        project_info = [
            current_doc_report.project_name,
            current_doc_report.project_number,
            current_doc_report.project_client,
            current_doc_report.project_phases,
            current_doc_report.worksets_names,
            "N/A",
            "N/A",
            "N/A",
            "N/A",
        ]
        output.print_md("# Main File Infos")
        output.print_table(
            [project_info],
            columns=FILE_INFO_HEADERS,
        )

        # Linked files infos
        links_cards = ""
        if current_doc_report.rvtlinks_elements_items:
            link_data = []
            rvtlinks_instances = get_linked_model_instances(doc).ToElements()
            rvtlinks_documents = (link.GetLinkDocument() for link in rvtlinks_instances)
            links_documents_data = [ReportData(link_doc) for link_doc in rvtlinks_documents]
            for rvt_link_instance, link_document_data in zip(rvtlinks_instances, links_documents_data):
                link_data.append(
                    [
                        link_document_data.project_name,
                        link_document_data.project_number,
                        link_document_data.project_client,
                        link_document_data.project_phases,
                        link_document_data.worksets_names,
                        link_document_data.doc_clean_name,
                        get_rvt_link_instance_name(rvt_link_instance),                       
                        get_rvt_link_status(rvt_link_instance.GetLinkDocument()),
                        link_document_data.rvtlink_pinned_status,
                    ]
                )
            output.print_md("# Linked Files Infos")
            output.print_table(link_data, columns=FILE_INFO_HEADERS)
            links_cards = card_builder(50, current_doc_report.rvtlinks_count, " Links") + card_builder(
                0, current_doc_report.rvtlinks_unpinned_count, " Links not pinned"
            )

        output.print_md("# <p style='text-align: center;'>" + current_doc_report.doc_clean_name + "</p>")

        critical_elements_frame = create_frame(
            "Critical Elements",
            card_builder(100000, current_doc_report.element_count, " Elements"),
            card_builder(1000, current_doc_report.purgeable_elements_count, " Purgeable (2024+)"),
            card_builder(100, current_doc_report.all_warnings_count, " Warnings"),
            card_builder(5, current_doc_report.critical_warnings_count, " Critical Warnings"),
            card_builder(
                0, current_doc_report.activated_analytical_model_elements_count, " Analytical Model ON"
            ),
            links_cards,
        )

        rooms_frame = create_frame(
            "Rooms",
            card_builder(1000, current_doc_report.rooms_count, " Rooms"),
            card_builder(0, current_doc_report.unplaced_rooms_count, " Unplaced Rooms"),
            card_builder(0, current_doc_report.unbounded_rooms, " Unbounded Rooms"),
        )

        sheets_views_graphics_frame = create_frame(
            "Sheets, Views, Graphics",
            card_builder(500, current_doc_report.sheets_count, " Sheets"),
            card_builder(1500, current_doc_report.views_count, " Views"),
            card_builder(300, current_doc_report.views_not_on_sheets, " Views not on Sheets"),
            card_builder(20, current_doc_report.schedule_count, " Schedules"),
            card_builder(5, current_doc_report.schedules_not_sheeted_count, " Schedules not on sheet"),
            card_builder(0, current_doc_report.copied_views_count, " Copied Views"),
            card_builder(100, current_doc_report.view_templates_count, " View Templates"),
            card_builder(0, current_doc_report.unused_view_templates_count, " Unused VT"),
            card_builder(0, current_doc_report.all_filters_count, " Filters"),
            card_builder(0, current_doc_report.unused_view_filters_count, " Unused Filters"),
        )

        cad_files_frame = create_frame(
            "CAD Files",
            card_builder(5, current_doc_report.dwgs_count, " DWGs"),
            card_builder(5, current_doc_report.linked_dwg_count, " Linked DWGs"),
        )

        families_frame = create_frame(
            "Families",
            card_builder(500, current_doc_report.family_count, " Families"),
            card_builder(0, current_doc_report.inplace_family_count, " In-Place Families"),
            card_builder(
                100, current_doc_report.not_parametric_families_count, " Non-Parametric Families"
            ),
            card_builder(0, current_doc_report.imports_subcats_count, " Imports in Families"),
            card_builder(50, current_doc_report.generic_models_types_count, " Generic Models Types"),
            card_builder(100, current_doc_report.detail_components_count, " Detail Components"),
        )

        graphical2d_elements_frame = create_frame(
            "Graphical 2D Elements",
            card_builder(5000, current_doc_report.detail_lines_count, " Detail Lines"),
            card_builder(30, current_doc_report.line_patterns_count, " Line Patterns"),
            card_builder(30, current_doc_report.text_notes_types_count, " Text Notes Types"),
            card_builder(1, current_doc_report.text_bg_count, " Text Notes w/ White Background"),
            card_builder(0, current_doc_report.text_notes_types_wf_count, " Text Notes Width Factor !=1"),
            card_builder(2000, current_doc_report.text_notes_count, " Text Notes"),
            card_builder(100, current_doc_report.text_notes_caps_count, " Text Notes allCaps"),
            card_builder(5, current_doc_report.dim_types_count, " Dimension Types"),
            card_builder(5000, current_doc_report.dim_count, " Dimensions"),
            card_builder(0, current_doc_report.dim_overrides_count, " Dimension Overrides"),
            card_builder(100, current_doc_report.revision_clouds_count, " Revision Clouds"),
        )

        groups_summary_frame = create_frame(
            "Groups",
            card_builder(10, current_doc_report.model_group_count, " Model Groups"),
            card_builder(5, current_doc_report.model_group_type_count, " Model Group Types"),
            card_builder(10, current_doc_report.detail_groups_count, " Detail Groups"),
            card_builder(20, current_doc_report.detail_groups_types_count, " Detail Group Types"),
        )

        reference_planes_frame = create_frame(
            "Reference Planes",
            card_builder(100, current_doc_report.reference_planes_count, " Ref Planes"),
            card_builder(10, current_doc_report.unnamed_ref_planes_count, " Ref Planes no_name"),
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
            + create_frame(
                "Materials", card_builder(100, current_doc_report.materials_count, " Materials")
            )
        )

        output.print_html(html_content + "</div>")

        # csv export
        current_doc_report.export_to_csv()

        # RVTLinks
        if current_doc_report.rvtlinks_elements_items:
            output.print_md("# RVTLinks")
            for idx, link_doc_data in enumerate(links_documents_data):
                generate_rvt_links_report(link_doc_data, output)
    except Exception as e:
        print(format_exc())
        print(e)


def generate_rvt_links_report(link_document_data, output):
    """
    Generates a detailed report of Revit link document data and outputs it in markdown and HTML format.
    
    Args:
        link_document_data (LinkDocumentData): An object containing various metrics and data about the Revit link document.
        output (Output): An object responsible for printing markdown and HTML content.
    
    The function creates multiple frames of information, each containing specific metrics about the Revit link document,
    such as critical elements, rooms, sheets, views, CAD files, families, graphical 2D elements, groups, and reference planes.
    
    It then combines these frames into a single HTML content string and prints it using the output object.
    Additionally, it exports the link document data to a CSV file.
    """
    doc_clean_name = link_document_data.doc_clean_name
    output.print_md("## " + doc_clean_name)
    output.print_md("___")
    output.print_md(link_document_data.doc_clean_name)
    links_data = ""
    if link_document_data.rvtlinks_elements_items:
        links_data = card_builder(50, link_document_data.rvtlinks_count, " Links") + card_builder(
            0, link_document_data.rvtlinks_unpinned_count, " Links not pinned"
        )
    critical_elements_frame = create_frame(
        "Critical Elements",
        card_builder(100000, link_document_data.element_count, " Elements"),
        card_builder(1000, link_document_data.purgeable_elements_count, " Purgeable (2024+)"),
        card_builder(100, link_document_data.all_warnings_count, " Warnings"),
        card_builder(5, link_document_data.critical_warnings_count, " Critical Warnings"),
        card_builder(
            0, link_document_data.activated_analytical_model_elements_count, " Analytical Model ON"
        ),
        links_data,
    )
    rooms_frame = create_frame(
        "Rooms",
        card_builder(1000, link_document_data.rooms_count, " Rooms"),
        card_builder(0, link_document_data.unplaced_rooms_count, " Unplaced Rooms"),
        card_builder(0, link_document_data.unbounded_rooms, " Unbounded Rooms"),
    )
    sheets_views_graphics_frame = create_frame(
        "Sheets, Views, Graphics",
        card_builder(500, link_document_data.sheets_count, " Sheets"),
        card_builder(1500, link_document_data.views_count, " Views"),
        card_builder(300, link_document_data.views_not_on_sheets, " Views not on Sheets"),
        card_builder(20, link_document_data.schedule_count, " Schedules"),
        card_builder(5, link_document_data.schedules_not_sheeted_count, " Schedules not on sheet"),
        card_builder(0, link_document_data.copied_views_count, " Copied Views"),
        card_builder(100, link_document_data.view_templates_count, " View Templates"),
        card_builder(0, link_document_data.unused_view_templates_count, " Unused VT"),
        card_builder(0, link_document_data.all_filters_count, " Filters"),
        card_builder(0, link_document_data.unused_view_filters_count, " Unused Filters"),
    )
    cad_files_frame = create_frame(
        "CAD Files",
        card_builder(5, link_document_data.dwgs_count, " DWGs"),
        card_builder(5, link_document_data.linked_dwg_count, " Linked DWGs"),
    )
    families_frame = create_frame(
        "Families",
        card_builder(500, link_document_data.family_count, " Families"),
        card_builder(0, link_document_data.inplace_family_count, " In-Place Families"),
        card_builder(
            100, link_document_data.not_parametric_families_count, " Non-Parametric Families"
        ),
        card_builder(0, link_document_data.imports_subcats_count, " Imports in Families"),
        card_builder(50, link_document_data.generic_models_types_count, " Generic Models Types"),
        card_builder(100, link_document_data.detail_components_count, " Detail Components"),
    )
    graphical2d_elements_frame = create_frame(
        "Graphical 2D Elements",
        card_builder(5000, link_document_data.detail_lines_count, " Detail Lines"),
        card_builder(30, link_document_data.line_patterns_count, " Line Patterns"),
        card_builder(30, link_document_data.text_notes_types_count, " Text Notes Types"),
        card_builder(1, link_document_data.text_bg_count, " Text Notes w/ White Background"),
        card_builder(0, link_document_data.text_notes_types_wf_count, " Text Notes Width Factor !=1"),
        card_builder(2000, link_document_data.text_notes_count, " Text Notes"),
        card_builder(100, link_document_data.text_notes_caps_count, " Text Notes allCaps"),
        card_builder(5, link_document_data.dim_types_count, " Dimension Types"),
        card_builder(5000, link_document_data.dim_count, " Dimensions"),
        card_builder(0, link_document_data.dim_overrides_count, " Dimension Overrides"),
        card_builder(100, link_document_data.revision_clouds_count, " Revision Clouds"),
    )
    groups_summary_frame = create_frame(
        "Groups",
        card_builder(10, link_document_data.model_group_count, " Model Groups"),
        card_builder(5, link_document_data.model_group_type_count, " Model Group Types"),
        card_builder(10, link_document_data.detail_groups_count, " Detail Groups"),
        card_builder(20, link_document_data.detail_groups_types_count, " Detail Group Types"),
    )
    reference_planes_frame = create_frame(
        "Reference Planes",
        card_builder(100, link_document_data.reference_planes_count, " Ref Planes"),
        card_builder(10, link_document_data.unnamed_ref_planes_count, " Ref Planes no_name"),
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
        + create_frame(
            "Materials", card_builder(100, link_document_data.materials_count, " Materials")
        )
    )
    output.print_html(html_content + "</div>")
    # csv export
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
        endtime_hms_claim = (
            " \n\nCheck duration " + endtime_hms[0:7]
        )  # Remove seconds decimals from string
        output.print_md(endtime_hms_claim)
