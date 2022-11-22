# -*- coding=utf-8 -*-

import os
import shutil
import webbrowser
from pyrevit.forms import ask_for_string, alert
from pyrevit import script
from pyrevit.loader import sessionmgr
from pyrevit.loader import sessioninfo


def create_pushbutton():
    current_folder = os.path.dirname(__file__)
    up_folder = os.path.dirname(current_folder)
    template_folder = os.path.join(current_folder, 'TemplateFolder')
    newname = ask_for_string(
        title="New Folder", instructions="Specify name for new command"
    )
    if not newname:
        return
    newfolder = os.path.join(up_folder, newname + ".pushbutton")
    if os.path.exists(newfolder):
        alert("Folder already exists")
    else:
        os.mkdir(newfolder)
        for f in os.listdir(template_folder):
            file = os.path.join(template_folder, f)
            shutil.copy(file, newfolder)
        webbrowser.open(newfolder)
        logger = script.get_logger()
        results = script.get_results()
        # re-load pyrevit session.
        logger.info("Reloading....")
        sessionmgr.reload_pyrevit()
        results.newsession = sessioninfo.get_session_uuid()

create_pushbutton()
