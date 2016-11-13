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

import os
import re
import hashlib
import os.path as op

from ..exceptions import PyRevitUnknownFormatError, PyRevitNoScriptFileError, PyRevitException
from ..logger import logger
from ..config import PACKAGE_POSTFIX, TAB_POSTFIX, PANEL_POSTFIX, LINK_BUTTON_POSTFIX, PUSH_BUTTON_POSTFIX,\
                     TOGGLE_BUTTON_POSTFIX, PULLDOWN_BUTTON_POSTFIX, STACKTHREE_BUTTON_POSTFIX,\
                     STACKTWO_BUTTON_POSTFIX, SPLIT_BUTTON_POSTFIX, SPLITPUSH_BUTTON_POSTFIX,\
                     SEPARATOR_IDENTIFIER, SLIDEOUT_IDENTIFIER
from ..config import DEFAULT_SYS_PATHS, COMP_LIBRARY_DIR_NAME
from ..config import DEFAULT_ICON_FILE, DEFAULT_SCRIPT_FILE, DEFAULT_ON_ICON_FILE, DEFAULT_OFF_ICON_FILE,\
                     DEFAULT_LAYOUT_FILE_NAME, SCRIPT_FILE_FORMAT, DEFAULT_CONFIG_SCRIPT_FILE
from ..config import DOCSTRING_PARAM, AUTHOR_PARAM, MIN_REVIT_VERSION_PARAM,\
                     MIN_PYREVIT_VERSION_PARAM, COMMAND_OPTIONS_PARAM
from ..config import PyRevitVersion, HostVersion
from ..utils import ScriptFileParser, cleanup_string

from ..userconfig import user_settings


# superclass for all tree branches that contain sub-branches (containers)
class GenericContainer(object):
    """

    """

    type_id = ''
    allowed_sub_cmps = []

    def __init__(self):
        self._sub_components = []

        self.directory = None
        self.original_name = self.name = None
        self.unique_name = None
        self.library_path = None
        self.syspath_search_paths = []
        self.layout_list = None
        self.icon_file = None

    def __init_from_dir__(self, branch_dir):
        self._sub_components = []

        self.directory = branch_dir
        if not self.directory.endswith(self.type_id):
            raise PyRevitUnknownFormatError()

        self.original_name = op.splitext(op.basename(self.directory))[0]
        self.name = user_settings.get_alias(self.original_name, self.type_id)
        if self.name != self.original_name:
            logger.debug('Alias name is: {}'.format(self.name))
        self.unique_name = self._get_unique_name()

        # each container can store custom libraries under /Lib inside the container folder
        lib_path = op.join(self.directory, COMP_LIBRARY_DIR_NAME)
        self.library_path = lib_path if op.exists(lib_path) else None

        # setting up search paths. These paths will be added to all sub-components of this component.
        if self.library_path:
            self.syspath_search_paths.append(self.library_path)

        self.layout_list = self._read_layout_file()
        logger.debug('Layout is: {}'.format(self.layout_list))

        full_file_path = op.join(self.directory, DEFAULT_ICON_FILE)
        self.icon_file = full_file_path if op.exists(full_file_path) else None
        if self.icon_file:
            logger.debug('Icon file is: {}'.format(self.original_name, self.icon_file))

    @staticmethod
    def is_container():
        return True

    def __iter__(self):
        return iter(self._get_components_per_layout())

    def __repr__(self):
        return 'Name: {} Directory: {}'.format(self.original_name, self.directory)

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

    def _read_layout_file(self):
        full_file_path = op.join(self.directory, DEFAULT_LAYOUT_FILE_NAME)
        if op.exists(full_file_path):
            layout_file = open(op.join(self.directory, DEFAULT_LAYOUT_FILE_NAME), 'r')
            # return [x.replace('\n', '') for x in layout_file.readlines()]
            return layout_file.read().splitlines()
        else:
            logger.debug('Container does not have layout file defined: {}'.format(self))

    def _get_components_per_layout(self):
        # if item is not listed in layout, it will not be created
        if self.layout_list and self._sub_components:
            logger.debug('Reordering components per layout file...')
            layout_index = 0
            _processed_cmps = []
            for layout_item in self.layout_list:
                for cmp_index, component in enumerate(self._sub_components):
                    if component.original_name == layout_item:
                        _processed_cmps.append(component)
                        layout_index += 1
                        break

            # insert separators and slideouts per layout definition
            logger.debug('Adding separators and slide outs per layout...')
            for i_index, layout_item in enumerate(self.layout_list):
                if SEPARATOR_IDENTIFIER in layout_item:
                    _processed_cmps.insert(i_index, GenericSeparator())
                elif SLIDEOUT_IDENTIFIER in layout_item:
                    _processed_cmps.insert(i_index, GenericSlideout())

            logger.debug('Reordered sub_component list is: {}'.format(_processed_cmps))
            return _processed_cmps
        else:
            return self._sub_components

    def get_cache_data(self):
        cache_dict = self.__dict__.copy()
        cache_dict['type_id'] = self.type_id
        return cache_dict

    def load_cache_data(self, cache_dict):
        for k, v in cache_dict.items():
            self.__dict__[k] = v

    def add_component(self, comp):
        if self.syspath_search_paths:
            comp.syspath_search_paths.extend(self.syspath_search_paths)
        self._sub_components.append(comp)

    def get_components(self):
        return self._sub_components


# superclass for all single command classes (link, push button, toggle button) -----------------------------------------
# GenericCommand is not derived from GenericContainer since a command can not contain other elements
class GenericCommand(object):
    """Superclass for all single commands.
    The information provided by these classes will be used to create a
    push button under Revit UI. However, pyRevit expands the capabilities of push button beyond what is provided by
    Revit UI. (e.g. Toggle button changes it's icon based on its on/off status)
    See LinkButton and ToggleButton classes.
    """
    type_id = ''

    def __init__(self):
        self.directory = None
        self.original_name = self.name = None
        self.icon_file = self.script_file = self.config_script_file = None
        self.min_pyrevit_ver = self.min_revit_ver = None
        self.doc_string = self.author = self.cmd_options = None
        self.unique_name = None
        self.library_path = self.search_paths = None
        self.syspath_search_paths = []

    def __init_from_dir__(self, cmd_dir):
        self.directory = cmd_dir
        if not self.directory.endswith(self.type_id):
            raise PyRevitUnknownFormatError()

        self.original_name = op.splitext(op.basename(self.directory))[0]
        self.name = user_settings.get_alias(self.original_name, self.type_id)
        if self.name != self.original_name:
            logger.debug('Alias name is: {}'.format(self.name))

        full_file_path = op.join(self.directory, DEFAULT_ICON_FILE)
        self.icon_file = full_file_path if op.exists(full_file_path) else None
        logger.debug('Command {}: Icon file is: {}'.format(self, self.icon_file))

        full_file_path = op.join(self.directory, DEFAULT_SCRIPT_FILE)
        self.script_file = full_file_path if op.exists(full_file_path) else None
        if self.script_file is None:
            logger.error('Command {}: Does not have script file.'.format(self))
            raise PyRevitNoScriptFileError()

        full_file_path = op.join(self.directory, DEFAULT_CONFIG_SCRIPT_FILE)
        self.config_script_file = full_file_path if op.exists(full_file_path) else None
        if self.config_script_file is None:
            logger.debug('Command {}: Does not have independent config script.'.format(self))
            self.config_script_file = self.script_file

        try:
            # reading script file content to extract parameters
            script_content = ScriptFileParser(self.get_full_script_address())
            # extracting min requried Revit and pyRevit versions
            self.min_pyrevit_ver = script_content.extract_param(MIN_PYREVIT_VERSION_PARAM)  # type: tuple
            self.min_revit_ver = script_content.extract_param(MIN_REVIT_VERSION_PARAM)  # type: str
            self.doc_string = script_content.extract_param(DOCSTRING_PARAM)  # type: str
            self.author = script_content.extract_param(AUTHOR_PARAM)  # type: str
            self.cmd_options = script_content.extract_param(COMMAND_OPTIONS_PARAM)  # type: list
        except PyRevitException as err:
            logger.error(err)

        # fixme: logger reports module as 'ast' after a successfull param retrieval. Must be ast.literal_eval()
        logger.debug('Minimum pyRevit version: {}'.format(self.min_pyrevit_ver))
        logger.debug('Minimum host version: {}'.format(self.min_revit_ver))
        logger.debug('command tooltip: {}'.format(self.doc_string))
        logger.debug('Command author: {}'.format(self.author))
        logger.debug('Command options: {}'.format(self.cmd_options))

        try:
            # check minimum requirements
            self._check_dependencies()
        except PyRevitException as err:
            logger.warning(err)
            raise err

        # setting up a unique name for command. This name is especially useful for creating dll assembly
        self.unique_name = self._get_unique_name()

        # each command can store custom libraries under /Lib inside the command folder
        lib_path = op.join(self.directory, COMP_LIBRARY_DIR_NAME)
        self.library_path = lib_path if op.exists(lib_path) else None

        # setting up search paths. These paths will be added to sys.path by the command loader for easy imports.
        if self.library_path:
            self.syspath_search_paths.append(self.library_path)

    @staticmethod
    def is_container():
        return False

    def __repr__(self):
        return 'Type Id: {} Directory: {} Name: {}'.format(self.type_id, self.directory, self.original_name)

    def _check_dependencies(self):
        if self.min_revit_ver and HostVersion.is_older_than(self.min_revit_ver):
            raise PyRevitException('Command requires a newer host version ({}): {}'.format(self.min_revit_ver,
                                                                                           self))
        elif self.min_pyrevit_ver and PyRevitVersion.is_older_than(self.min_pyrevit_ver):
            raise PyRevitException('Command requires a newer pyrevit version ({}): {}'.format(self.min_pyrevit_ver,
                                                                                              self))

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

    @staticmethod
    def is_valid_cmd():
        return True

    def get_cache_data(self):
        cache_dict = self.__dict__.copy()
        cache_dict['type_id'] = self.type_id
        return cache_dict

    def load_cache_data(self, cache_dict):
        for k, v in cache_dict.items():
            self.__dict__[k] = v

    def has_config_script(self):
        return self.config_script_file != self.script_file

    def get_search_paths(self):
        return self.syspath_search_paths

    def get_cmd_options(self):
        return self.cmd_options

    def get_full_script_address(self):
        return op.join(self.directory, self.script_file)

    def get_full_config_script_address(self):
        return op.join(self.directory, self.config_script_file)

    def append_search_path(self, path):
        self.search_paths.append(path)


# Derived classes here correspond to similar elements in Revit ui. Under Revit UI:
# Packages contain Tabs, Tabs contain, Panels, Panels contain Stacks, Commands, or Command groups
# ----------------------------------------------------------------------------------------------------------------------
class LinkButton(GenericCommand):
    type_id = LINK_BUTTON_POSTFIX

    def __init__(self):
        GenericCommand.__init__(self)
        self.assembly = self.command_class = None

    def __init_from_dir__(self, cmd_dir):
        GenericCommand.__init_from_dir__(self, cmd_dir)
        # todo extract assembly and class info
        self.assembly = self.command_class = None


class PushButton(GenericCommand):
    type_id = PUSH_BUTTON_POSTFIX


class ToggleButton(GenericCommand):
    type_id = TOGGLE_BUTTON_POSTFIX

    def __init__(self):
        GenericCommand.__init__(self)
        self.icon_on_file = self.icon_off_file = None

    def __init_from_dir__(self, cmd_dir):
        GenericCommand.__init_from_dir__(self, cmd_dir)

        full_file_path = op.join(self.directory, DEFAULT_ON_ICON_FILE)
        self.icon_on_file = full_file_path if op.exists(full_file_path) else None

        full_file_path = op.join(self.directory, DEFAULT_OFF_ICON_FILE)
        self.icon_off_file = full_file_path if op.exists(full_file_path) else None


# # Command groups only include commands. these classes can include GenericCommand as sub components
class GenericCommandGroup(GenericContainer):
    allowed_sub_cmps = [GenericCommand]

    def has_commands(self):
        for component in self:
            if component.is_valid_cmd():
                return True


class PullDownButtonGroup(GenericCommandGroup):
    type_id = PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericCommandGroup):
    type_id = SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericCommandGroup):
    type_id = SPLIT_BUTTON_POSTFIX


# Stacks include GenericCommand, or GenericCommandGroup
class GenericStack(GenericContainer):
    allowed_sub_cmps = [GenericCommandGroup, GenericCommand]

    def has_commands(self):
        for component in self:
            if not component.is_container():
                if component.is_valid_cmd():
                    return True
            else:
                if component.has_commands():
                    return True


class StackThreeButtonGroup(GenericStack):
    type_id = STACKTHREE_BUTTON_POSTFIX


class StackTwoButtonGroup(GenericStack):
    type_id = STACKTWO_BUTTON_POSTFIX


# Panels include GenericStack, GenericCommand, or GenericCommandGroup
class Panel(GenericContainer):
    type_id = PANEL_POSTFIX
    allowed_sub_cmps = [GenericStack, GenericCommandGroup, GenericCommand]

    def has_commands(self):
        for component in self:
            if not component.is_container():
                if component.is_valid_cmd():
                    return True
            else:
                if component.has_commands():
                    return True


# Tabs include Panels
class Tab(GenericContainer):
    type_id = TAB_POSTFIX
    allowed_sub_cmps = [Panel]

    def has_commands(self):
        for panel in self:
            if panel.has_commands():
                return True
        return False


class Package(GenericContainer):
    type_id = PACKAGE_POSTFIX
    allowed_sub_cmps = [Tab]

    def __init__(self):
        GenericContainer.__init__(self)
        self.author = None
        self.version = None
        self.hash_value = self.hash_version = None

    def __init_from_dir__(self, package_dir):
        GenericContainer.__init_from_dir__(self, package_dir)
        self.hash_value = self._calculate_hash()
        self.hash_version = PyRevitVersion.full_version_as_str()

    def _calculate_hash(self):
        """Creates a unique hash # to represent state of directory."""
        # logger.info('Generating Hash of directory')
        # search does not include png files:
        #   if png files are added the parent folder mtime gets affected
        #   cache only saves the png address and not the contents so they'll get loaded everytime
        #       see http://stackoverflow.com/a/5141710/2350244
        pat = '(\\' + TAB_POSTFIX + ')|(\\' + PANEL_POSTFIX + ')'
        patfile = '(\\' + SCRIPT_FILE_FORMAT + ')'
        mtime_sum = 0
        for root, dirs, files in os.walk(self.directory):
            if re.search(pat, root, flags=re.IGNORECASE):
                mtime_sum += op.getmtime(root)
                for filename in files:
                    if re.search(patfile, filename, flags=re.IGNORECASE):
                        modtime = op.getmtime(op.join(root, filename))
                        mtime_sum += modtime
        return hashlib.md5(str(mtime_sum)).hexdigest()


# Misc UI Classes
# ----------------------------------------------------------------------------------------------------------------------
class GenericSeparator:
    type_id = SEPARATOR_IDENTIFIER

    def __init__(self):
        self.name = SEPARATOR_IDENTIFIER

    @staticmethod
    def is_container():
        return False


class GenericSlideout:
    type_id = SLIDEOUT_IDENTIFIER

    def __init__(self):
        self.name = SLIDEOUT_IDENTIFIER

    @staticmethod
    def is_container():
        return False
