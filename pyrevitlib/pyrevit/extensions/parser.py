"""Base module for parsing extensions."""
import os
import os.path as op

from pyrevit.coreutils import get_all_subclasses
from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def _get_discovered_comps(comp_path, cmp_types_list):
    discovered_cmps = []
    mlogger.debug('Testing _get_component(s) on: %s ', comp_path)
    # comp_path might be a file or a dir,
    # but its name should not start with . or _:
    for cmp_type in cmp_types_list:
        mlogger.debug('Testing sub_directory %s for %s', comp_path, cmp_type)
        # if cmp_class can be created for this sub-dir, the add to list
        if cmp_type.matches(comp_path):
            component = cmp_type(cmp_path=comp_path)
            discovered_cmps.append(component)
            mlogger.debug('Successfuly created component: %s from: %s',
                          component, comp_path)

    return discovered_cmps


def _create_subcomponents(search_dir,
                          cmp_types_list,
                          create_from_search_dir=False):
    """Returns the objects in search_dir of the types in cmp_types_list.

    Arguments:
        search_dir (str): directory to parse
        cmp_types_list: This methods checks the subfolders in search_dir
            against the _get_component types provided in this list.
        create_from_search_dir (bool, optional): whether to create the _get_component objects, default to False

    Examples:
        ```python
        _create_subcomponents(search_dir,
                              [LinkButton, PushButton, or ToggleButton])
        ```
        this method creates LinkButton, PushButton, or ToggleButton for
        the parsed sub-directories under search_dir with matching .type_id
        identifiers in their names. (e.g. "folder.LINK_BUTTON_POSTFIX")

    Returns:
        list of created classes of types provided in cmp_types_list
    """
    sub_cmp_list = []

    if not create_from_search_dir:
        mlogger.debug('Searching directory: %s for components of type: %s',
                      search_dir, cmp_types_list)
        for file_or_dir in os.listdir(search_dir):
            full_path = op.join(search_dir, file_or_dir)
            if not file_or_dir.startswith(('.', '_')):
                sub_cmp_list.extend(_get_discovered_comps(full_path,
                                                          cmp_types_list))
            else:
                mlogger.debug('Skipping _get_component. '
                              'Name can not start with . or _: %s', full_path)
    else:
        sub_cmp_list.extend(_get_discovered_comps(search_dir,
                                                  cmp_types_list))

    return sub_cmp_list


def _get_subcomponents_classes(parent_classes):
    """Find available subcomponents for given parent types."""
    return [x for x in get_all_subclasses(parent_classes) if x.type_id]


def _parse_for_components(component):
    """Recursively parses the component directory for allowed components type.

    This method uses get_all_subclasses() to get a list of all subclasses
    of _get_component.allowed_sub_cmps type.
    This ensures that if any new type of component_class is added later,
    this method does not need to be updated as the new sub-class will be
    listed by .__subclasses__() method of the parent class and this method
    will check the directory for its .type_id.
    """
    for new_cmp in _create_subcomponents(
            component.directory,
            _get_subcomponents_classes(component.allowed_sub_cmps)):
        # add the successfulyl created _get_component to the
        # parent _get_component
        component.add_component(new_cmp)
        if new_cmp.is_container:
            # Recursive part: parse each sub-_get_component
            # for its allowed sub-sub-components.
            _parse_for_components(new_cmp)


def parse_comp_dir(comp_path, comp_class):
    return _create_subcomponents(
        comp_path,
        _get_subcomponents_classes([comp_class]),
        create_from_search_dir=True
        )


def get_parsed_extension(extension):
    """Creates and adds the extensions components to the package.

    Each package object is the root to a tree of components that exists
    under that package. (e.g. tabs, buttons, ...) sub components of package
    can be accessed by iterating the _get_component.
    See _basecomponents for types.

    When a layout file is present, uses layout-based parsing. An invalid
    layout never wipes the ribbon: parsing falls back from the custom
    override to the bundled layout, then to the legacy directory walk.
    """
    from pyrevit.extensions.layout_parser import get_custom_layout_file, \
        get_bundled_layout_file, parse_extension_layout
    from pyrevit.extensions.toolindex import build_tool_index

    # Candidate layouts in priority order: custom override, then bundled.
    candidates = []
    for layout_file in (get_custom_layout_file(extension.directory),
                        get_bundled_layout_file(extension.directory)):
        if layout_file and layout_file not in candidates:
            candidates.append(layout_file)

    if candidates:
        mlogger.debug('Using layout-based parsing for: %s', extension.name)
        tools_dir = op.join(extension.directory, exts.TOOLS_DIR_NAME)
        # build_tool_index handles missing tools_dir and also scans the
        # legacy .tab/.panel/ hierarchy, supporting hybrid layouts.
        tool_index = build_tool_index(tools_dir, extension.directory)
        for layout_file in candidates:
            _reset_components(extension)
            if parse_extension_layout(extension, tool_index, layout_file):
                return extension
            mlogger.warning('Layout file failed to parse, falling back: %s',
                            layout_file)
        mlogger.warning('No valid layout for %s; using legacy directory parsing',
                        extension.name)

    _reset_components(extension)
    _parse_for_components(extension)
    return extension


def _reset_components(extension):
    """Clear components from a prior parse attempt before re-parsing."""
    extension.components = []


def parse_dir_for_ext_type(root_dir, parent_cmp_type):
    """Return the objects of type parent_cmp_type of the extensions in root_dir.

    The package objects won't be parsed at this level.
    This is useful for collecting basic info on an extension type
    for cache cheching or updating extensions using their directory paths.

    Args:
        root_dir (str): directory to parse
        parent_cmp_type (type): type of objects to return
    """
    # making sure the provided directory exists.
    # This is mainly for the user defined package directories
    if not op.exists(root_dir):
        mlogger.debug('Extension search directory does not exist: %s', root_dir)
        return []

    # try creating extensions in given directory
    ext_data_list = []

    mlogger.debug('Parsing directory for extensions of type: %s',
                  parent_cmp_type)
    for ext_data in _create_subcomponents(root_dir, [parent_cmp_type]):
        mlogger.debug('Extension directory found: %s', ext_data)
        ext_data_list.append(ext_data)

    return ext_data_list
