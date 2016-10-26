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
from ._logger import logger
from ._basecomponents import Package, Panel, Tab, GenericStack, GenericCommandGroup, GenericCommand
from .utils import get_all_subclasses


def _create_subcomponents(search_dir, *cmp_classes):
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
    component_types = get_all_subclasses(cmp_classes)

    logger.debug('Searching directory: {} for components of type: {}'.format(search_dir, component_types))

    sub_cmp_list = []

    for file_or_dir in os.listdir(search_dir):
        full_path = op.join(search_dir, file_or_dir)
        logger.debug('Testing component(s) on: {} '.format(full_path))
        # full_path might be a file or a dir, but its name should not start with . or _:
        if not file_or_dir.startswith(('.', '_')):
            for component_type in component_types:
                logger.debug('Testing sub_directory for {}'.format(component_type))
                try:
                    # if cmp_class can be created for this sub-dir, the add to list
                    # cmp_class will raise error if full_path is not of cmp_class type.
                    component = component_type(full_path)
                    sub_cmp_list.append(component)
                    logger.debug('Successfuly created component: {} from: {}'.format(component_type, full_path))
                    break
                except PyRevitException:
                    logger.debug('Can not create component: {} from: {}'.format(component_type, full_path))
        else:
            logger.debug('Skipping component. Name can not start with . or _: {}'.format(full_path))

    return sub_cmp_list


def _create_buttons(search_dir):
    return _create_subcomponents(search_dir, GenericCommand)


def _create_stack_items(search_dir):
    return _create_subcomponents(search_dir, GenericCommandGroup, GenericCommand)


def _create_ribbon_items(search_dir):
    return _create_subcomponents(search_dir, GenericStack, GenericCommandGroup, GenericCommand)


def _create_panels(search_dir):
    return _create_subcomponents(search_dir, Panel)


def _create_tabs(search_dir):
    return _create_subcomponents(search_dir, Tab)


def _create_pkgs(search_dir):
    return _create_subcomponents(search_dir, Package)


def _get_parsed_package(pkg):
    """Parses package directory and creates and adds components to the package object
    Each package object is the root to a tree of components that exists under that package. (e.g. tabs, buttons, ...)
    sub components of package can be accessed from pkg.sub_components list.
    See _basecomponents for types.
    """

    # errors are handled internally by the _create_* functions.
    # component creation errors are not critical. Each component that fails, will simply not be created.
    # all errors will be logged to debug for troubleshooting

    # todo explain deterministic search for pks, tabs and panels, stacks, command groups and commands

    # try creating tabs for new_pkg
    logger.debug('Parsing package for tabs...')
    for new_tab in _create_tabs(pkg.directory):
        pkg.add_component(new_tab)
        logger.debug('Tab added: {}'.format(new_tab))

        # try creating panels for new_tab
        logger.debug('Parsing tab for panels...')
        for new_panel in _create_panels(new_tab.directory):
            new_tab.add_component(new_panel)
            logger.debug('Panel added: {}'.format(new_panel))

            # try creating ribbon items for new_panel
            logger.debug('Parsing panel for ribbon items...')
            for ribbon_item in _create_ribbon_items(new_panel.directory):
                new_panel.add_component(ribbon_item)
                logger.debug('Ribbon item added: {}'.format(ribbon_item))

                # Panels can contain stacks, button groups and buttons.
                # if ribbon_item is a stack, parse its folder for button groups and buttons
                if isinstance(ribbon_item, GenericStack):
                    logger.debug('Parsing stack for buttons and button groups...')
                    for stack_item in _create_stack_items(ribbon_item.directory):
                        ribbon_item.add_component(stack_item)
                        logger.debug('Stack item added: {}'.format(stack_item))

                        # Stacks can contain either button groups or buttons
                        # if stack_item is a button group, parse its folder for buttons
                        if isinstance(stack_item, GenericCommandGroup):
                            logger.debug('Parsing button group for buttons...')
                            for button in _create_buttons(stack_item.directory):
                                stack_item.add_component(button)
                                logger.debug('Button added: {}'.format(button))

                # if ribbon_item is a button group, parse its folder for buttons
                elif isinstance(ribbon_item, GenericCommandGroup):
                    logger.debug('Parsing button group for buttons...')
                    for button in _create_buttons(ribbon_item.directory):
                        ribbon_item.add_component(button)
                        logger.debug('Button added: {}'.format(button))

    return pkg


def _get_installed_packages(root_dir):
    """Parses home directory and return a list of Package objects for installed packages."""

    # try creating packages in given directory
    pkg_list = []

    logger.debug('Parsing directory for packages...')
    for new_pkg in _create_pkgs(root_dir):
        logger.debug('Package directory found: {}'.format(new_pkg))
        pkg_list.append(new_pkg)

    return pkg_list
