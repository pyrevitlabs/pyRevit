"""Find, parse and cache extensions.

There are two types of extensions: UI Extensions (components.Extension) and
Library Extensions (components.LibraryExtension).

This module, finds the ui extensions installed and parses their directory for
tools or loads them from cache. It also finds the library extensions and adds
their directory address to the ui extensions so the python tools can use
the shared libraries.

To do its job correctly, this module needs to communicate with
pyrevit.userconfig to get a list of user extension folder and also
pyrevit.extensions.extpackages to check whether an extension is active or not.
"""

from pyrevit import MAIN_LIB_DIR, MISC_LIB_DIR
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config


try:
    if user_config.bin_cache:
        from pyrevit.extensions.cacher_bin import is_cache_valid,\
            get_cached_extension, update_cache
    else:
        from pyrevit.extensions.cacher_asc import is_cache_valid,\
            get_cached_extension, update_cache
except AttributeError:
    user_config.bin_cache = True
    user_config.save_changes()
    from pyrevit.extensions.cacher_bin import is_cache_valid,\
        get_cached_extension, update_cache

#pylint: disable=C0413
from pyrevit.extensions.parser import parse_dir_for_ext_type, get_parsed_extension
from pyrevit.extensions.components import Extension, LibraryExtension

import pyrevit.extensions.extpackages as extpkgs


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def _update_extension_search_paths(ui_ext, lib_ext_list, pyrvt_paths):
    for lib_ext in lib_ext_list:
        ui_ext.add_module_path(lib_ext.directory)

    for pyrvt_path in pyrvt_paths:
        ui_ext.add_module_path(pyrvt_path)


def _is_extension_enabled(ext_info):
    try:
        ext_pkg = extpkgs.get_ext_package_by_name(ext_info.name)
        if ext_pkg:
            return ext_pkg.is_enabled and ext_pkg.user_has_access
        else:
            mlogger.debug('Extension package is not defined: %s', ext_info.name)
    except Exception as ext_check_err:
        mlogger.error('Error checking state for extension: %s | %s',
                      ext_info.name, ext_check_err)

    # Lets be nice and load the package if it is not defined
    return True


def _remove_disabled_extensions(ext_list):
    cleaned_ext_list = []
    for extension in ext_list:
        if _is_extension_enabled(extension):
            cleaned_ext_list.append(extension)
        else:
            mlogger.debug('Skipping disabled extension: %s', extension.name)

    return cleaned_ext_list


def _parse_or_cache(ext_info):
    # parse the extension if ui_extension does not have a valid cache
    if not is_cache_valid(ext_info):
        mlogger.debug('Cache is not valid for: %s', ext_info)

        # Either cache is not available, not valid, or cache load has failed.
        # parse directory for components and return fully loaded ui_extension
        mlogger.debug('Parsing for ui_extension...')
        ui_extension = get_parsed_extension(ext_info)

        # update cache with newly parsed ui_extension
        mlogger.debug('UI Extension successfuly parsed: %s', ui_extension.name)
        mlogger.debug('Updating cache for ui_extension: %s', ui_extension.name)
        update_cache(ui_extension)

    # otherwise load the cache
    else:
        mlogger.debug('Cache is valid for: %s', ext_info)
        # if cache is valid, load the cached ui_extension
        # cacher module takes the ui_extension object and
        # injects cache data into it.
        ui_extension = get_cached_extension(ext_info)
        mlogger.debug('UI Extension successfuly loaded from cache: %s',
                     ui_extension.name)

    return ui_extension


def get_thirdparty_extension_data():
    """Returns all installed and active UI and Library extensions (not parsed).

    Returns:
        (list): list of components.Extension or components.LibraryExtension
    """
    # FIXME: reorganzie this code to use one single method to collect
    # extension data for both lib and ui
    ext_data_list = []

    for root_dir in user_config.get_thirdparty_ext_root_dirs():
        ext_data_list.extend(
            [ui_ext for ui_ext in parse_dir_for_ext_type(root_dir,
                                                         Extension)])
        ext_data_list.extend(
            [lib_ext for lib_ext in parse_dir_for_ext_type(root_dir,
                                                           LibraryExtension)])

    return _remove_disabled_extensions(ext_data_list)


def get_installed_lib_extensions(root_dir):
    """Returns all the installed and active Library extensions (not parsed).

    Args:
        root_dir (str): Extensions directory address

    Returns:
        (list[LibraryExtension]): list of components.LibraryExtension objects
    """
    lib_ext_list = \
        [lib_ext for lib_ext in parse_dir_for_ext_type(root_dir,
                                                       LibraryExtension)]
    return _remove_disabled_extensions(lib_ext_list)


def get_installed_ui_extensions():
    """Returns all UI extensions (fully parsed) under the given directory.

    This will also process the Library extensions and will add
    their path to the syspath of the UI extensions.

    Returns:
        (list[Extension]): list of components.Extension objects
    """
    ui_ext_list = []
    lib_ext_list = []

    # get a list of all directories that could include extensions
    ext_search_dirs = user_config.get_ext_root_dirs()
    mlogger.debug('Extension Directories: %s', ext_search_dirs)

    # collect all library extensions. Their dir paths need to be added
    # to sys.path for all commands
    for root_dir in ext_search_dirs:
        lib_ext_list.extend(get_installed_lib_extensions(root_dir))
        # Get a list of all installed extensions in this directory
        # _parser.parse_dir_for_ext_type() returns a list of extensions
        # in given directory

    for root_dir in ext_search_dirs:
        for ext_info in parse_dir_for_ext_type(root_dir, Extension):
            # test if cache is valid for this ui_extension
            # it might seem unusual to create a ui_extension and then
            # re-load it from cache but minimum information about the
            # ui_extension needs to be passed to the cache module for proper
            # hash calculation and ui_extension recovery. at this point
            # `ui_extension` does not include any sub-components
            # (e.g, tabs, panels, etc) ui_extension object is very small and
            # its creation doesn't add much overhead.

            if _is_extension_enabled(ext_info):
                ui_extension = _parse_or_cache(ext_info)
                ui_ext_list.append(ui_extension)
            else:
                mlogger.debug('Skipping disabled ui extension: %s',
                             ext_info.name)

    # update extension master syspaths with standard pyrevit lib paths and
    # lib address of other lib extensions (to support extensions that provide
    # library only to be used by other extensions)
    # all other lib paths internal to the extension and tool bundles have
    # already been set inside the extension bundles and will take precedence
    # over paths added by this method (they're the first paths added to the
    # search paths list, and these paths will follow)
    for ui_extension in ui_ext_list:
        _update_extension_search_paths(
            ui_extension,
            lib_ext_list,
            [MAIN_LIB_DIR, MISC_LIB_DIR]
            )

    return ui_ext_list
