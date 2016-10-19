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

from .exceptions import PyRevitException
from .logger import logger
from .config import HOME_DIR
from ._basecomponents import Package, Panel, Tab, GenericCommandGroup, GenericCommand
from ._cache import is_cache_valid, get_cached_package, update_cache


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
        cmp_classes = [component_class]

    for file_or_dir in os.listdir(search_dir):
        full_path = op.join(search_dir, file_or_dir)
        # full_path might be a file or a dir, but its name should not start with . or _:
        if not file_or_dir.startswith(('.', '_')):
            for cmp_class in cmp_classes:
                try:
                    # if cmp_class can be created for this sub-dir, the add to list
                    # cmp_class will raise error if full_path is not of cmp_class type.
                    component = cmp_class(full_path)
                    logger.debug('Successfuly created component:\n{}'.format(component))
                    sub_cmp_list.append(component)
                except PyRevitException:
                    logger.debug('Can not create component from:\n{}'.format(full_path))
        else:
            logger.debug('Excluding directories with . or _ in name: {}'.format(full_path))

    return sub_cmp_list


def _create_cmds(search_dir):
    return _create_subcomponents(search_dir, GenericCommand)


def _create_cmd_groups(search_dir):
    return _create_subcomponents(search_dir, GenericCommandGroup)


def _create_panels(search_dir):
    return _create_subcomponents(search_dir, Panel)


def _create_tabs(search_dir):
    return _create_subcomponents(search_dir, Tab)


def _create_pkgs(search_dir):
    return _create_subcomponents(search_dir, Package)


def get_installed_packages():
    """Parses home directory and return a list of Package objects for installed packages.
    Each package object is the root to a tree of components that exists under that package. (e.g. tabs, buttons, ...)
    sub components of package can be accessed from pkg.sub_components list.
    See _basecomponents for types.
    """

    # errors are handled internally by the _create_* functions.
    # component creation errors are not critical. Each component that fails, will simply not be created.
    # all errors will be logged to debug for troubleshooting

    # try creating packages
    pkg_list = []
    for new_pkg in _create_pkgs(HOME_DIR):

        # test if cache is valid for this package
        # it might seem unusual to create a package and then re-load it from cache but minimum information
        # about the package needs to be passed to the cache module for proper hash calculation and package recovery.
        # Also package object is very small and its creation doesn't add much overhead.
        if is_cache_valid(new_pkg):
            # if yes, load the cached package and add the cached tabs to the new package
            for new_tab in get_cached_package(new_pkg).get_components():
                new_pkg.add_component(new_tab)

        # if load from cache failed or cache is obsolete (due to folder changes, new pyRevit version, etc.)
        # parse the folders and create sub-components for the package
        else:
            # try creating tabs for new_pkg
            for new_tab in _create_tabs(new_pkg.directory):
                new_pkg.add_component(new_tab)

                # try creating panels for new_tab
                for new_panel in _create_panels(new_tab.directory):
                    new_tab.add_panel(new_panel)

                    # panels can hold both single commands and command groups
                    # try creating command groups for new_panel
                    for new_cmd_group in _create_cmd_groups(new_panel.directory):
                        new_panel.add_component(new_cmd_group)
                        # try creating commands for new_cmd_gorup
                        for new_cmd in _create_cmds(new_cmd_group.directory):
                            new_cmd_group.add_cmd(new_cmd)

                    # try creating commands for new_panel
                    for new_cmd in _create_cmds(new_panel.directory):
                        new_panel.add_component(new_cmd)

            # update cache with newly parsed package and its components
            update_cache(new_pkg)

        # add the newly parsed package to the return list
        pkg_list.append(new_pkg)

    return pkg_list
