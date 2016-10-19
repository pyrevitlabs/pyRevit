""" Module name = _parser.py
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
This is the module responsible for parsing folders and creating components (Buttons, Tabs, ...)
The assembly, ui, and cache module will later use this information to to their job.

All these four modules are private and handled by pyRevit.session
These modules do not import each other and mainly use base modules (.config, .logger, .exceptions, .output, .utils)
All these four modules can understand the component tree. (_basecomponents module)
 _parser parses the folders and creates a tree of components provided by _basecomponents
 _assemblies make a dll from the tree.
 _ui creates the ui using the information provided by the tree.
 _cache will save and restore the tree to increase loading performance.
"""

import os
import os.path as op

from .exceptions import PyRevitUnknownFormatError
# todo add debug messages
from .logger import logger
from .config import HOME_DIR
from ._basecomponents import Package, Panel, Tab, GenericCommandGroup, GenericCommand
# todo implement cache
from ._cache import is_cache_valid, get_cached_package, update_cache


def _get_sub_dirs(parent_dir):
    # todo revise to return directories only?
    logger.debug('Listing directories for {}'.format(parent_dir))
    return os.listdir(parent_dir)


def _create_subcomponents(search_dir, component_class):
    """Parses the provided directory and returns a list of objects of the type component_class.
    Arguments:
        search_dir: directory to parse
        component_class: If a subfolder name ends with component_class.type_id, (or .type_id of any sub-class)
         this method creates an object of type component_class and adds to the list to be returned.
        This ensures that if any new type of component_class is added later, this method does not need to be updated as
         the new sub-class will be listed by .__subclasses__() method of the parent class and this method will check
         the directory for its .type_id
    Example:
        _create_subcomponents(search_dir, GenericCommand)
        GenericCommand.__subclasses__() will return [LinkButton, PushButton, or ToggleButton] and thus
        this method creates LinkButton, PushButton, or ToggleButton for the parsed sub-directories under search_dir
        with matching .type_id identifiers in their names. (e.g. "folder.LINK_BUTTON_POSTFIX")
    Returns:
        list of created classes of type component_class or sub-classes of component_class
    """
    sub_cmp_list = []

    # if super-class, get a list of sub-classes. Otherwise use component_class to create objects.
    try:
        cmp_classes = component_class.__subclasses__()
    except AttributeError:
        cmp_classes = list(component_class)

    for dirname in os.listdir(search_dir):
        full_path = op.join(search_dir, dirname)
        # full_path is a dir, its name does not start with . or _:
        if op.isdir(full_path) and not dirname.startswith(('.', '_')):
            for cmp_class in cmp_classes:
                try:
                    # if cmp_class can be created for this sub-dir, the add to list
                    # cmp_class will raise error if full_path is not of cmp_class type.
                    cmp = cmp_class(full_path)
                    sub_cmp_list.append(cmp)
                    logger.debug('Successfuly created component of type {}\nfrom: {}'.format(cmp.type_id, full_path))
                except PyRevitUnknownFormatError:
                    logger.debug('Can not create component from: {}'.format(full_path))
                    # cmp_class can not init with full_path, try next class
                    continue
                # todo: log skipping over dirs that dont match anthing

    return sub_cmp_list


def _create_cmds(search_dir):
    return _create_subcomponents(search_dir, GenericCommand)


def _create_cmd_groups(search_dir):
    return _create_subcomponents(search_dir, GenericCommandGroup)


def _create_panels(search_dir):
    return _create_subcomponents(search_dir, Panel)


def _create_tabs(search_dir):
    return _create_subcomponents(search_dir, Tab)


def _create_pkg(search_dir):
    return _create_subcomponents(search_dir, Package)


def get_installed_packages():
    """Parses home directory and return a list of Package objects for installed packages."""
    pkgs = []
    for dirname in _get_sub_dirs(HOME_DIR):
        full_path = op.join(HOME_DIR, dirname)
        logger.debug('Parsing {}'.format(full_path))
        try:
            # try creating a package
            new_pkg = _create_pkg(full_path)

            # try creating tabs for new_pkg
            for new_tab in _create_tabs(new_pkg.directory):
                new_pkg.add_component(new_tab)
                # todo: try reading tab from cache before parsing for it
                # try creating panels for new_tab
                for new_panel in _create_panels(new_tab.directory):
                    new_tab.add_panel(new_panel)
                    # panles can hold both single commands and command groups
                    # try creating command groups for new_panel
                    for new_cmd_group in _create_cmd_groups(new_panel.directory):
                        new_panel.add_component(new_cmd_group)
                        # try creating commands for new_cmd_gorup
                        for new_cmd in _create_cmds(new_cmd_group.directory):
                            new_cmd_group.add_cmd(new_cmd)
                    # try creating commands for new_panel
                    for new_cmd in _create_cmds(new_panel.directory):
                        new_panel.add_component(new_cmd)

            pkgs.append(new_pkg)

        except PyRevitUnknownFormatError:
            logger.debug('Directory: {}\nis not a package.'.format(full_path))
            pass

    return pkgs
