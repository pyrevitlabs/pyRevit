""" parsers.py
Parse directories and file list and create the corresposponding UI elements
such as Tabs, Panels, RibbonButtons, and Commands
"""

import os
from os import path
import re
import fnmatch

from loader.logger import logger
from loader.uielements import Ribbon, Tab, Panel, Command
from loader.uielements import RibbonButton, PushButton, PullDown
from loader.config import PKG_IDENTIFIER, LOADER

def parse_directory(script_dir):
    """ Parses SCRIPT_DIR to find tabs, panels, and scripts, sequentially
    Tabs and Panels are only created if valid commands are created.
    Parsing relies heavily on .identifies attributes stored in
    UI classes. These attributes are used to identify corresponding
    files.
    """

    logger.title('Parsing Directory...')
    ribbon = Ribbon()

    packages = [pkg for pkg in os.listdir(script_dir) if PKG_IDENTIFIER in pkg]
    for package in packages:
        package_path = path.join(script_dir, package)

        tabs_folder = [t for t in os.listdir(package_path) if t.endswith(Tab.identifier)]

        for tab_folder in tabs_folder:
            tab_path = path.join(package_path, tab_folder)
            tab_name = tab_folder.split(Tab.identifier)[0]
            tab = Tab(ribbon=ribbon, tab_name=tab_name)

            panels_folder = [p for p in os.listdir(tab_path) if p.endswith(Panel.identifier)]
            for panel_folder in panels_folder:
                panel_path = path.join(tab_path, panel_folder)

                all_files = os.listdir(panel_path)
                py_files = [f for f in all_files if f.lower().endswith('.py')]
                png_files = [f for f in all_files if f.lower().endswith('.png')]

                #"PanelName.panel".split('.panel')[0] - "PanelName"
                panel_name = panel_folder.split(Panel.identifier)[0]
                panel = Panel(tab=tab, panel_name=panel_name)
                ribbon_buttons = parse_files(panel, panel_path, png_files, py_files)

                if ribbon_buttons:
                    panel.ribbon_buttons.extend(ribbon_buttons)
                    tab.panels[panel.name] = panel    # Adds parent panel as attribute
                else:
                    logger.warning('No commands for panel: {}'.format(panel.name))

            if tab.panels:
                ribbon.tabs[tab.name] = tab
            else:
                logger.warning('Tab had no panels: {}'.format(tab_name))
    return ribbon


#  Matchs if Putton Identifier is present, returns cmd name
pattern_button_type = r'(?<={id}_)[a-zA-Z0-9\s]+'

#  Matchs if Cmd_name is present, returns cmd name
pattern_cmd_name = r'(?<=^{parent}_)[a-zA-Z0-9\s]+'

def parse_files(panel, panel_folder, png_files, py_files):
    """ This is the primary parser.
    It's responsible for transforming a list of files into RibbonButton
    instances.

    returns: [PushButton, PushButton, PullDown, etc.]

    Args needs to be cleanned up.
    #TODO: Cleanup/Optimize file parser.
    """
    ribbon_buttons = []

    for png_file in png_files:

        ################
        # PUSH BUTTONS #
        ################
        if PushButton.identifier in png_file.lower():
            logger.debug('[{}] > PushButton'.format(png_file))
            pattern = pattern_button_type.format(id=PushButton.identifier)
            cmd_name = re.search(pattern, png_file, flags=re.IGNORECASE)
            if not cmd_name:
                logger.warning('Could not parse class in: {}'.format(png_file))
                continue
            cmd_name = cmd_name.group()
            matching_py_files = filter_filelist_by_name(py_files, cmd_name)
            if matching_py_files:
                py_file = matching_py_files[0]  # Just returning the first
                py_filepath = path.join(panel_folder, py_file)
                png_filepath = path.join(panel_folder, png_file)

                # Create Command and Push Button
                command = Command(panel=panel, cmd_name=cmd_name, py_filepath=
                                  py_filepath)
                ribbon_button = PushButton(panel=panel, command=command,
                                           png_path=png_filepath)
                ribbon_buttons.append(ribbon_button)
                continue

        if 'RELOAD' in png_file:
            cmd_name = "ReloadScripts"
            png_filepath = path.join(panel_folder, png_file)
            loader = LOADER
            command = Command(panel=panel, cmd_name=cmd_name, py_filepath=
                              loader)
            ribbon_button = PushButton(panel=panel, command=command,
                                           png_path=png_filepath)
            ribbon_buttons.append(ribbon_button)
            continue

        ####################
        # PULLDOWN BUTTONS #
        ####################
        #TODO: Add icon to push in pull down
        if PullDown.identifier in png_file.lower():
            logger.debug('[{}] > Pulldown'.format(png_file))
            pattern = pattern_button_type.format(id=PullDown.identifier)
            cmd_name = re.search(pattern, png_file, flags=re.IGNORECASE)
            if not cmd_name:
                logger.warning('Could not parse class in: {}'.format(png_file))
                continue
            cmd_name = cmd_name.group()
            matching_py_files = filter_filelist_by_name(py_files, cmd_name)

            # Found py files that match pulldown class name

            if matching_py_files:
                # logger.debug('Processing match files for pulldown: {}'.format(
                                                            # matching_py_files))
                pd_py_files = matching_py_files
                png_filepath = path.join(panel_folder, png_file)

                pulldown_button = PullDown(panel=panel, cmd_name=cmd_name,
                                           png_path=png_filepath)
                for pd_py_file in pd_py_files:
                    pattern = pattern_cmd_name.format(parent=cmd_name)
                    pd_cmd_name = re.search(pattern, pd_py_file,
                                            flags=re.IGNORECASE)
                    if not pd_cmd_name:
                        logger.warning('Could not parse class in: {}'.format(
                                                                    png_file))
                        logger.degug(cmd_name)
                        logger.degug(pd_py_file)
                        continue

                    pd_cmd_name = pd_cmd_name.group()
                    # See if there is a matching png
                    matching_png = pd_py_file.replace('.py', '.png')
                    if matching_png in png_files:
                        pd_png_filepath = path.join(panel_folder, matching_png)
                        logger.debug('Found Matching Pulldown icon')
                    else:
                        pd_png_filepath = png_filepath

                    # Add pulldown parent to push button cmd_name to avoid clash
                    pd_cmd_name = '{}_{}'.format(cmd_name, pd_cmd_name)
                    pd_py_filepath = path.join(panel_folder, pd_py_file)

                    command = Command(panel=panel, cmd_name=pd_cmd_name,
                                      py_filepath=pd_py_filepath)
                    push_down = PushButton(panel=panel, command=command,
                                           png_path=pd_png_filepath,
                                           pulldown_parent=pulldown_button)
                    pulldown_button.push_buttons.append(push_down)
                ribbon_buttons.append(pulldown_button)

        # if PullDown.identifier in png_file.lower():
    return ribbon_buttons

def filter_filelist_by_name(filelist, cmd_name):
    """Returns list of files that match provided pattern.
    Usage:
    filelist = ['fruit_banana,py', 'fruit_apple.py','nothing.py']
    matching_files = filter_filelist_by_name(filelist, 'fruit')
    returns: ['fruit_banana,py', 'fruit_apple.py']
    cmd_name only matches if it's on the begginging of the file name.
    ie: 'something_fruit_banana' would not match

    """
    matching_files = []
    for filename in filelist:
        pattern = pattern_cmd_name.format(parent=cmd_name)
        match = re.search(pattern, filename, flags=re.IGNORECASE)
        if match:
            matching_files.append(filename)

    if len(matching_files) > 1:
        logger.debug('Matched more than one for cmd: {}'.format(cmd_name))
    if matching_files:  # One or more have been found - returns just one
        logger.debug('Found matching pyfiles.')
        # logger.debug('Found matching pyfiles: {}'.format(matching_files))
        return matching_files
    else:
        logger.warning('No matching script for: {}'.format(cmd_name))
        logger.debug('Filelist: {}'.format(str(filelist)))
        logger.debug('cmd_name: {}'.format(str(cmd_name)))


def print_parsed_ribbon(ribbon):
    """ Prints a text version of the parsed directory for debugging purpose.
    Usage:
    print_parsed_ribbon(Ribbon())
    Prints:
    =========================================================================
    <RIBBON: tabs:['pyWeWork']>
    =========================================================================
    + <TAB: pyWeWork>
    ++ <PANEL: WWRoomBootstrap>
    +++ <PUSHBUTTON: RoomBootstrap>
    ++ <PANEL: pyWeWork>
    +++ <PULLDOWN: pyWeWork>
    ++++ <PUSHBUTTON: aboutPyRevit>
    ++++ <PUSHBUTTON: settings>
    ... """
    logger.title('SESSION: ' + str(ribbon))
    for tab in ribbon.tabs.values():
        print('+ ' + str(tab))
        for panel in tab.panels.values():
            print('+ + ' + str(panel))
            for ribbon_button in panel.ribbon_buttons:
                print('+ + + ' + str(ribbon_button))
                if isinstance(ribbon_button, PullDown):
                    for pushbutton in ribbon_button.push_buttons:
                        print('+ + + + ' + str(pushbutton))
