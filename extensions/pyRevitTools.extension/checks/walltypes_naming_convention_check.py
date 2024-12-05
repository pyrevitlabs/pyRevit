# -*- coding: UTF-8 -*-

import datetime
import json
from collections import Counter

# Revit-specific imports
from pyrevit import coreutils, revit, script, DOCS
from pyrevit.forms import pick_file
from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector

# Set up preflight for model check
from pyrevit.preflight import PreflightTestCase

# Load wall list from JSON file
import os
import json

def pick_json():
    # Set default directory
    default_dir = os.path.dirname(__file__)

    # Open the file dialog with the default path
    json_file_path = pick_file(file_ext="json", init_dir=default_dir)

    # Check if a file was selected
    if not json_file_path:
        raise FileNotFoundError("No JSON file selected.")

    # Load JSON data
    with open(json_file_path, "r") as f:
        return json.load(f)


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
    # Count occurrences of each wall name
    wall_counts = Counter((wall.Name for wall in walls))

    # Load wall list from JSON
    allowed_wall_names = set(pick_json()["allowed_wall_types"])

    # Initialize results dictionary for found and wrong wall types
    wrong_wall_names = set(wall_counts) - allowed_wall_names

    # Prepare data for output table
    data = [
        (wall_type, count, "Wrong Name" if wall_type in wrong_wall_names else "")
        for wall_type, count in wall_counts.items()
    ]

    # Print table and highlight incorrect wall names
    output.print_table(
        table_data=data,
        title="Naming Convention Wall Check",
        columns=["Wall Type", "Count", "Status"],
        formats=['', '{}', '']
    )

    if wrong_wall_names:
        output.print_md('## Incorrectly Named Wall Types Found:')
        for wrong in wrong_wall_names:
            print_red(output, wrong)


class ModelChecker(PreflightTestCase):
    """
    Verifies whether family type names conform to a specified list,
    as defined by a wall type list within Revit.
    """

    name = "Naming Convention"
    author = "Andreas Draxl"

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        check_model(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        print("Transaction took {}".format(endtime_hms))


# Initialize variables
doc = DOCS.doc
output = script.get_output()

# Start model checker
if __name__ == "__main__":
    checker = ModelChecker()
    checker.startTest(doc, output)
