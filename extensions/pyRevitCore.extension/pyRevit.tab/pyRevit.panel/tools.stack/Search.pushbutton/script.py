"""The best interface ever!"""
# -*- coding=utf-8 -*-
#pylint: disable=undefined-variable,import-error,invalid-name
import os
import os.path as op

from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit.loader import sessionmgr
from pyrevit import forms
from pyrevit import script
import pyrevit.extensions as exts


__context__ = 'zero-doc'
__title__ = {
    'en_us': 'Search',
    'fa': 'جستجو',
    'bg': 'Търси',
    'nl_nl': 'Zoek',
    'fr_fr': 'Rechercher',
    'de_de': 'Suche',
}


logger = script.get_logger()


HELP_SWITCH = '/help'
DOC_SWITCH = '/doc'
INFO_SWITCH = '/info'
OPEN_SWITCH = '/open'
SHOW_SWITCH = '/show'
ATOM_SWITCH = '/atom'
NPP_SWITCH = '/npp'
NP_SWITCH = '/np'
CONFIG_SWITCH = '/config'


def print_help():
    output = script.get_output()
    # output.set_width(500)
    output.print_md(
        '### Options:\n\n'
        '- **{help}**: Prints this help\n\n'
        '- **{help} COMMAND:** Opens the help url or prints the docstring\n\n'
        '- **{doc} [{config}] COMMAND:** Prints the command docstring\n\n'
        '- **{info} [{config}] COMMAND:** Prints info about the command\n\n'
        '- **{open} [{config}] COMMAND:** Opens the bundle folder\n\n'
        '- **{show} [{config}] COMMAND:** Shows the source code\n\n'
        '- **{atom} [{config}] COMMAND:** Opens the script in atom\n\n'
        '- **{npp} [{config}] COMMAND:** Opens the script in notepad++\n\n'
        '- **{np} [{config}] COMMAND:** Opens the script in notepad\n\n'
        '- **{config}:** Executes the config script (like Shift+Click).\n\n'
        .format(help=HELP_SWITCH,
                doc=DOC_SWITCH,
                info=INFO_SWITCH,
                open=OPEN_SWITCH,
                show=SHOW_SWITCH,
                atom=ATOM_SWITCH,
                npp=NPP_SWITCH,
                np=NP_SWITCH,
                config=CONFIG_SWITCH)
        )


def show_command_info(pyrvtcmd):
    print('Script Source: {}\n\n'
          'Config Script Source: {}\n\n'
          'Search Paths: {}\n\n'
          'Help Source: {}\n\n'
          'Name: {}\n\n'
          'Bundle Name: {}\n\n'
          'Extension Name: {}\n\n'
          'Unique Id: {}\n\n'
          'Class Name: {}\n\n'
          'Availability Class Name: {}\n\n'
          .format(pyrvtcmd.script,
                  pyrvtcmd.config_script,
                  pyrvtcmd.search_paths,
                  pyrvtcmd.helpsource,
                  pyrvtcmd.name,
                  pyrvtcmd.bundle,
                  pyrvtcmd.extension,
                  pyrvtcmd.unique_id,
                  pyrvtcmd.typename,
                  pyrvtcmd.extcmd_availtype
                  )
          )


def show_command_docstring(pyrvtcmd):
    script_content = coreutils.ScriptFileParser(selected_cmd.script)
    doc_string = script_content.get_docstring()
    custom_docstring = script_content.extract_param(exts.DOCSTRING_PARAM)
    if custom_docstring:
        doc_string = custom_docstring

    print(doc_string)


def open_command_helpurl(pyrvtcmd):
    script_content = coreutils.ScriptFileParser(selected_cmd.script)
    helpurl = script_content.extract_param(exts.COMMAND_HELP_URL_PARAM)
    if helpurl:
        script.open_url(helpurl)
        return True

    return False


def print_source(selected_cmd, altsrc=False):
    output = script.get_output()
    source = \
        selected_cmd.script if not altsrc else selected_cmd.config_script
    if source:
        with open(source, 'r') as s:
            output.print_code(s.read())


def open_in_editor(editor_name, selected_cmd, altsrc=False):
    source = \
        selected_cmd.script if not altsrc else selected_cmd.config_script
    if source:
        os.popen('{} "{}"'.format(editor_name, source))


# get all default postable commands
postable_cmds = {x.name: x for x in HOST_APP.get_postable_commands()}

# find all available commands (for current selection)
# in currently active document
pyrevit_cmds = {}
for cmd in sessionmgr.find_all_available_commands():
    if cmd.name:
        pyrevit_cmds[cmd.name] = cmd


# build the search database
search_db = {}
for cmd in pyrevit_cmds.values():
    search_db[cmd.name] = cmd.tooltip

for postcmd in postable_cmds.values():
    search_db[postcmd.name] = ""

# search
matched_cmdname, matched_cmdargs, switches = \
    forms.SearchPrompt.show(search_db,
                            switches=[HELP_SWITCH,
                                      DOC_SWITCH,
                                      INFO_SWITCH,
                                      OPEN_SWITCH,
                                      SHOW_SWITCH,
                                      ATOM_SWITCH,
                                      NPP_SWITCH,
                                      NP_SWITCH,
                                      CONFIG_SWITCH],
                            search_tip='type to search')

logger.debug('matched command: {}'.format(matched_cmdname))
logger.debug('arguments: {}'.format(matched_cmdargs))
logger.debug('switches: {}'.format(switches))

# if asking for help show help and exit
if switches[HELP_SWITCH] and not matched_cmdname:
    print_help()
    script.exit()

if matched_cmdname:
    # if postable command
    if matched_cmdname in postable_cmds.keys():
        if any(switches.values()):
            forms.alert('This is a native Revit command.')
        else:
            __revit__.PostCommand(postable_cmds[matched_cmdname].rvtobj)
    # if pyrevit command
    else:
        selected_cmd = pyrevit_cmds[matched_cmdname]
        if switches[INFO_SWITCH]:
            show_command_info(selected_cmd)
        elif switches[HELP_SWITCH]:
            if not open_command_helpurl(selected_cmd):
                show_command_docstring(selected_cmd)
        elif switches[DOC_SWITCH]:
            show_command_docstring(selected_cmd)
        elif switches[OPEN_SWITCH]:
            coreutils.open_folder_in_explorer(op.dirname(selected_cmd.script))
        elif switches[SHOW_SWITCH]:
            print_source(selected_cmd, altsrc=switches[CONFIG_SWITCH])
        elif switches[ATOM_SWITCH]:
            open_in_editor('atom', selected_cmd,
                           altsrc=switches[CONFIG_SWITCH])
        elif switches[NPP_SWITCH]:
            open_in_editor('notepad++', selected_cmd,
                           altsrc=switches[CONFIG_SWITCH])
        elif switches[NP_SWITCH]:
            open_in_editor('notepad', selected_cmd,
                           altsrc=switches[CONFIG_SWITCH])
        else:
            config_mode = switches[CONFIG_SWITCH] or switches[CONFIG_SWITCH]
            sessionmgr.execute_command_cls(selected_cmd.extcmd_type,
                                           arguments=matched_cmdargs,
                                           config_mode=config_mode)
