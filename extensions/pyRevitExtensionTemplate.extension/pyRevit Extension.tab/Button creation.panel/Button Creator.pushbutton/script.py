# -*- coding=utf-8 -*-

import os
import shutil
from pyrevit.forms import ask_for_string, alert, CommandSwitchWindow
from pyrevit import script
from pyrevit.loader import sessionmgr


def create_button(button_type="pushbutton"):
    current_folder = os.path.dirname(__file__)
    up_folder = os.path.dirname(current_folder)
    template_folder = os.path.join(up_folder, button_type)
    newname = ask_for_string(
        title="New Folder", instructions="Specify name for new button")

    if not newname:
        script.exit()

    newfolder = os.path.join(up_folder, newname + "." + button_type)
    if os.path.exists(newfolder):
        alert("Folder already exists")
    else:
        os.mkdir(newfolder)
        for f in os.listdir(template_folder):
            file = os.path.join(template_folder, f)
            shutil.copy(file, newfolder)
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


# get the button count from user
button_count = ask_for_string(
    prompt='How many buttons do you want to create?', title='Number of buttons')

for i in range(int(button_count)):
    # select the type of button you want to create:
    button_type_selected = CommandSwitchWindow.show(["pushbutton", "urlbutton"],
                                                    message="Select button type")
    if button_type_selected:
        create_button(button_type_selected)
sessionmgr.reload_pyrevit()
