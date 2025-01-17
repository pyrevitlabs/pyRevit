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
    get_warnings_info,
    get_critical_warnings_number,
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
    count_unplaced_views,
    count_analytical_model_activated,
    count_schedules,
    count_copied_views,
    count_unused_view_templates,
    count_filters,
    count_dwg_files,
    count_families_by_type,
    count_import_subcategories,
    count_detail_components,
    count_textnote_types,
    count_text_notes,
    count_detail_groups,
    count_model_groups,
    count_reference_planes,
    count_elements,
    count_detail_lines,
    count_dimensions,
    count_dimension_types,
    count_dimension_overrides,
    count_revision_clouds,
    count_purgeable_elements,
)


user = HOST_APP.username
date = datetime.today().strftime("%d-%m-%Y")
revit_version_build = HOST_APP.build
DATASET_PREFIX = ", ".join([user, date, revit_version_build])

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


def export_to_csv(doc_clean_name, data, data_str, output):
    """
    Exports data to a CSV file.
    If the CSV file does not exist, it creates a new file and writes the header and the initial data.
    If the CSV file exists, it checks if the data for the given date and document name already exists.
    If the data does not exist, it appends the new data to the file.
    Args:
        doc_clean_name (str): The cleaned name of the document.
        data (list): The data to be written to the CSV file.
        data_str (list): The string representation of the data to be written as the header.
        output (object): An object with a self_destruct method to be called after writing to the file.
    Returns:
        None
    """

    if not isfile(EXPORT_FILE_PATH):
        with open(EXPORT_FILE_PATH, mode="wb") as csv_file:
            w = writer(csv_file, lineterminator="\n")
            w.writerow(COLUMNS)
            w.writerow(data_str)
    with open(EXPORT_FILE_PATH, mode="rb") as csv_file:
        r = reader(csv_file, delimiter=",")
        flag = any(row[1] == date and row[2] == doc_clean_name for row in r)
    if not flag:
        with open(EXPORT_FILE_PATH, mode="ab") as csv_file:
            w = writer(csv_file, lineterminator="\n")
            w.writerow(data)
    output.self_destruct(30)


def check_model(doc, output):
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
        project_info = ProjectInfo(doc)
        project_name, project_number, project_client = (
            project_info.name,
            project_info.number,
            project_info.client_name,
        )
        project_phases = get_phases_names(doc)
        worksets_names = get_worksets_names(doc)
        doc_clean_name = get_document_clean_name(doc)
        element_count = count_elements(doc)
        purgeable_elements_count = count_purgeable_elements(doc)
        all_warnings_count, _, warnings_guid = get_warnings_info(doc)
        critical_warnings_count = get_critical_warnings_number(warnings_guid, CRITICAL_WARNINGS)
        if all_warnings_count > 0:
            try:
                show_balloon(
                    header="Warnings",
                    text="The file {} contains {} warnings".format(
                        doc_clean_name, all_warnings_count
                    ),
                    is_favourite=True,
                    is_new=True,
                )
            except Exception as e:
                print(e)
        activated_analytical_model_elements_count = count_analytical_model_activated(
            doc
        )
        doc_cached_issues = DOCS.doc
        rooms_count, unplaced_rooms_count, unbounded_rooms = count_rooms(doc_cached_issues)
        sheets_set = get_sheets(doc_cached_issues)
        sheets_count = len(sheets_set)
        views = get_all_views(doc_cached_issues)
        views_count = len(views)
        views_not_on_sheets = count_unplaced_views(sheets_set, views_count)
        schedule_count, schedules_not_sheeted_count = count_schedules(doc_cached_issues)
        copied_views_count = count_copied_views(views)
        view_templates_count = len(get_all_view_templates(doc))
        unused_view_templates_count = count_unused_view_templates(views)
        all_filters_count, unused_view_filters_count = count_filters(doc, views)
        materials_count = len(get_elements_by_categories(element_bicats=[DB.BuiltInCategory.OST_Materials],doc=doc))
        line_patterns_count = len(get_elements_by_class(DB.LinePatternElement, doc=doc))
        dwgs_count, linked_dwg_count = count_dwg_files(doc)
        inplace_family_count, not_parametric_families_count, family_count = count_families_by_type(
            doc
        )
        imports_subcats_count = count_import_subcategories(doc)
        generic_models_types_count = len(get_families(doc))
        detail_components_count = count_detail_components(doc)
        text_notes_types_count, text_notes_types_wf_count, text_bg_count = (
            count_textnote_types(doc)
        )
        text_notes_count, text_notes_caps_count = count_text_notes(doc)
        detail_groups_count, detail_groups_types_count = count_detail_groups(doc)
        model_group_count, model_group_type_count = count_model_groups(doc)
        reference_planes_count, unnamed_ref_planes_count = count_reference_planes(doc)
        detail_lines_count = count_detail_lines(doc)
        dim_types_count, dim_count, dim_overrides_count = (
            count_dimension_types(doc),
            count_dimensions(doc),
            count_dimension_overrides(doc),
        )
        revision_clouds_count = count_revision_clouds(doc)

        # output section
        output.close_others()
        output.set_height(900)
        output.set_width(1400)

        # RVT file dashboard section
        body_css = '<style>.grid-container { display: grid; justify-content: center; align-items: center; }</style><div class="grid-container">'

        # Main file infos
        project_info = [
            project_name,
            project_number,
            project_client,
            project_phases,
            worksets_names,
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
        rvtlinks_elements_items, rvtlinks_count, rvtlinks_type_load_status, rvtlinks_documents = (
            get_rvtlinks_elements_data(doc)
        )
        links_names, links_instances_names = get_rvt_links_names(rvtlinks_elements_items)
        if rvtlinks_elements_items:
            link_data = []
            pinned = get_revit_link_pinning_status(rvtlinks_elements_items)
            for idx, link_doc in enumerate(rvtlinks_documents):
                project_info_link = ProjectInfo(link_doc)
                project_name, project_number, project_client = (
                    project_info_link.name,
                    project_info_link.number,
                    project_info_link.client_name,
                )
                link_data.append(
                    [
                        project_name,
                        project_number,
                        project_client,
                        get_phases_names(link_doc),
                        get_worksets_names(link_doc),
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
            card_builder(100000, element_count, " Elements"),
            card_builder(1000, purgeable_elements_count, " Purgeable (2024+)"),
            card_builder(100, all_warnings_count, " Warnings"),
            card_builder(5, critical_warnings_count, " Critical Warnings"),
            card_builder(
                0, activated_analytical_model_elements_count, " Analytical Model ON"
            ),
            links_cards,
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
        data_str = [str(i) for i in data]

        export_to_csv(doc_clean_name, data, data_str, output)

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
        project_info = ProjectInfo(rvtlink)
        project_name, project_number, project_client = (
            project_info.name,
            project_info.number,
            project_info.client_name,
        )
        project_phases = get_phases_names(rvtlink)
        worksets_names = get_worksets_names(rvtlink)
        output.print_md(doc_clean_name)
        element_count = count_elements(rvtlink)
        purgeable_elements_count = count_purgeable_elements(rvtlink)
        all_warnings_count, _, warnings_guid = get_warnings_info(rvtlink)
        critical_warnings_count = get_critical_warnings_number(warnings_guid, CRITICAL_WARNINGS)
        rvtlinks_elements_items, rvtlinks_count, rvtlinks_type_load_status, rvtlinks_documents = (
            get_rvtlinks_elements_data(rvtlink)
        )
        rvtlinks_unpinned = count_unpinned_revit_links(rvtlinks_elements_items)
        activated_analytical_model_elements_count = count_analytical_model_activated(
            rvtlink
        )
        rooms_count, unplaced_rooms_count, unbounded_rooms = count_rooms(rvtlink)
        sheets_set = get_sheets(rvtlink)
        sheets_count = len(sheets_set)
        views = get_all_views(rvtlink)
        views_count = len(views)
        views_not_on_sheets = count_unplaced_views(sheets_set, views_count)
        schedule_count, schedules_not_sheeted_count = count_schedules(rvtlink)
        copied_views_count = count_copied_views(views)
        view_templates_count = len(get_all_view_templates(rvtlink))
        unused_view_templates_count = count_unused_view_templates(views)
        all_filters_count, unused_view_filters_count = count_filters(rvtlink, views)
        materials_count = len(get_elements_by_categories(element_bicats=[DB.BuiltInCategory.OST_Materials], doc=rvtlink))
        line_patterns_count = len(get_elements_by_class(DB.LinePatternElement, doc=rvtlink))
        dwgs_count, linked_dwg_count = count_dwg_files(rvtlink)
        inplace_family_count, not_parametric_families_count, family_count = count_families_by_type(
            rvtlink
        )
        imports_subcats_count = count_import_subcategories(rvtlink)
        generic_models_types_count = len(get_families(rvtlink))
        detail_components_count = count_detail_components(rvtlink)
        text_notes_types_count, text_notes_types_wf_count, text_bg_count = (
            count_textnote_types(rvtlink)
        )
        text_notes_count, text_notes_caps_count = count_text_notes(rvtlink)
        detail_groups_count, detail_groups_types_count = count_detail_groups(rvtlink)
        model_group_count, model_group_type_count = count_model_groups(rvtlink)
        reference_planes_count, unnamed_ref_planes_count = count_reference_planes(rvtlink)
        detail_lines_count = count_detail_lines(rvtlink)
        dim_types_count, dim_count, dim_overrides_count = (
            count_dimension_types(rvtlink),
            count_dimensions(rvtlink),
            count_dimension_overrides(rvtlink),
        )
        revision_clouds_count = count_revision_clouds(rvtlink)
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
        data_str = [str(i) for i in data]

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
        check_model(doc, output)

    def tearDown(self, doc, output):
        endtime = self.timer.get_time()
        endtime_hms = str(timedelta(seconds=endtime))
        endtime_hms_claim = (
            " \n\nCheck duration " + endtime_hms[0:7]
        )  # Remove seconds decimals from string
        output.print_md(endtime_hms_claim)
