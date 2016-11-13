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

from ..logger import get_logger
logger = get_logger(__name__)

from ..exceptions import PyRevitException
from ..utils import get_all_subclasses, get_sub_folders

from .components import Package


def _create_subcomponents(search_dir, component_types_list):
    """Parses the provided directory and returns a list of objects of the types in component_types_list.
    Arguments:
        search_dir: directory to parse
        component_types_list: This methods checks the subfolders in search_dir against the _get_component types provided
        in this list.
    Example:
        _create_subcomponents(search_dir, [LinkButton, PushButton, or ToggleButton])
        this method creates LinkButton, PushButton, or ToggleButton for the parsed sub-directories under search_dir
        with matching .type_id identifiers in their names. (e.g. "folder.LINK_BUTTON_POSTFIX")
    Returns:
        list of created classes of types provided in component_types_list
    """
    logger.debug('Searching directory: {} for components of type: {}'.format(search_dir, component_types_list))

    sub_cmp_list = []

    for file_or_dir in os.listdir(search_dir):
        full_path = op.join(search_dir, file_or_dir)
        logger.debug('Testing _get_component(s) on: {} '.format(full_path))
        # full_path might be a file or a dir, but its name should not start with . or _:
        if not file_or_dir.startswith(('.', '_')):
            for component_type in component_types_list:
                logger.debug('Testing sub_directory {} for {}'.format(file_or_dir, component_type))
                try:
                    # if cmp_class can be created for this sub-dir, the add to list
                    # cmp_class will raise error if full_path is not of cmp_class type.
                    component = component_type()
                    component.__init_from_dir__(full_path)
                    sub_cmp_list.append(component)
                    logger.debug('Successfuly created component: {} from: {}'.format(component, full_path))
                    break
                except PyRevitException:
                    logger.debug('Can not create component of type: {} from: {}'.format(component_type, full_path))
        else:
            logger.debug('Skipping _get_component. Name can not start with . or _: {}'.format(full_path))

    return sub_cmp_list


def _parse_for_components(component):
    """Recursively parses _get_component.directory for components of type _get_component.allowed_sub_cmps
    This method uses get_all_subclasses() to get a list of all subclasses of _get_component.allowed_sub_cmps type.
    This ensures that if any new type of component_class is added later, this method does not need to be updated as
    the new sub-class will be listed by .__subclasses__() method of the parent class and this method will check
    the directory for its .type_id
    """
    for new_cmp in _create_subcomponents(component.directory, get_all_subclasses(component.allowed_sub_cmps)):
        # add the successfulyl created _get_component to the parent _get_component
        component.add_component(new_cmp)
        if new_cmp.is_container():
            # Recursive part: parse each sub-_get_component for its allowed sub-sub-components.
            _parse_for_components(new_cmp)


def get_parsed_package(pkg):
    """Parses package directory and creates and adds components to the package object
    Each package object is the root to a tree of components that exists under that package. (e.g. tabs, buttons, ...)
    sub components of package can be accessed by iterating the _get_component. See _basecomponents for types.
    """
    _parse_for_components(pkg)

    return pkg


def get_installed_package_data(root_dir):
    """Parses home directory and return a list of Package objects for installed packages.
    The package objects won't be parsed at this level. This function onyl provides the basic info for the installed
    packages so the session can check the cache for each package and decide if they need to be parsed or not.
    """

    # try creating packages in given directory
    pkg_data_list = []

    logger.debug('Parsing directory for packages...')
    for pkg_data in _create_subcomponents(root_dir, [Package]):
        logger.debug('Package directory found: {}'.format(pkg_data))
        pkg_data_list.append(pkg_data)

    return pkg_data_list
