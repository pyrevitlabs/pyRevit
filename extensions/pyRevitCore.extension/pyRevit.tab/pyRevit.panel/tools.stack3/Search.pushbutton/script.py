from pyrevit import HOST_APP
from pyrevit.loader import sessionmgr
from pyrevit import forms
from pyrevit import script


__context__ = 'zerodoc'


logger = script.get_logger()


# get all default postable commands
postable_cmds = {x.name:x for x in HOST_APP.get_postable_commands()}

# find all available commands (for current selection)
# in currently active document
pyrevit_cmds = {}
for cmd in sessionmgr.find_all_available_commands():
    if cmd.name:
        pyrevit_cmds[cmd.name] = cmd


# build the search database
search_db = []
search_db.extend(pyrevit_cmds.keys())
search_db.extend(postable_cmds.keys())

# search
matched_cmdname = forms.SearchPrompt.show_prompt(search_db,
                                                 search_tip='pyRevit Search')

if matched_cmdname:
    # if postable command
    if matched_cmdname in postable_cmds.keys():
        __revit__.PostCommand(postable_cmds[matched_cmdname].rvtobj)
    # if pyrevit command
    else:
        selected_cmd = pyrevit_cmds[matched_cmdname]
        sessionmgr.execute_command_cls(selected_cmd.extcmd_type)
