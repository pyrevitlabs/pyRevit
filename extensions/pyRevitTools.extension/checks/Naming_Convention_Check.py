# -*- coding: UTF-8 -*-
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens

import datetime
import json
from collections import Counter

# Revit-specific imports
from pyrevit import coreutils, revit, script
from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector

# Set up preflight for model check
from pyrevit.preflight import PreflightTestCase

# Load wall list from JSON file
import os
import json
from rpw.ui.forms import select_file

def load_wall_list():
    json_file_path = select_file("JSON Files (*.json)|*.json")
    with open(json_file_path, "r") as f:
        data = json.load(f)
    return data["allowed_wall_types"]


# Define function to display text in red
def print_red(output, text):
    output.print_html('<div style="color:red">{}</div>'.format(text))

# Function to check the model's wall naming conventions
def check_model(doc, output):
    """
    Checks if wall types in the model match the allowed wall names list.
    Displays summary with correct and incorrect wall names.
    """
    output.print_md('# Model Naming Convention Report')

    # Get all wall elements and their names
    walls = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToElements()
    wall_names = [wall.Name for wall in walls]

    # Count occurrences of each wall name
    wall_list_counts = Counter(wall_names)

    # Load wall list from JSON
    wall_list = load_wall_list()

    # Initialize results dictionary for found and wrong wall types
    wall_comparison_result = {
        "found": {wall_type: count for wall_type, count in wall_list_counts.items() if wall_type in wall_list},
        "wrong": [wall_type for wall_type in wall_list_counts if wall_type not in wall_list]
    }

    # Prepare data for output table
    data = [
        (wall_type, count, "Wrong Name" if wall_type in wall_comparison_result["wrong"] else "")
        for wall_type, count in wall_list_counts.items()
    ]

    # Print table and highlight incorrect wall names
    output.print_table(
        table_data=data,
        title="Naming Convention Wall Check",
        columns=["Wall Type", "Count", "Status"],
        formats=['', '{}', '']
    )

    if wall_comparison_result["wrong"]:
        output.print_md('## Incorrectly Named Wall Types Found:')
        for wrong in wall_comparison_result["wrong"]:
            print_red(output, wrong)


class ModelChecker(PreflightTestCase):
    """
    Verifies whether family type names conform to a specified list,
    as defined by a wall type list within Revit.
    """

    name = "Naming Convention"
    author = "Andreas Draxl"

    def setUp(self, doc, output):
        pass

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        check_model(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        print("Transaction took {}".format(endtime_hms))

    def tearDown(self, doc, output):
        pass

    def doCleanups(self, doc, output):
        pass

# Initialize variables
doc = __revit__.ActiveUIDocument.Document
output = script.get_output()

# Start model checker
if __name__ == "__main__":
    checker = ModelChecker()
    checker.startTest(doc, output)
