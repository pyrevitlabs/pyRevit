import os
import os.path as op

from pyrevit.core.exceptions import PyRevitException
from pyrevit.core.logger import get_logger
from pyrevit.coreutils.coreutils import get_all_subclasses
from .components import Extension, LibraryExtension

logger = get_logger(__name__)




# ----------------------------------------------------------------------------------------------------------------------
# caching tabs, panels, buttons and button groups
# ----------------------------------------------------------------------------------------------------------------------
SUB_CMP_KEY = '_sub_components'
HASH_VALUE_PARAM = 'hash_value'
HASH_VERSION_PARAM = 'hash_version'



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


def get_parsed_extension(pkg):
    """Parses package directory and creates and adds components to the package object
    Each package object is the root to a tree of components that exists under that package. (e.g. tabs, buttons, ...)
    sub components of package can be accessed by iterating the _get_component. See _basecomponents for types.
    """
    _parse_for_components(pkg)
    return pkg


def get_installed_extension_data(root_dir):
    """Parses home directory and return a list of Extension objects for installed extensions.
    The package objects won't be parsed at this level. This function onyl provides the basic info for the installed
    extensions so the session can check the cache for each package and decide if they need to be parsed or not.
    """
    # making sure the provided directory exists. This is mainly for the user defined package directories
    if not op.exists(root_dir):
        logger.debug('Extension search directory does not exist: {}'.format(root_dir))
        return []

    # try creating extensions in given directory
    pkg_data_list = []

    logger.debug('Parsing directory for extensions...')
    for pkg_data in _create_subcomponents(root_dir, [Extension]):
        logger.debug('Extension directory found: {}'.format(pkg_data))
        pkg_data_list.append(pkg_data)

    return pkg_data_list


def get_installed_lib_extension_data(root_dir):
    """Parses home directory and return a list of LibraryExtension objects for installed library extensions."""

    # making sure the provided directory exists. This is mainly for the user defined package directories
    if not op.exists(root_dir):
        logger.debug('Extension search directory does not exist: {}'.format(root_dir))
        return []

    # try creating extensions in given directory
    lib_pkg_data_list = []

    logger.debug('Parsing directory for library extensions...')
    for lib_pkg_data in _create_subcomponents(root_dir, [LibraryExtension]):
        logger.debug('Library package directory found: {}'.format(lib_pkg_data))
        lib_pkg_data_list.append(lib_pkg_data)

    return lib_pkg_data_list
