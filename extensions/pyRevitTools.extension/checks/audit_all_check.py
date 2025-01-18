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
    get_rvt_links_names,
    get_all_linkeddocs,
    get_linked_model_types,
    get_linked_model_instances,
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
        Initialize the Class with the user, date, document name, and Revit version build.
        """
        self.user = HOST_APP.username
        self.date = datetime.today().strftime("%d-%m-%Y")
        self.doc_clean_name = get_document_clean_name(document)
        self.revit_version_build = HOST_APP.build
        project_info = ProjectInfo(document)
        self.project_name=project_info.name
        self.project_number=project_info.number
        self.project_client=project_info.client_name
        self.project_phases=get_phases_names(document)
        self.worksets_names=get_worksets_names(document)
        sheets_set = get_sheets(document)
        views = get_all_views(document)
        self.doc_clean_name=get_document_clean_name(document)
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
        self.line_patterns_count = len(get_elements_by_class(DB.LinePatternElement, doc=document))
        self.dwgs_count = count_total_dwg_files(document)
        self.linked_dwg_count = count_linked_dwg_files(document)
        self.inplace_family_count = count_in_place_families(document)
        self.not_parametric_families_count = count_non_parametric_families(document)
        self.family_count = count_total_families(document)
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
        self.detail_lines_count = count_detail_lines(document)
        self.dim_types_count = count_dimension_types(document)
        self.dim_count = count_dimensions(document)
        self.dim_overrides_count = count_dimension_overrides(document)
        self.revision_clouds_count = count_revision_clouds(document)

    def __str__(self):
        return ','.join([str(getattr(self, col, '')) for col in self.COLUMNS])

    def __repr__(self):
        return self.__str__()

    def export_to_csv(self, export_file_path=EXPORT_FILE_PATH, headers=None):
        """
        Export data to a CSV file. If the file does not exist, it will be created. If the file exists, the data will be appended based on the date and document name.
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


def get_rvtlinks_elements_data(document):
    """
    Returns a list of all the Revit links elements in the document.

    Args:
        document (Document): A Revit document.

    Returns:
        list: Revit link elements, the number of Revit links, Revit link status, and Revit link documents.
    """
    rvtlinks_instances = get_linked_model_instances(document)
    rvtlinks_types_items = get_linked_model_types(document, rvtlinks_instances)
    revitlinks_elements = rvtlinks_instances.ToElements()
    rvtlinks_count = len(revitlinks_elements)
    linked_file_statuses = [
        rvtlinktype.GetLinkedFileStatus() for rvtlinktype in rvtlinks_types_items
    ]
    rvtlink_docs = get_all_linkeddocs(document)
    return revitlinks_elements, rvtlinks_count, linked_file_statuses, rvtlink_docs


def get_revit_link_pinning_status(revitlinks_elements):
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
        doc_clean_name = get_document_clean_name(doc)
        warnings_count= get_warnings_count(doc),
        if warnings_count > 0:
            try:
                show_balloon(
                    header="Warnings",
                    text="The file {} contains {} warnings".format(
                        doc_clean_name, warnings_count
                    ),
                    is_favourite=True,
                    is_new=True,
                )
            except Exception as e:
                print(e)
        
        current_doc_report = ReportData(doc)

        # output section
        output.close_others()
        output.set_height(900)
        output.set_width(1400)

        # RVT file dashboard section
        body_css = '<style>.grid-container { display: grid; justify-content: center; align-items: center; }</style><div class="grid-container">'

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
            columns=[
                "Project Name",
                "Project Number",
                "Client Name",
                "Project Phases",
                "Worksets",
                "Linked File Name",
                "Instance Name",
                "Loaded Status",
                "Pinned status",
            ],
        )

        # Linked files infos
        links_cards = ""
        # Links
        (
            rvtlinks_elements_items,
            rvtlinks_count,
            rvtlinks_type_load_status,
            rvtlinks_documents,
        ) = get_rvtlinks_elements_data(doc)
        links_names, links_instances_names = get_rvt_links_names(
            rvtlinks_elements_items
        )
        if rvtlinks_elements_items:
            link_data = []
            pinned = get_revit_link_pinning_status(rvtlinks_elements_items)
            for idx, link_doc in enumerate(rvtlinks_documents):
                link_document_data = ReportData(link_doc)
                link_data.append(
                    [
                        link_document_data.project_name,
                        link_document_data.project_number,
                        link_document_data.project_client,
                        link_document_data.project_phases,
                        link_document_data.worksets_names,
                        links_names[idx],
                        links_instances_names[idx],
                        rvtlinks_type_load_status[idx],
                        pinned[idx],
                    ]
                )
            columns_headers = [
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
            output.print_md("# Linked Files Infos")
            output.print_table(link_data, columns=columns_headers)
            rvtlinks_unpinned = count_unpinned_revit_links(rvtlinks_elements_items)
            links_cards = card_builder(50, rvtlinks_count, " Links") + card_builder(
                0, rvtlinks_unpinned, " Links not pinned"
            )

        output.print_md("# <p style='text-align: center;'>" + doc_clean_name + "</p>")

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
            body_css
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
        if rvtlinks_elements_items:
            generate_rvt_links_report(output, rvtlinks_documents, body_css)
        output.self_destruct(180)
    except Exception as e:
        print(format_exc())
        print(e)


def generate_rvt_links_report(output, rvtlinks_docs, body_css):
    output.print_md("# RVTLinks")
    for rvtlink in rvtlinks_docs:
        doc_clean_name = get_document_clean_name(rvtlink)
        output.print_md("## " + doc_clean_name)
        output.print_md("___")
        if rvtlink is None:
            continue
        link_document_data = ReportData(rvtlink)
        output.print_md(link_document_data.doc_clean_name)
        links_data = ""
        if rvtlinks_elements_items:
            links_data = card_builder(50, rvtlinks_count, " Links") + card_builder(
                0, rvtlinks_unpinned, " Links not pinned"
            )
        critical_elements_frame = create_frame(
            "Critical Elements",
            card_builder(100000, element_count, " Elements"),
            card_builder(1000, purgeable_elements_count, " Purgeable (2024+)"),
            card_builder(100, all_warnings_count, " Warnings"),
            card_builder(5, critical_warnings_count, " Critical Warnings"),
            card_builder(
                0, activated_analytical_model_elements_count, " Analytical Model ON"
            ),
            links_data,
        )
        rooms_frame = create_frame(
            "Rooms",
            card_builder(1000, rooms_count, " Rooms"),
            card_builder(0, unplaced_rooms_count, " Unplaced Rooms"),
            card_builder(0, unbounded_rooms, " Unbounded Rooms"),
        )
        sheets_views_graphics_frame = create_frame(
            "Sheets, Views, Graphics",
            card_builder(500, sheets_count, " Sheets"),
            card_builder(1500, views_count, " Views"),
            card_builder(300, views_not_on_sheets, " Views not on Sheets"),
            card_builder(20, schedule_count, " Schedules"),
            card_builder(5, schedules_not_sheeted_count, " Schedules not on sheet"),
            card_builder(0, copied_views_count, " Copied Views"),
            card_builder(100, view_templates_count, " View Templates"),
            card_builder(0, unused_view_templates_count, " Unused VT"),
            card_builder(0, all_filters_count, " Filters"),
            card_builder(0, unused_view_filters_count, " Unused Filters"),
        )
        cad_files_frame = create_frame(
            "CAD Files",
            card_builder(5, dwgs_count, " DWGs"),
            card_builder(5, linked_dwg_count, " Linked DWGs"),
        )
        families_frame = create_frame(
            "Families",
            card_builder(500, family_count, " Families"),
            card_builder(0, inplace_family_count, " In-Place Families"),
            card_builder(
                100, not_parametric_families_count, " Non-Parametric Families"
            ),
            card_builder(0, imports_subcats_count, " Imports in Families"),
            card_builder(50, generic_models_types_count, " Generic Models Types"),
            card_builder(100, detail_components_count, " Detail Components"),
        )
        graphical2d_elements_frame = create_frame(
            "Graphical 2D Elements",
            card_builder(5000, detail_lines_count, " Detail Lines"),
            card_builder(30, line_patterns_count, " Line Patterns"),
            card_builder(30, text_notes_types_count, " Text Notes Types"),
            card_builder(1, text_bg_count, " Text Notes w/ White Background"),
            card_builder(0, text_notes_types_wf_count, " Text Notes Width Factor !=1"),
            card_builder(2000, text_notes_count, " Text Notes"),
            card_builder(100, text_notes_caps_count, " Text Notes allCaps"),
            card_builder(5, dim_types_count, " Dimension Types"),
            card_builder(5000, dim_count, " Dimensions"),
            card_builder(0, dim_overrides_count, " Dimension Overrides"),
            card_builder(100, revision_clouds_count, " Revision Clouds"),
        )
        groups_summary_frame = create_frame(
            "Groups",
            card_builder(10, model_group_count, " Model Groups"),
            card_builder(5, model_group_type_count, " Model Group Types"),
            card_builder(10, detail_groups_count, " Detail Groups"),
            card_builder(20, detail_groups_types_count, " Detail Group Types"),
        )
        reference_planes_frame = create_frame(
            "Reference Planes",
            card_builder(100, reference_planes_count, " Ref Planes"),
            card_builder(10, unnamed_ref_planes_count, " Ref Planes no_name"),
        )
        html_content = (
            body_css
            + critical_elements_frame
            + rooms_frame
            + sheets_views_graphics_frame
            + cad_files_frame
            + families_frame
            + graphical2d_elements_frame
            + groups_summary_frame
            + reference_planes_frame
            + create_frame(
                "Materials", card_builder(100, materials_count, " Materials")
            )
        )
        output.print_html(html_content + "</div>")

        # csv export
        data = [
            user,
            date,
            doc_clean_name,
            revit_version_build,
            project_name,
            project_number,
            project_client,
            project_phases,
            worksets_names,
            element_count,
            purgeable_elements_count,
            all_warnings_count,
            critical_warnings_count,
            rvtlinks_count,
            activated_analytical_model_elements_count,
            rooms_count,
            unplaced_rooms_count,
            unbounded_rooms,
            sheets_count,
            views_count,
            views_not_on_sheets,
            schedule_count,
            schedules_not_sheeted_count,
            copied_views_count,
            view_templates_count,
            unused_view_templates_count,
            all_filters_count,
            unused_view_filters_count,
            materials_count,
            line_patterns_count,
            dwgs_count,
            linked_dwg_count,
            inplace_family_count,
            not_parametric_families_count,
            family_count,
            imports_subcats_count,
            generic_models_types_count,
            detail_components_count,
            text_notes_types_count,
            text_bg_count,
            text_notes_types_wf_count,
            text_notes_count,
            text_notes_caps_count,
            detail_groups_count,
            detail_groups_types_count,
            model_group_count,
            model_group_type_count,
            reference_planes_count,
            unnamed_ref_planes_count,
            detail_lines_count,
            dim_types_count,
            dim_count,
            dim_overrides_count,
            revision_clouds_count,
        ]
        data_str = list(map(str, data))

        export_to_csv(doc_clean_name, data, data_str, output)


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
