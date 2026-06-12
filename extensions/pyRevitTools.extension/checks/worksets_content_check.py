# -*- coding: UTF-8 -*-
import datetime
import os

from pyrevit import coreutils
from pyrevit import DB
from pyrevit.coreutils import applocales
from pyrevit.preflight import PreflightTestCase

_XAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale", "Checks.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(_XAML, key)


# LISTS
# COLORS for chart.js graphs - chartCategories.randomize_colors() sometimes
# creates COLORS which are not distunguishable or visible
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


def checkModel(doc, output):
    """Check given model"""

    # elements by workset graph
    worksets_names = []
    graph_workset_data = []
    data = []

    all_elements = (
        DB.FilteredElementCollector(doc)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    worksetTable = doc.GetWorksetTable()
    for element in all_elements:
        worksetId = element.WorksetId
        worksetKind = str(worksetTable.GetWorkset(worksetId).Kind)
        if worksetKind == "UserWorkset":
            element_data = []
            worksetName = worksetTable.GetWorkset(worksetId).Name
            try:
                if element.Name not in ('DefaultLocation', '', None) or element.Category.Name not in ('', None):
                    # Remove the location objects from the list as well as empty elements or proxies
                    element_data.append(worksetName)
                    element_data.append(element.Category.Name)
                    element_data.append(element.Name)
                    element_data.append(element.Id)
                    # element_data.append(output.linkify(element.Id)) Does not seem to work due
                    # to massive amount of elements
                    if worksetName not in worksets_names:
                        worksets_names.append(worksetName)
                    graph_workset_data.append(worksetName)
            except Exception:
                pass

            # make sure there is no empty data in the set of 4 data, this check allows the following
            # lambda function to work
            if len(element_data) == 4:
                data.append(element_data)

    # sort by workset name
    data = sorted(data, key=lambda x: x[0])
    output.print_table(data, columns=[
        _t("WorksetName"),
        _t("ElementCategory"),
        _t("ElementName"),
        _t("ElementId"),
    ])

    # sorting results in chart legend
    worksets_names.sort()

    worksetsSet = []
    for i in worksets_names:
        count = graph_workset_data.count(i)
        worksetsSet.append(count)
    worksets_names = [x.encode("utf8") for x in worksets_names]

    # Worksets OUTPUT print chart only when file is workshared
    if len(worksets_names) > 0:
        chartWorksets = output.make_doughnut_chart()
        chartWorksets.options.title = {
            "display": True,
            "text": _t("ElementCountByWorkset"),
            "fontSize": 25,
            "fontColor": "#000",
            "fontStyle": "bold",
        }
        chartWorksets.data.labels = worksets_names
        set_a = chartWorksets.data.new_dataset("Not Standard")
        set_a.data = worksetsSet

        set_a.backgroundColor = COLORS

        worksetsCount = len(worksets_names)
        if worksetsCount < 15:
            chartWorksets.set_height(100)
        elif worksetsCount < 30:
            chartWorksets.set_height(160)
        else:
            chartWorksets.set_height(200)
        chartWorksets.draw()


class ModelChecker(PreflightTestCase):
    name = _t("CheckName_ElementsPerWorksets")
    author = "Jean-Marc Couffin"

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        endtime_hms_claim = "{} {}".format(_t("TransactionTook"), endtime_hms)
        print(endtime_hms_claim)


ModelChecker.__doc__ = _t("CheckDescription_ElementsPerWorksets")
