import os
import os.path as op

from .exceptions import PyRevitUnknownFormatError
from .logger import logger
from .config import HOME_DIR
from ._commandtree import Package, Panel, Tab, GenericCommandGroup, GenericCommand
from ._cache import is_cache_valid, get_cached_package, update_cache


def _get_sub_dirs(parent_dir):
    # todo revise to return directories only?
    return os.listdir(parent_dir)


def _find_subcomponents(search_dir, component_class):
    """Parses the provided directory and returns a list of objects of the type component_class.
    Arguments:
        search_dir: directory to parse
        component_class: If a subfolder name ends with component_class.type_id, (or .type_id of any sub-class)
        this method creates the component_class (or sub-class) object and adds to the list to be returned.
        This ensures that of any new type of sub-class is added, this method does not need to be updated as
         the new sub-class will be listed by .__subclasses__() method of the parent class.
    Example:
        _find_subcomponents(search_dir, GenericCommand)
        GenericCommand.__subclasses__() will return [LinkButton, PushButton, or ToggleButton] and thus
        this method creates LinkButton, PushButton, or ToggleButton for the parsed sub-directories under search_dir
        with matching .type_id identifiers in folder names. (e.g. "folder.LINK_BUTTON_POSTFIX")
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
                    sub_cmp_list.append(cmp_class(full_path))
                except PyRevitUnknownFormatError:
                    # else, try next class
                    continue
                # todo: log skipping over dirs that dont match anthing

    return sub_cmp_list


def _find_cmd(search_dir):
    return _find_subcomponents(search_dir, GenericCommand)


def _find_cmd_groups(search_dir):
    return _find_subcomponents(search_dir, GenericCommandGroup)


def _find_panels(search_dir):
    return _find_subcomponents(search_dir, Panel)


def _find_tabs(search_dir):
    return _find_subcomponents(search_dir, Tab)


def get_installed_packages():
    """Parses home directory and return a list of Package objects for installed packages."""
    pkgs = []
    for dirname in _get_sub_dirs(HOME_DIR):
        full_path = op.join(HOME_DIR, dirname)
        try:
            # try creating a package
            new_pkg = Package(full_path)

            for new_tab in _find_tabs(new_pkg.directory):
                new_pkg.add_component(new_tab)
                # todo: try reading tab from cache before parsing for it
                for new_panel in _find_panels(new_tab.directory):
                    new_tab.add_panel(new_panel)
                    for new_cmd_group in _find_cmd_groups(new_panel.directory):
                        new_panel.add_component(new_cmd_group)
                        for new_cmd in _find_cmd(new_cmd_group.group_dir):
                            new_cmd_group.add_cmd(new_cmd)
                    for new_cmd in _find_cmd(new_panel.directory):
                        new_panel.add_component(new_cmd)

            pkgs.append(new_pkg)

        except PyRevitUnknownFormatError:
            # todo log failure
            pass

    return pkgs
