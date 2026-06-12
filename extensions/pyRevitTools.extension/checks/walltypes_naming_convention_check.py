# -*- coding: UTF-8 -*-

import datetime
import json
from collections import Counter

# Revit-specific imports
from pyrevit import coreutils, script, DOCS
from pyrevit.forms import pick_file
from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector

import os

from pyrevit.coreutils import applocales
from pyrevit.preflight import PreflightTestCase

_XAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale", "Checks.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(_XAML, key)


def pick_json():
    # Set default directory
    default_dir = os.path.dirname(__file__)

    # Open the file dialog with the default path
    json_file_path = pick_file(file_ext="json", init_dir=default_dir)

    # Check if a file was selected
    if not json_file_path:
        raise FileNotFoundError(_t("NamingConventionNoFileSelected"))

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
    output.print_md("# {}".format(_t("NamingConventionReport")))

    # Get all wall elements and their names
    walls = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_Walls)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    # Count occurrences of each wall name
    wall_counts = Counter((wall.Name for wall in walls))

    # Load wall list from JSON
    allowed_wall_names = set(pick_json()["allowed_wall_types"])

    # Initialize results dictionary for found and wrong wall types
    wrong_wall_names = set(wall_counts) - allowed_wall_names

    # Prepare data for output table
    data = [
        (
            wall_type,
            count,
            _t("NamingConventionWrongName") if wall_type in wrong_wall_names else "",
        )
        for wall_type, count in wall_counts.items()
    ]

    # Print table and highlight incorrect wall names
    output.print_table(
        table_data=data,
        title=_t("NamingConventionWallCheck"),
        columns=[
            _t("NamingConventionWallType"),
            _t("NamingConventionCount"),
            _t("NamingConventionStatus"),
        ],
        formats=["", "{}", ""],
    )

    if wrong_wall_names:
        output.print_md("## {}".format(_t("NamingConventionIncorrectlyNamed")))
        for wrong in wrong_wall_names:
            print_red(output, wrong)


class ModelChecker(PreflightTestCase):
    name = _t("CheckName_NamingConvention")
    author = "Andreas Draxl"

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        check_model(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        print("{} {}".format(_t("TransactionTook"), endtime_hms))


ModelChecker.__doc__ = _t("CheckDescription_NamingConvention")


# Initialize variables
doc = DOCS.doc
output = script.get_output()

# Start model checker
if __name__ == "__main__":
    checker = ModelChecker()
    checker.startTest(doc, output)
