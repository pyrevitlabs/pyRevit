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
from pyrevit import script
from pyrevit.forms import alert, show_balloon
from pyrevit.preflight import PreflightTestCase
from pyrevit.preflight.query import (
    doc_name, clean_name, project_informations, phases, worksets, warnings,
    critical_warnings, rvtlinks_elements, rvt_links_name,
    rvt_links_unpinned_count, rvt_links_unpinned_str,
    analytical_model_activated_count, rooms, sheets,
    views_not_sheeted, views_bucket, unsheeted_schedules_count,
    copied_views, view_templates, unused_view_templates, filters, materials,
    line_patterns, dwgs, families, subcategories_imports, generic_models,
    details_components, text_notes_types, text_notes_instances, detail_groups,
    groups, reference_planes, elements_count, detail_lines, count_dimensions,
    count_dimension_types, count_dimension_overrides, revisions_clouds,
    get_purgeable_count, card_builder, create_frame
    )


user = HOST_APP.username
date = datetime.today().strftime("%d-%m-%Y")
revit_version_build = HOST_APP.build
DATASET_PREFIX = ", ".join([user, date, revit_version_build])

config = script.get_config()
if config is None:
    alert("No configuration setn run the Preflight Checks clicking on the tool while maintaining ALT key to configurate. Exiting...", exitscript=True)

CURRENT_FOLDER = config.get_option("current_folder")
CRITICAL_WARNINGS = config.get_option("critical_warnings")
EXPORT_FILE_PATH = config.get_option("export_file_path")
COLUMNS = ["user", "date", "doc_clean_name", "revit_version_build",
           "project_name", "project_number", "project_client",
           "project_phases", "worksets_names", "element_count",
           "purgeable_elements_count", "all_warnings_count",
           "critical_warnings_count", "rvtlinks_count",
           "activated_analytical_model_elements_count", "rooms_count",
           "unplaced_rooms_count", "sheets_count", "views_count",
           "views_not_on_sheets", "schedules_not_sheeted_count",
           "copied_views_count", "view_templates_count",
           "unused_view_templates_count", "all_filters_count",
           "unused_view_filters_count", "materials_count",
           "line_patterns_count", "dwgs_count", "linked_dwg_count",
           "inplace_family_count", "not_parametric_families_count",
           "family_count", "imports_subcats_count",
           "generic_models_types_count", "detail_components_count",
           "text_notes_types_count", "text_bg_count", "text_notes_types_wf_count",
           "text_notes_count", "text_notes_caps_count",
           "detail_groups_count", "detail_groups_types_count",
           "model_group_count", "model_group_type_count",
           "reference_planes_count", "unnamed_ref_planes_count",
           "detail_lines_count", "dim_types_count", "dim_count",
           "dim_overrides_count", "revision_clouds_count"
           ]


def check_model(doc, output):
    try:
        if doc.IsFamilyDocument:
            alert("This tool is for project files only. Exiting...", exitscript=True)
        # Project infos
        project_name, project_number, project_client = project_informations(
            doc)
        project_phases = phases(doc)
        worksets_names = worksets(doc)
        doc_clean_name = clean_name(doc)
        # Element Count
        element_count = elements_count(doc)
        # Purgeable Elements
        purgeable_elements_count = get_purgeable_count(doc)
        # Warnings
        all_warnings_count, _, warnings_guid = warnings(doc)
        critical_warnings_count = critical_warnings(warnings_guid, CRITICAL_WARNINGS)
        if all_warnings_count > 0:
            try:
                show_balloon(header='Warnings', text='The file {} contains {} warnings'.format(doc_clean_name, all_warnings_count), is_favourite=True, is_new=True)
            except Exception as e:
                print(e)
        # Links
        rvtlinks_elements_items, rvtlinks_count, type_status, rvtlinks_docs = rvtlinks_elements(doc)
        if rvtlinks_elements_items:
            projects_names, projects_numbers, projects_clients, projects_phases, projects_worksets, link_status = [], [], [], [], [], []
            for doc, status in zip(rvtlinks_docs, type_status):
                project_name, project_number, project_client = project_informations(
                    doc)
                projects_names.append(project_name)
                link_status.append(status)
                projects_numbers.append(project_number)
                projects_clients.append(project_client)
                projects_phases.append(phases(doc))
                projects_worksets.append(worksets(doc))
            rvtlinks_docs_name, rvtlinks_instances_name = rvt_links_name(
                rvtlinks_elements_items)
            rvtlinks_unpinned = rvt_links_unpinned_count(
                rvtlinks_elements_items)
            rvtlinks_unpinned_str = rvt_links_unpinned_str(
                rvtlinks_elements_items)
        # Analytical model
        activated_analytical_model_elements_count = analytical_model_activated_count(doc)
        # Rooms
        doc_cached_issues = DOCS.doc
        rooms_count, unplaced_rooms_count = rooms(doc_cached_issues)
        # sheets
        sheets_count, sheets_set = sheets(doc_cached_issues)
        # views
        views_count, views = views_bucket(doc_cached_issues)
        # views not on sheets
        views_not_on_sheets = views_not_sheeted(sheets_set, views_count)
        # Schedules
        schedules_not_sheeted_count = unsheeted_schedules_count(doc_cached_issues)
        # copied views
        copied_views_count = copied_views(views)
        # View Templates section
        _, view_templates_count = view_templates(doc)
        # Unused view templates section
        unused_view_templates_count = unused_view_templates(views)
        # view filters
        all_filters_count, unused_view_filters_count = filters(doc, views)
        # materials
        materials_count = materials(doc)
        # line patterns
        line_patterns_count = line_patterns(doc)
        # DWGs
        dwgs_count, linked_dwg_count = dwgs(doc)
        # families
        inplace_family_count, not_parametric_families_count, family_count = families(doc)
        # Imports in Families
        imports_subcats_count = subcategories_imports(doc)
        # Generic Models
        generic_models_types_count = generic_models(doc)
        # Detail Components
        detail_components_count = details_components(doc)
        # Text Notes
        # Text notes width factor != 1
        text_notes_types_count, text_notes_types_wf_count, text_bg_count = text_notes_types(doc)
        # Text notes with allCaps applied in Revit
        text_notes_count, text_notes_caps_count = text_notes_instances(doc)
        # detail groups
        detail_groups_count, detail_groups_types_count = detail_groups(doc)
        # model groups
        model_group_count, model_group_type_count = groups(doc)
        # reference plane without name
        reference_planes_count, unnamed_ref_planes_count = reference_planes(doc)
        # Detail Lines
        detail_lines_count = detail_lines(doc)
        # Dimensions
        dim_types_count, dim_count, dim_overrides_count = count_dimension_types(doc), count_dimensions(doc), count_dimension_overrides(doc)
        # Revision clouds
        revision_clouds_count = revisions_clouds(doc)

        # output section
        output.set_height(900)
        output.set_width(1200)
        output.close_others()
        output = script.get_output()

        # RVT file dashboard section
        body_css = '<style>.grid-container { display: grid; justify-content: center; align-items: center; }</style><div class="grid-container">'

        # Main file infos
        project_info = [project_name, project_number,project_client, project_phases, worksets_names, "N/A", "N/A", "N/A", "N/A"]
        output.print_md('# Main File Infos')
        output.print_table([project_info], columns=['Project Name', 'Project Number', 'Client Name', 'Project Phases', 'Worksets', 'Linked File Name', 'Instance Name','Loaded Status', 'Pinned status'])

        # Linked files infos
        links_cards = ''
        if rvtlinks_count != 0:
            data = zip(projects_names, projects_numbers, projects_clients, projects_phases, projects_worksets, rvtlinks_docs_name, rvtlinks_instances_name,  link_status,  rvtlinks_unpinned_str)
            columns_headers = ['Project Name', 'Project Number', 'Client Name', 'Project Phases', 'Worksets', 'Linked File Name', 'Instance Name','Loaded Status', 'Pinned status']
            output.print_md('# Linked Files Infos')
            output.print_table(data, columns=columns_headers)
            links_cards = card_builder(50, rvtlinks_count, ' Links') + card_builder(0, rvtlinks_unpinned, ' Links not pinned')

        output.print_md("# <p style='text-align: center;'>"+doc_clean_name+"</p>")

        critical_elements_frame = create_frame(
            "Critical Elements", 
            card_builder(100000, element_count, ' Elements'), card_builder(1000, purgeable_elements_count, ' Purgeable (2024+)'), card_builder(100, all_warnings_count, ' Warnings'), card_builder(5, critical_warnings_count, ' Critical Warnings'), card_builder(0, activated_analytical_model_elements_count, ' Analytical Model ON'), links_cards
            )

        rooms_frame = create_frame(
            "Rooms", 
            card_builder(1000, rooms_count, ' Rooms'), card_builder(0, unplaced_rooms_count, ' Unplaced Rooms')
            )

        sheets_views_graphics_frame = create_frame(
            "Sheets, Views, Graphics", 
            card_builder(500, sheets_count, ' Sheets'), card_builder(1500, views_count, ' Views'),card_builder(300, views_not_on_sheets, ' Views not on Sheets'), card_builder(5, schedules_not_sheeted_count, ' Schedules not on sheet'), card_builder(0, copied_views_count, ' Copied Views'), card_builder(100, view_templates_count, ' View Templates'), card_builder(0, unused_view_templates_count, ' Unused VT'), card_builder(0, all_filters_count, ' Filters'), card_builder(0, unused_view_filters_count, ' Unused Filters')
            )

        cad_files_frame = create_frame(
            "CAD Files",
            card_builder(5, dwgs_count, ' DWGs'), card_builder(5, linked_dwg_count, ' Linked DWGs')
            )

        families_frame = create_frame(
            "Families",
            card_builder(500, family_count, ' Families'), card_builder(0, inplace_family_count, ' In-Place Families'), card_builder(100, not_parametric_families_count, ' Non-Parametric Families'), card_builder(0, imports_subcats_count, ' Imports in Families'), card_builder(50, generic_models_types_count, ' Generic Models Types'), card_builder(100, detail_components_count, ' Detail Components')
            )

        graphical2d_elements_frame = create_frame(
            "Graphical 2D Elements",
            card_builder(5000, detail_lines_count, ' Detail Lines'),  card_builder(30, line_patterns_count, ' Line Patterns'),  card_builder(30, text_notes_types_count, ' Text Notes Types'),  card_builder(1, text_bg_count, ' Text Notes w/ White Background'),  card_builder(0, text_notes_types_wf_count, ' Text Notes wfactor!=1'), card_builder(2000, text_notes_count, ' Text Notes'), card_builder(100, text_notes_caps_count, ' Text Notes allCaps'), card_builder(5, dim_types_count, ' Dimension Types'), card_builder(5000, dim_count, ' Dimensions'), card_builder(0, dim_overrides_count, ' Dimension Overrides'), card_builder(100, revision_clouds_count, ' Revision Clouds')
            )

        groups_summary_frame = create_frame(
            "Groups", 
            card_builder(10, model_group_count, ' Model Groups'), card_builder(5, model_group_type_count, ' Model Group Types'), card_builder(10, detail_groups_count, ' Detail Groups'), card_builder(20, detail_groups_types_count, ' Detail Group Types')
            )

        reference_planes_frame = create_frame(
            "Reference Planes", 
            card_builder(100, reference_planes_count, ' Ref Planes'), card_builder(10, unnamed_ref_planes_count, ' Ref Planes no_name')
            )

        html_content = body_css + \
            critical_elements_frame + \
            rooms_frame+ \
            sheets_views_graphics_frame + \
            cad_files_frame + \
            families_frame + \
            graphical2d_elements_frame + \
            groups_summary_frame + \
            reference_planes_frame + \
            create_frame(
                'Materials',
                card_builder(100, materials_count, ' Materials')
                )

        output.print_html(html_content + '</div>')

        # concatenate data for csv export
        data = [user, date, doc_clean_name, revit_version_build, project_name, project_number, project_client, project_phases, worksets_names, element_count, purgeable_elements_count, all_warnings_count, critical_warnings_count, rvtlinks_count, activated_analytical_model_elements_count, rooms_count, unplaced_rooms_count, sheets_count, views_count, views_not_on_sheets, schedules_not_sheeted_count, copied_views_count, view_templates_count, unused_view_templates_count, all_filters_count, unused_view_filters_count, materials_count, line_patterns_count, dwgs_count, linked_dwg_count, inplace_family_count, not_parametric_families_count, family_count, imports_subcats_count, generic_models_types_count, detail_components_count, text_notes_types_count, text_bg_count, text_notes_types_wf_count, text_notes_count, text_notes_caps_count, detail_groups_count, detail_groups_types_count, model_group_count, model_group_type_count, reference_planes_count, unnamed_ref_planes_count, detail_lines_count, dim_types_count, dim_count, dim_overrides_count, revision_clouds_count]
        data_str = [str(i) for i in data]

        # create new csv file at export_file_path
        if not isfile(EXPORT_FILE_PATH):
            with open(EXPORT_FILE_PATH, mode='wb') as csv_file:
                w = writer(csv_file, lineterminator='\n')
                w.writerow(COLUMNS)
                w.writerow(data_str)
        else:
            with open(EXPORT_FILE_PATH, mode='rb') as csv_file:
                r = reader(csv_file, delimiter=',')
                flag = False
                for row in r:
                    if row[1] == date and row[2] == doc_clean_name:
                        flag = True
                        # print('Data already in csv file')
                        break
            if not flag:
                with open(EXPORT_FILE_PATH, mode='ab') as csv_file:
                    # print('writing')
                    w = writer(csv_file, lineterminator='\n')
                    w.writerow(data)

        # RVTLinks
        if rvtlinks_count != 0:
            output.print_md('# RVTLinks')
            for rvtlink in rvtlinks_docs:
                link_name = doc_name(rvtlink)
                link_printed_name = clean_name(rvtlink)
                output.print_md('## ' + link_printed_name)
                output.print_md('___')
                if rvtlink is not None:
                    output.print_md(link_name)
                    # Cards
                    html_content = body_css
                    # Element Count
                    element_count = elements_count(rvtlink)
                    # Purgeable Elements
                    purgeable_elements_count = get_purgeable_count(rvtlink)
                    # Warnings
                    all_warnings_count, _, warnings_guid = warnings(rvtlink)
                    critical_warnings_count = critical_warnings(warnings_guid,CRITICAL_WARNINGS)
                    # Links
                    rvtlinks_elements_items, rvtlinks_count, type_status, rvtlinks_docs = rvtlinks_elements(rvtlink)
                    rvtlinks_unpinned = rvt_links_unpinned_count(rvtlinks_elements_items)
                    # Analytical model section
                    activated_analytical_model_elements_count = (analytical_model_activated_count(rvtlink))
                    # Rooms
                    rooms_count, unplaced_rooms_count = rooms(rvtlink)
                    # Sheets
                    sheets_count, sheets_set = sheets(rvtlink)
                    # Views
                    views_count, views = views_bucket(rvtlink)
                    # views not on sheets
                    views_not_on_sheets = views_not_sheeted(sheets_set, views_count)
                    # Schedules
                    schedules_not_sheeted_count = unsheeted_schedules_count(rvtlink)
                    # copied views
                    copied_views_count = copied_views(views)
                    # View Templates section
                    _, view_templates_count = view_templates(rvtlink)
                    # Unused view templates section
                    unused_view_templates_count = unused_view_templates(views)
                    # filters
                    all_filters_count, unused_view_filters_count = filters(rvtlink, views)
                    # materials
                    materials_count = materials(rvtlink)
                    # line patterns
                    line_patterns_count = line_patterns(rvtlink)
                    # dwgs
                    dwgs_count, linked_dwg_count = dwgs(rvtlink)
                    # families
                    inplace_family_count, not_parametric_families_count, family_count = families(rvtlink)
                    # Imports in Families
                    imports_subcats_count = subcategories_imports(rvtlink)
                    # Generic Models
                    generic_models_types_count = generic_models(rvtlink)
                    # Detail Components
                    detail_components_count = details_components(rvtlink)
                    # Text Notes
                    # Text notes width factor != 1
                    text_notes_types_count, text_notes_types_wf_count, text_bg_count = text_notes_types(rvtlink)
                    # Text notes with allCaps applied in Revit
                    text_notes_count, text_notes_caps_count = text_notes_instances(rvtlink)
                    # detail groups
                    detail_groups_count, detail_groups_types_count = detail_groups(rvtlink)
                    # model groups
                    model_group_count, model_group_type_count = groups(rvtlink)
                    # reference plane without name
                    reference_planes_count, unnamed_ref_planes_count = reference_planes(rvtlink)
                    # detail lines
                    detail_lines_count = detail_lines(rvtlink)
                    # Dimensions
                    dim_types_count, dim_count, dim_overrides_count = count_dimension_types(rvtlink), count_dimensions(rvtlink), count_dimension_overrides(rvtlink)
                    # Revision clouds
                    revision_clouds_count = revisions_clouds(rvtlink)
                    links_data = ''
                    if rvtlinks_count != 0:
                        links_data += card_builder(50, rvtlinks_count, ' Links') + \
                            card_builder(0, rvtlinks_unpinned,
                                         ' Links not pinned')

                    critical_elements_frame = create_frame(
                            "Critical Elements", 
                            card_builder(100000, element_count, ' Elements'), card_builder(1000, purgeable_elements_count, ' Purgeable (2024+)'), card_builder(100, all_warnings_count, ' Warnings'), card_builder(5, critical_warnings_count, ' Critical Warnings'), card_builder(0, activated_analytical_model_elements_count, ' Analytical Model ON'), links_data
                            )

                    rooms_frame = create_frame(
                        "Rooms",
                        card_builder(1000, rooms_count, ' Rooms'), card_builder(0, unplaced_rooms_count, ' Unplaced Rooms')
                        )

                    sheets_views_graphics_frame = create_frame(
                        "Sheets, Views, Graphics",
                        card_builder(500, sheets_count, ' Sheets'), card_builder(1500, views_count, ' Views'), card_builder(300, views_not_on_sheets, ' Views not on Sheets'), card_builder(5, schedules_not_sheeted_count, ' Schedules not on sheet'), card_builder(0, copied_views_count, ' Copied Views'), card_builder(100, view_templates_count, ' View Templates'), card_builder(0, unused_view_templates_count, ' Unused VT'), card_builder(0, all_filters_count, ' Filters'), card_builder(0, unused_view_filters_count, ' Unused Filters')
                        )

                    cad_files_frame = create_frame(
                        "CAD Files",
                        card_builder(5, dwgs_count, ' DWGs'), card_builder(5, linked_dwg_count, ' Linked DWGs')
                        )

                    families_frame = create_frame(
                        "Families",
                        card_builder(500, family_count, ' Families'), card_builder(0, inplace_family_count, ' In-Place Families'), card_builder(100, not_parametric_families_count, ' Non-Parametric Families'), card_builder(0, imports_subcats_count, ' Imports in Families'), card_builder(50, generic_models_types_count, ' Generic Models Types'), card_builder(100, detail_components_count, ' Detail Components')
                        )

                    graphical2d_elements_frame = create_frame(
                        "Graphical 2D Elements",
                        card_builder(5000, detail_lines_count, ' Detail Lines'),  card_builder(30, line_patterns_count, ' Line Patterns'),  card_builder(30, text_notes_types_count, ' Text Notes Types'),  card_builder(1, text_bg_count, ' Text Notes w/ White Background'),  card_builder(0, text_notes_types_wf_count, ' Text Notes wfactor!=1'), card_builder(2000, text_notes_count, ' Text Notes'), card_builder(100, text_notes_caps_count, ' Text Notes allCaps'), card_builder(5, dim_types_count, ' Dimension Types'), card_builder(5000, dim_count, ' Dimensions'), card_builder(0, dim_overrides_count, ' Dimension Overrides'), card_builder(100, revision_clouds_count, ' Revision Clouds')
                        )

                    groups_summary_frame = create_frame(
                        "Groups",
                        card_builder(10, model_group_count, ' Model Groups'), card_builder(5, model_group_type_count, ' Model Group Types'), card_builder(10, detail_groups_count, ' Detail Groups'), card_builder(20, detail_groups_types_count, ' Detail Group Types')
                        )

                    reference_planes_frame = create_frame(
                        "Reference Planes",
                        card_builder(100, reference_planes_count, ' Ref Planes'), card_builder(10, unnamed_ref_planes_count, ' Ref Planes no_name')
                        )

                    html_content += \
                        critical_elements_frame + \
                        rooms_frame + \
                        sheets_views_graphics_frame + \
                        cad_files_frame + \
                        families_frame + \
                        graphical2d_elements_frame + \
                        groups_summary_frame + \
                        reference_planes_frame + \
                        create_frame(
                            'Materials',
                            card_builder(100, materials_count, ' Materials')
                            )

                    output.print_html(html_content + '</div>')
                else:
                    pass
        output.self_destruct(180)
    except Exception as e:
        print(format_exc())
        print(e)
        output.self_destruct(30)



timer = Timer()

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


    def startTest(self, doc, output):
        check_model(doc, output)

    def tearDown(self, doc, output):
        endtime = timer.get_time()
        endtime_hms = str(timedelta(seconds=endtime))
        endtime_hms_claim = " \n\nCheck duration " + endtime_hms[0:7]  # Remove seconds decimals from string
        output.print_md(endtime_hms_claim)
