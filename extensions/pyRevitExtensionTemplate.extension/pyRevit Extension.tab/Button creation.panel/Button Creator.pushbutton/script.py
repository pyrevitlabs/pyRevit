# -*- coding=utf-8 -*-
"""
Create a new button from a template of button bundles.
"""

import os
import shutil
from pyrevit.forms import ask_for_string, alert, CommandSwitchWindow
from pyrevit import script
from pyrevit.loader import sessionmgr

current_folder = os.path.dirname(__file__)
up_folder = os.path.dirname(current_folder)
button_types_folder = "button_types"
button_types_folder = os.path.join(up_folder, button_types_folder)
# to extend add entry to dict: {"button type": ["bundle extension", "button template folder"]}
buttton_type_dict = {"pushbutton": ["pushbutton", "pushbutton"],
                     "pushbutton with config": ["pushbutton", "pushbutton_with_config"],
                     "pushbutton for Dynamo script": ["pushbutton", "pushbutton_for_dynamo_script"],
                     "content button": ["content", "content_button"],
                     "url button": ["urlbutton", "url_button"],
                     "invoke C# dll button": ["invoke", "invoke_dll_button"],
                     }


def button_template(button_type):
    button_folder = "pushbutton"
    button_template_folder_str = "pushbutton"
    if button_type in buttton_type_dict:
        button_folder = buttton_type_dict[button_type][0]
        button_template_folder_str = buttton_type_dict[button_type][1]
    button_template_folder = os.path.join(
        button_types_folder, button_template_folder_str)
    return button_folder, button_template_folder


def create_button(button_type):
    button_folder, button_template_folder = button_template(button_type)
    newname = ask_for_string(
        title="New Folder", instructions="Specify name for new button")
    if not newname:
        alert("No name specified, will exit")
        script.exit()
    newfolder = os.path.join(up_folder, newname + "." + button_folder)

    if os.path.exists(newfolder):
        alert("Folder already exists")
    else:
        os.mkdir(newfolder)
        for f in os.listdir(button_template_folder):
            file = os.path.join(button_template_folder, f)
            shutil.copy(file, newfolder)
            if button_type == "invoke C# dll button":
                # copy bin folder to root of newfolder
                bin_template_folder = os.path.join(up_folder, "bin")
                bin_folder = os.path.join(up_folder, "bin")
                os.mkdir(bin_folder)
                for f in os.listdir(bin_template_folder):
                    file = os.path.join(bin_template_folder, f)
                    shutil.copy(file, bin_folder)
        for copied_file in os.listdir(newfolder):
            if copied_file.endswith(".yaml"):
                # get english title string and replace with newname
                path = os.path.join(newfolder, copied_file)
                with open(path, "r") as f:
                    lines = f.readlines()
                with open(path, "w") as f:
                    for line in lines:
                        if "  en_us: english title" in line:
                            line = "  en_us: {}\n".format(newname)
                        f.write(line)


while True:
    button_type_selected = CommandSwitchWindow.show(
        buttton_type_dict.keys(), message="Select button type")
    if button_type_selected:
        create_button(button_type_selected)
    res = CommandSwitchWindow.show(
        ["Yes", "No"], message="Create another one?")
    if res == "No":
        sessionmgr.reload_pyrevit()
        break
