# -*- coding: UTF-8 -*-

import datetime
from pyrevit import script
from pyrevit import revit, DB

output = script.get_output()
output.close_others(True)
output.center()
output.set_title('Models Checker')


doc = revit.doc

# Grab data from config
my_config = script.get_config()
tests = getattr(my_config, "BILT_tests")

# Series of queries

def project_number(doc):
    project_number = doc.ProjectInformation.Number
    return project_number

def project_name(doc):
    project_name = doc.ProjectInformation.Name
    return project_name

def doc_warnings(doc):
    warnings = doc.GetWarnings()
    descriptions = []
    for warning in warnings:
        descriptions.append(DB.FailureMessage.GetDescriptionText(warning))
    if len(descriptions):
        return str(len(descriptions)) + ' Warnings in the project'

# set minimal value to empty string
pname, pnumber, warnings = "", "", ""

# check if queries requested in config file
if tests == [] or tests == None:
    pname = project_name(doc)
    pnumber = project_number(doc)
    warnings = warnings(doc)
if "Project Name" in tests:
    pname = project_name(doc)
if "Project Number" in tests:
    pnumber = project_number(doc)
if "Warnings" in tests:
    warnings = doc_warnings(doc)

# print the whole thing
output.print_md(pname + "\n\n" + pnumber + "\n\n" + warnings)