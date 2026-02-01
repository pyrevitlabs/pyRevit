# -*- coding: UTF-8 -*-

import datetime
import json
from collections import Counter

# Revit-specific imports
from pyrevit import coreutils, revit, script, DOCS
from pyrevit.forms import pick_file
from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector

# Set up preflight for model check
import sys
import os
# Add current directory to path for local imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from pyrevit.preflight import PreflightTestCase
from check_translations import DocstringMeta

import json

def pick_json():
    # Set default directory
    default_dir = os.path.dirname(__file__)

    # Open the file dialog with the default path
    json_file_path = pick_file(file_ext="json", init_dir=default_dir)

    # Check if a file was selected
    if not json_file_path:
        from check_translations import get_check_translation
        raise FileNotFoundError(get_check_translation("NamingConventionNoFileSelected"))

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
    from check_translations import get_check_translation
    output.print_md('# {}'.format(get_check_translation("NamingConventionReport")))

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
        (wall_type, count, get_check_translation("NamingConventionWrongName") if wall_type in wrong_wall_names else "")
        for wall_type, count in wall_counts.items()
    ]

    # Print table and highlight incorrect wall names
    output.print_table(
        table_data=data,
        title=get_check_translation("NamingConventionWallCheck"),
        columns=[
            get_check_translation("NamingConventionWallType"),
            get_check_translation("NamingConventionCount"),
            get_check_translation("NamingConventionStatus")
        ],
        formats=['', '{}', '']
    )

    if wrong_wall_names:
        output.print_md('## {}'.format(get_check_translation("NamingConventionIncorrectlyNamed")))
        for wrong in wrong_wall_names:
            print_red(output, wrong)


class ModelChecker(PreflightTestCase):
    __metaclass__ = DocstringMeta
    _docstring_key = "CheckDescription_NamingConvention"
    
    @property
    def name(self):
        from check_translations import get_check_translation
        return get_check_translation("CheckName_NamingConvention")
    
    author = "Andreas Draxl"

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        check_model(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        from check_translations import get_check_translation
        print("{} {}".format(get_check_translation("TransactionTook"), endtime_hms))


# Initialize variables
doc = DOCS.doc
output = script.get_output()

# Start model checker
if __name__ == "__main__":
    checker = ModelChecker()
    checker.startTest(doc, output)
