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
from pyrevit.script import get_config
from pyrevit.forms import alert, show_balloon
from pyrevit.output.cards import card_builder, create_frame
from pyrevit.revit.db import ProjectInfo
from pyrevit.revit.db.query import get_phases_names
from pyrevit.preflight import PreflightTestCase
from pyrevit.preflight.query import (
    clean_name,
    worksets,
    warnings,
    critical_warnings,
    rvtlinks_elements,
    rvt_links_name,
    rvt_links_unpinned_count,
    rvt_links_unpinned_str,
    analytical_model_activated_count,
    rooms,
    sheets,
    views_not_sheeted,
    views_bucket,
    schedules_count,
    copied_views,
    view_templates,
    unused_view_templates,
    filters,
    materials,
    line_patterns,
    dwgs,
    families,
    subcategories_imports,
    generic_models,
    details_components,
    text_notes_types,
    text_notes_instances,
    detail_groups,
    groups,
    reference_planes,
    elements_count,
    detail_lines,
    count_dimensions,
    count_dimension_types,
    count_dimension_overrides,
    revisions_clouds,
    get_purgeable_count,
)


user = HOST_APP.username
date = datetime.today().strftime("%d-%m-%Y")
revit_version_build = HOST_APP.build
DATASET_PREFIX = ", ".join([user, date, revit_version_build])

config = get_config()
if config is None:
    alert(
        "No configuration setn run the Preflight Checks clicking on the tool while maintaining ALT key to configurate. Exiting...",
        exitscript=True,
    )

CURRENT_FOLDER = config.get_option("current_folder")
CRITICAL_WARNINGS = config.get_option("critical_warnings")
EXPORT_FILE_PATH = config.get_option("export_file_path")
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


def export_to_csv(doc_clean_name, data, data_str, output):
    if not isfile(EXPORT_FILE_PATH):
        with open(EXPORT_FILE_PATH, mode="wb") as csv_file:
            w = writer(csv_file, lineterminator="\n")
            w.writerow(COLUMNS)
            w.writerow(data_str)
    else:
        with open(EXPORT_FILE_PATH, mode="rb") as csv_file:
            r = reader(csv_file, delimiter=",")
            flag = any(row[1] == date and row[2] == doc_clean_name for row in r)
        if not flag:
            with open(EXPORT_FILE_PATH, mode="ab") as csv_file:
                w = writer(csv_file, lineterminator="\n")
                w.writerow(data)
        output.self_destruct(30)


def check_model(doc, output):
    try:
        if doc.IsFamilyDocument:
            alert("This tool is for project files only. Exiting...", exitscript=True)
        project_info = ProjectInfo(doc)
        project_name, project_number, project_client = project_info.name, project_info.number, project_info.client_name
        project_phases = get_phases_names(doc)
        worksets_names = worksets(doc)
        doc_clean_name = clean_name(doc)
        element_count = elements_count(doc)
        purgeable_elements_count = get_purgeable_count(doc)
        all_warnings_count, _, warnings_guid = warnings(doc)
        critical_warnings_count = critical_warnings(warnings_guid, CRITICAL_WARNINGS)
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
        activated_analytical_model_elements_count = analytical_model_activated_count(
            doc
        )
        doc_cached_issues = DOCS.doc
        rooms_count, unplaced_rooms_count, unbounded_rooms = rooms(doc_cached_issues)
        sheets_count, sheets_set = sheets(doc_cached_issues)
        views_count, views = views_bucket(doc_cached_issues)
        views_not_on_sheets = views_not_sheeted(sheets_set, views_count)
        schedule_count, schedules_not_sheeted_count = schedules_count(doc_cached_issues)
        copied_views_count = copied_views(views)
        view_templates_count = view_templates(doc)
        unused_view_templates_count = unused_view_templates(views)
        all_filters_count, unused_view_filters_count = filters(doc, views)
        materials_count = materials(doc)
        line_patterns_count = line_patterns(doc)
        dwgs_count, linked_dwg_count = dwgs(doc)
        inplace_family_count, not_parametric_families_count, family_count = families(
            doc
        )
        imports_subcats_count = subcategories_imports(doc)
        generic_models_types_count = generic_models(doc)
        detail_components_count = details_components(doc)
        text_notes_types_count, text_notes_types_wf_count, text_bg_count = (
            text_notes_types(doc)
        )
        text_notes_count, text_notes_caps_count = text_notes_instances(doc)
        detail_groups_count, detail_groups_types_count = detail_groups(doc)
        model_group_count, model_group_type_count = groups(doc)
        reference_planes_count, unnamed_ref_planes_count = reference_planes(doc)
        detail_lines_count = detail_lines(doc)
        dim_types_count, dim_count, dim_overrides_count = (
            count_dimension_types(doc),
            count_dimensions(doc),
            count_dimension_overrides(doc),
        )
        revision_clouds_count = revisions_clouds(doc)

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
        rvtlinks_elements_items, rvtlinks_count, type_status, rvtlinks_documents = (
            rvtlinks_elements(doc)
        )
        links_names, links_instances_names = rvt_links_name(rvtlinks_elements_items)
        if rvtlinks_elements_items:
            link_data = []
            pinned = rvt_links_unpinned_str(rvtlinks_elements_items)
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
                        worksets(link_doc),
                        links_names[idx],
                        links_instances_names[idx],
                        type_status[idx],
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
            rvtlinks_unpinned = rvt_links_unpinned_count(rvtlinks_elements_items)
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
        link_printed_name = clean_name(rvtlink)
        output.print_md("## " + link_printed_name)
        output.print_md("___")
        if rvtlink is None:
            continue
        output.print_md(link_printed_name)
        element_count = elements_count(rvtlink)
        purgeable_elements_count = get_purgeable_count(rvtlink)
        all_warnings_count, _, warnings_guid = warnings(rvtlink)
        critical_warnings_count = critical_warnings(warnings_guid, CRITICAL_WARNINGS)
        rvtlinks_elements_items, rvtlinks_count, type_status, rvtlinks_documents = (
            rvtlinks_elements(rvtlink)
        )
        rvtlinks_unpinned = rvt_links_unpinned_count(rvtlinks_elements_items)
        activated_analytical_model_elements_count = analytical_model_activated_count(
            rvtlink
        )
        rooms_count, unplaced_rooms_count, unbounded_rooms = rooms(rvtlink)
        sheets_count, sheets_set = sheets(rvtlink)
        views_count, views = views_bucket(rvtlink)
        views_not_on_sheets = views_not_sheeted(sheets_set, views_count)
        schedule_count, schedules_not_sheeted_count = schedules_count(rvtlink)
        copied_views_count = copied_views(views)
        view_templates_count = view_templates(rvtlink)
        unused_view_templates_count = unused_view_templates(views)
        all_filters_count, unused_view_filters_count = filters(rvtlink, views)
        materials_count = materials(rvtlink)
        line_patterns_count = line_patterns(rvtlink)
        dwgs_count, linked_dwg_count = dwgs(rvtlink)
        inplace_family_count, not_parametric_families_count, family_count = families(
            rvtlink
        )
        imports_subcats_count = subcategories_imports(rvtlink)
        generic_models_types_count = generic_models(rvtlink)
        detail_components_count = details_components(rvtlink)
        text_notes_types_count, text_notes_types_wf_count, text_bg_count = (
            text_notes_types(rvtlink)
        )
        text_notes_count, text_notes_caps_count = text_notes_instances(rvtlink)
        detail_groups_count, detail_groups_types_count = detail_groups(rvtlink)
        model_group_count, model_group_type_count = groups(rvtlink)
        reference_planes_count, unnamed_ref_planes_count = reference_planes(rvtlink)
        detail_lines_count = detail_lines(rvtlink)
        dim_types_count, dim_count, dim_overrides_count = (
            count_dimension_types(rvtlink),
            count_dimensions(rvtlink),
            count_dimension_overrides(rvtlink),
        )
        revision_clouds_count = revisions_clouds(rvtlink)
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
