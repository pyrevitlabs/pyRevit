#! python3
"""Manually exercise the supported modal forms against a live Revit owner."""

import datetime

from pyrevit import forms


if forms.alert(
    "Test CPython modal forms?",
    sub_msg="Check keyboard input, validation, Escape, window ownership and theme. "
    "Each cancelled input should print None. Run again after a pyRevit reload.",
    yes=True,
    no=True,
    ok=False,
):
    print("String: {!r}".format(forms.ask_for_string(default="Edit me")))
    print(
        "Unique string: {!r}".format(
            forms.ask_for_unique_string(
                ["Reserved"],
                default="Reserved",
                prompt="OK must stay disabled until this name changes.",
            )
        )
    )
    print("Date: {!r}".format(forms.ask_for_date(default=datetime.datetime.now())))
    print(
        "Number: {!r}".format(
            forms.ask_for_number_slider(
                default=25,
                min=0,
                max=100,
                interval=5,
                prompt="Choose a multiple of five.",
            )
        )
    )
    if forms.alert("Test native file and folder pickers?", yes=True, no=True, ok=False):
        print("File: {!r}".format(forms.pick_file()))
        print("Files: {!r}".format(forms.pick_file(multi_file=True)))
        print("Folder: {!r}".format(forms.pick_folder()))
        print("Save path: {!r}".format(forms.save_file(default_name="forms-test.txt")))
