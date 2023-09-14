# -*- coding: UTF-8 -*-
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import datetime

from pyrevit import coreutils
from pyrevit import DB

from pyrevit.preflight import PreflightTestCase


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
                    # element_data.append(output.linkify(element.Id)) Does not seem to work due to massive amount of elements
                    if worksetName not in worksets_names:
                        worksets_names.append(worksetName)
                    graph_workset_data.append(worksetName)
            except:
                pass
            
            # make sure there is no empty data in the set of 4 data, this check allows the following lambda function to work
            if len(element_data) == 4: 
                data.append(element_data)

    # sort by workset name
    data = sorted(data, key=lambda x: x[0])
    output.print_table(data, columns=['Workset Name', 'Element Category', 'Element Name', 'Element Id'])

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
            "text": "Element Count by Workset",
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
    """
    Revit model quality check
    The QC tools returns you with the following data:
        - Table of all elements by workset including category name, element name and element id
        - Element count per workset donut chart
    """

    name = "Elements per Worksets check"
    author = "Jean-Marc Couffin"

    def setUp(self, doc, output):
        pass

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        endtime_hms_claim = "Transaction took " + endtime_hms
        print(endtime_hms_claim)

    def tearDown(self, doc, output):
        pass

    def doCleanups(self, doc, output):
        pass
