""" Module name = _basecomponents.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
Description:
pyRevit library has 4 main modules for handling parsing, assembly creation, ui, and caching.
This module provides the base component classes that is understood by these four modules.
It is the language the these four modules can understand (_basecomponents module)
 _parser parses the folders and creates a tree of components provided by _basecomponents
 _assemblies make a dll from the tree.
 _ui creates the ui using the information provided by the tree.
 _cache will save and restore the tree to increase loading performance.

This module only uses the base modules (.config, .logger, .exceptions, .output, .utils)
"""

import os.path as op

from .exceptions import PyRevitUnknownFormatError, PyRevitNoScriptFileError, PyRevitScriptDependencyError
from .logger import logger
from .config import PACKAGE_POSTFIX, TAB_POSTFIX, PANEL_POSTFIX, LINK_BUTTON_POSTFIX, PUSH_BUTTON_POSTFIX,             \
                    TOGGLE_BUTTON_POSTFIX, PULLDOWN_BUTTON_POSTFIX, STACKTHREE_BUTTON_POSTFIX, STACKTWO_BUTTON_POSTFIX,\
                    SPLIT_BUTTON_POSTFIX, SPLITPUSH_BUTTON_POSTFIX
from .config import DEFAULT_ICON_FILE, DEFAULT_SCRIPT_FILE, DEFAULT_ON_ICON_FILE, DEFAULT_OFF_ICON_FILE,               \
                    DEFAULT_LAYOUT_FILE_NAME
from .config import DOCSTRING_PARAM, AUTHOR_PARAM, COMPONENT_LIB_NAME, MIN_REVIT_VERSION_PARAM,                        \
                    MIN_PYREVIT_VERSION_PARAM
from .config import REVIT_VERSION, SESSION_STAMPED_ID, PyRevitVersion
from .utils import ScriptFileContents, cleanup_string

from .usersettings import user_settings


# tree branch classes (package, tab, panel) ----------------------------------------------------------------------------
# superclass for all tree branches that contain sub-branches
class GenericContainer(object):
    """

    """

    type_id = ''

    def __init__(self, branch_dir):
        self.directory = branch_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.original_name = self._get_name()
        self.name = user_settings.get_alias(self.original_name)

        self.unique_name = self._get_unique_name()

        self.library_path = self._get_library()

        self._sub_components = []

        self.layout = self._read_layout_file()

    @staticmethod
    def is_group():
        return True

    def _is_valid_dir(self):
        return self.directory.endswith(self.type_id)

    def __iter__(self):
        self._layout_components()
        return iter(self._sub_components)

    def __repr__(self):
        return 'Name: {} Directory: {}'.format(self.original_name, self.directory)

    def _get_name(self):
        return op.splitext(op.basename(self.directory))[0]

    def _get_library(self):
        return op.join(self.directory, COMPONENT_LIB_NAME)

    def _get_unique_name(self):
        """Creates a unique name for the container. This is used to uniquely identify this container and also
        to create the dll assembly. Current method create a unique name based on the full directory address.
        Example:
            self.direcotry = '/pyRevit.package/pyRevit.tab/Edit.panel'
            unique name = pyRevitpyRevitEdit
        """
        uname = ''
        dir_str = self.directory
        for dname in dir_str.split(op.sep):
            name, ext = op.splitext(dname)
            if ext != '':
                uname += name
            else:
                continue
        return cleanup_string(uname)

    def _verify_file(self, file_name):
        return file_name if op.exists(op.join(self.directory, file_name)) else None

    def _read_layout_file(self):
        if self._verify_file(DEFAULT_LAYOUT_FILE_NAME):
            layout_file = open(op.join(self.directory, DEFAULT_LAYOUT_FILE_NAME), 'r')
            return layout_file.readlines()

    def _layout_components(self):
        # todo
        pass

    def add_component(self, comp):
        self._sub_components.append(comp)

    def get_components(self):
        return self._sub_components


# root class for each package. might contain multiple tabs
class Package(GenericContainer):
    type_id = PACKAGE_POSTFIX

    def __init__(self, package_dir):
        GenericContainer.__init__(self, package_dir)
        self.author = None
        self.version = None

    def get_all_commands(self):
        all_cmds = []
        for tab in self:
            for panel in tab:
                for item in panel:
                    if item.is_group():
                        for sub_item in item:
                            all_cmds.append(sub_item)
                    else:
                        all_cmds.append(item)

        return all_cmds


# class for each tab. might contain multiple panels
class Tab(GenericContainer):
    type_id = TAB_POSTFIX

    def __init__(self, tab_dir):
        GenericContainer.__init__(self, tab_dir)

    def has_commands(self):
        # todo
        return True


# class for each panel. might contain commands or command groups
class Panel(GenericContainer):
    type_id = PANEL_POSTFIX

    def __init__(self, panel_dir):
        GenericContainer.__init__(self, panel_dir)

    def get_commands(self):
        return [x for x in self._sub_components if isinstance(x, GenericCommand)]

    def get_command_groups(self):
        return [x for x in self._sub_components if isinstance(x, GenericCommandGroup)]


# command group classes (puu down, split, split pull down, stack2 and stack3) ------------------------------------------
# superclass for all groups of commands.
class GenericCommandGroup(GenericContainer):
    """

    """

    type_id = ''

    def __init__(self, group_dir):
        GenericContainer.__init__(self, group_dir)

        self.icon_file = self._verify_file(DEFAULT_ICON_FILE)
        logger.debug('Command group {}: Icon file is: {}'.format(self.original_name, self.icon_file))


class PullDownButtonGroup(GenericCommandGroup):
    type_id = PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericCommandGroup):
    type_id = SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericCommandGroup):
    type_id = SPLIT_BUTTON_POSTFIX


class StackThreeButtonGroup(GenericCommandGroup):
    type_id = STACKTHREE_BUTTON_POSTFIX


class StackTwoButtonGroup(GenericCommandGroup):
    type_id = STACKTWO_BUTTON_POSTFIX


# single command classes (link, push button, toggle button) ------------------------------------------------------------
class GenericCommand(object):
    """Superclass for all single commands.
    The information provided by these classes will be used to create a
    push button under Revit UI. However, pyRevit expands the capabilities of push button beyond what is provided by
    Revit UI. (e.g. Toggle button changes it's icon based on its on/off status)
    See LinkButton and ToggleButton classes.
    """
    type_id = ''

    def __init__(self, cmd_dir):
        self.directory = cmd_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.original_name = self._get_name()
        self.name = user_settings.get_alias(self.original_name)

        self.icon_file = self._verify_file(DEFAULT_ICON_FILE)
        logger.debug('Command {}: Icon file is: {}'.format(self.original_name, self.icon_file))

        self.script_file = self._verify_file(DEFAULT_SCRIPT_FILE)
        if self.script_file is None:
            logger.error('Command {}: Does not have script file.'.format(self.original_name))
            raise PyRevitNoScriptFileError()

        # reading script file content to extract parameters
        script_content = ScriptFileContents(self.get_full_script_address())

        # extracting min requried Revit and pyRevit versions
        self.min_pyrevit_ver = script_content.extract_param(MIN_PYREVIT_VERSION_PARAM)
        self.min_revit_ver = script_content.extract_param(MIN_REVIT_VERSION_PARAM)
        self._check_dependencies()

        self.doc_string = script_content.extract_param(DOCSTRING_PARAM)
        self.author = script_content.extract_param(AUTHOR_PARAM)

        # setting up a unique name for command. This name is especially useful for creating dll assembly
        self.unique_name = self._get_unique_name()

        # each command can store custom libraries under /Lib inside the command folder
        self.library_path = self._get_library()
        # setting up search paths. These paths will be added to sys.path by the command loader for easy imports.
        self.search_paths = []
        self.search_paths.append(self.library_path)

    @staticmethod
    def is_group():
        return False

    def __repr__(self):
        return 'Type Id: {} Directory: {} Name: {}'.format(self.type_id, self.directory, self.original_name)

    def _is_valid_dir(self):
        return self.directory.endswith(self.type_id)

    def _get_full_file_address(self, file_name):
        return op.join(self.directory, file_name)

    def _get_name(self):
        return op.splitext(op.basename(self.directory))[0]

    def _verify_file(self, file_name):
        return file_name if op.exists(op.join(self.directory, file_name)) else None

    def _get_library(self):
        return op.join(self.directory, COMPONENT_LIB_NAME)

    def _check_dependencies(self):
        # todo
        pass

    def _get_unique_name(self):
        """Creates a unique name for the command. This is used to uniquely identify this command and also
        to create the class in pyRevit dll assembly.
        Current method create a unique name based on the command full directory address.
        Example:
            self.direcotry = '/pyRevit.package/pyRevit.tab/Edit.panel/Flip doors.pushbutton'
            unique name = pyRevitpyRevitEditFlipdoors
        """
        uname = ''
        dir_str = self.directory
        for dname in dir_str.split(op.sep):
            name, ext = op.splitext(dname)
            if ext != '':
                uname += name
            else:
                continue
        return cleanup_string(uname)

    # def _get_clean_dict(self):
    #     return self.__dict__.copy()
    #
    # # todo: how to load from cache?
    # def _load_from_cache(self, cached_dict):
    #     for k,v in cached_dict.items():
    #         self.__dict__[k] = v

    def get_search_paths(self):
        return self.search_paths

    def get_full_script_address(self):
        return op.join(self.directory, self.script_file)

    def append_search_path(self, path):
        self.search_paths.append(path)


class LinkButton(GenericCommand):
    type_id = LINK_BUTTON_POSTFIX

    def __init__(self, cmd_dir):
        GenericCommand.__init__(self, cmd_dir)
        # todo extract assembly and class info


class PushButton(GenericCommand):
    type_id = PUSH_BUTTON_POSTFIX


class ToggleButton(GenericCommand):
    type_id = TOGGLE_BUTTON_POSTFIX

    def __init__(self, cmd_dir):
        GenericCommand.__init__(self, cmd_dir)
        self.icon_on_file = self._verify_file(DEFAULT_ON_ICON_FILE)
        self.icon_off_file = self._verify_file(DEFAULT_OFF_ICON_FILE)
