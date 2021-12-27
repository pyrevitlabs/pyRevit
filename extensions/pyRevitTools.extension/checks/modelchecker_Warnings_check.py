# -*- coding: UTF-8 -*-
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import datetime

from pyrevit import coreutils
from pyrevit import script
from pyrevit import revit, DB

from pyrevit.preflight import PreflightTestCase
from pyrevit.compat import safe_strtype

COLORS = 10 * [
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#000000",
    "#fff0f2",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#fff0e6",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#fff0e6",
    "#e97800",
    "#a6c844",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
]
# citical warnings Guids
CRITICAL_WARNINGS = [
    "6e1efefe-c8e0-483d-8482-150b9f1da21a",
    # 'Elements have duplicate "Number" values.',
    "6e1efefe-c8e0-483d-8482-150b9f1da21a",
    # 'Elements have duplicate "Type Mark" values.',
    "6e1efefe-c8e0-483d-8482-150b9f1da21a",
    # 'Elements have duplicate "Mark" values.',
    "b4176cef-6086-45a8-a066-c3fd424c9412",
    # 'There are identical instances in the same place',
    "4f0bba25-e17f-480a-a763-d97d184be18a",
    # 'Room Tag is outside of its Room',
    "505d84a1-67e4-4987-8287-21ad1792ffe9",
    # 'One element is completely inside another.',
    "8695a52f-2a88-4ca2-bedc-3676d5857af6",
    # 'Highlighted floors overlap.',
    "ce3275c6-1c51-402e-8de3-df3a3d566f5c",
    # 'Room is not in a properly enclosed region',
    "83d4a67c-818c-4291-adaf-f2d33064fea8",
    # 'Multiple Rooms are in the same enclosed region',
    "ce3275c6-1c51-402e-8de3-df3a3d566f5c",
    # 'Area is not in a properly enclosed region',
    "e4d98f16-24ac-4cbe-9d83-80245cf41f0a",
    # 'Multiple Areas are in the same enclosed region',
    "f657364a-e0b7-46aa-8c17-edd8e59683b9",
    # 'Room separation line is slightly off axis and may cause inaccuracies.''
]


def flatten(l):
    flat_list = []
    for sublist in l:
        for item in sublist:
            flat_list.append(item)
    return flat_list


def chunks(l, n):
    """Yield n number of striped chunks from l."""
    for i in range(0, n):
        yield l[i::n]


def inner_lists(lst):
    if all(isinstance(x, list) for x in lst):
        return [x for inner in lst for x in inner_lists(inner)]
    else:
        return [lst]


def unique(list1):
    # insert the list to the set
    list_set = set(list1)
    # convert the set to the list
    unique_list = list(list_set)
    for x in unique_list:
        print x,


def dashboardRectMaker(value, description, treshold):
    """dashboard HTMl maker - rectangle with large number"""
    content = str(value)
    # normal button
    if value <= treshold:
        html_code = (
            "<a class='dashboardLink' title='OK - maximum value "
            + str(int(treshold))
            + "'><p class='dashboardRectNormal'>"
            + content
            + "<br><span class='dashboardSmall'>"
            + description
            + "</span>"
            "</p></a>"
        )
        return coreutils.prepare_html_str(html_code)
    # mediocre button
    elif value < treshold * 2:
        html_code = (
            "<a class='dashboardLink' href='"
            + WIKI_ARTICLE
            + "' title='Mediocre - goal value "
            + str(int(treshold))
            + "'><p class='dashboardRectMediocre'>"
            + content
            + "<br><span class='dashboardSmall'>"
            + description
            + "</span>"
            "</p></a>"
        )
        return coreutils.prepare_html_str(html_code)
    # critical button
    else:
        html_code = (
            "<a class='dashboardLink' href='"
            + WIKI_ARTICLE
            + "' title='Critical - goal value "
            + str(int(treshold))
            + "'><p class='dashboardRectCritical'>"
            + content
            + "<br><span class='dashboardSmall'>"
            + description
            + "</span>"
            "</p></a>"
        )
        return coreutils.prepare_html_str(html_code)


def dashboardCenterMaker(value):
    """dashboard HTMl maker - div for center aligning"""
    content = str(value)
    html_code = "<div class='dashboardCenter'>" + content + "</div>"
    print (coreutils.prepare_html_str(html_code))


def dashboardLeftMaker(value):
    """dashboard HTMl maker - div for left aligning"""
    content = str(value)
    html_code = "<div class='dashboardLeft'>" + content + "</div>"
    print (coreutils.prepare_html_str(html_code))


def path2fileName(file_path, divider):
    """returns file name - everything in path from "\\" or "/" to the end"""
    lastDivider = file_path.rindex(divider) + 1
    file_name = file_path[lastDivider:]
    # print file_name
    return file_name


def checkModel(doc, output):
    """Check given model"""

    output.print_md("# **RVTV Links - Warning checker**")
    output.print_md("---")

    # first JS to avoid error in IE output window when at first run
    # this is most likely not proper way
    try:
        chartOuputError = output.make_doughnut_chart()
        chartOuputError.data.labels = []
        set_E = chartOuputError.data.new_dataset("Not Standard")
        set_E.data = []
        set_E.backgroundColor = ["#fff"]
        chartOuputError.set_height(1)
        chartOuputError.draw()
    except:
        pass

    ### Collectors ###

    ### RVTLinks collector
    # RVTLinks
    rvtlinks_id_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_RvtLinks)
        .WhereElementIsElementType()
        .ToElements()
    )
    if len(rvtlinks_id_collector) != 0:
        rvtlinkdocsName, rvtlink_status = [], []
        # checking loaded models
        for i in rvtlinks_id_collector:
            if str(i.GetLinkedFileStatus()) == "Loaded":
                rvtlink_status.append(True)
            else:
                rvtlink_status.append(False)
        if all(rvtlink_status):
            revitLinksdoc = DB.FilteredElementCollector(doc).OfClass(
                DB.RevitLinkInstance
            )
            revitLinksdoc_unique, revitLinksdoc_unique_name = [], []
            # isolating unique names and instances/types for links placed multiple times
            for i in revitLinksdoc:
                if i.GetLinkDocument().Title not in revitLinksdoc_unique_name:
                    revitLinksdoc_unique_name.append(i.GetLinkDocument().Title)
                    revitLinksdoc_unique.append(i)
            rvtlinkdocsName = revitLinksdoc_unique_name
            # RVTLinks
            rvtlinks_collector = (
                DB.FilteredElementCollector(doc)
                .OfCategory(DB.BuiltInCategory.OST_RvtLinks)
                .WhereElementIsNotElementType()
                # .ToElements()
            )

            def GetWarns(docs):
                all_warnings = []
                links = [doc.GetLinkDocument() for doc in docs]
                warnings_count = []
                warnings_count_int = []
                for link in links:
                    warnings = []
                    warnings_count_int.append(len(link.GetWarnings()))
                    warnings_count.append(str(len(link.GetWarnings())))
                    for warn in link.GetWarnings():
                        warnings.append(link.Title)
                        warnings.append(warn.GetDescriptionText())
                        elems = []
                        for i in warn.GetFailingElements():
                            elems.append(str(i))
                        warnings.append(str(elems))
                    all_warnings.append(warnings)
                return all_warnings, warnings_count, warnings_count_int

            # to be simplified in the list treatment
            links_warnings = GetWarns(revitLinksdoc_unique)
            warnings_count_num = links_warnings[2]
            links_warnings_count = list(
                chunks(rvtlinkdocsName + links_warnings[1], len(rvtlinkdocsName))
            )
            links_warnings = links_warnings[0]
            intermezzo = flatten(links_warnings)
            fileWarnings = list(chunks(intermezzo, 3))

            ## Warnings file dashboard section
            # output.print_md(str(fileWarnings))
            output.print_md("# Warnings count<br />")

            # Doughnut pie
            chartWarnings = output.make_doughnut_chart()
            chartWarnings.options.title = {
                "display": True,
                "text": "Warning Count by RVT link",
                "fontSize": 25,
                "fontColor": "#000",
                "fontStyle": "bold",
                "position": "left",
            }
            chartWarnings.options.legend = {"position": "top", "fullWidth": False}
            chartWarnings.data.labels = rvtlinkdocsName
            set_w = chartWarnings.data.new_dataset("Not Standard")
            set_w.data = warnings_count_num
            set_w.backgroundColor = COLORS
            chartWarnings.draw()

            # tables
            output.print_table(
                links_warnings_count,
                columns=["File Name", "Warnings count"],
                formats=None,
                title="",
                last_line_style="",
            )
            output.print_md("# Warnings details<br />")
            output.print_table(
                zip(*fileWarnings),
                columns=["File Name", "Warnings", "Ids"],
                formats=None,
                title="",
                last_line_style="",
            )
        else:
            output.print_md(
                "<b>Load all the links, the tool is meant for models with <ins>loaded</ins> links</b>"
            )
    else:
        output.print_md(
            "<b>Load at least one link, the tool is meant for models with <ins>loaded</ins> links </b>"
        )


class ModelChecker(PreflightTestCase):
    """
    Revit links Quality control - Warnings
        Warnings in linked files:
        - Description,
        - Ids,
        - Count

        !! Revit 2018 + only !!
        !!Load links before using!!
    """

    name = "RVTLinks warnings"
    author = "Jean-Marc Couffin"

    def setUp(self, doc, output):
        pass

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        endtime_hms_claim = "Transaction took " + endtime_hms
        print (endtime_hms_claim)

    def tearDown(self, doc, output):
        pass

    def doCleanups(self, doc, output):
        pass
