from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config

try:
    if user_config.init.bincache:
        from pyrevit.extensions.cacher_bin import is_cache_valid, get_cached_extension, update_cache
    else:
        from pyrevit.extensions.cacher_asc import is_cache_valid, get_cached_extension, update_cache
except AttributeError:
    user_config.init.bincache = True
    user_config.save_changes()
    from pyrevit.extensions.cacher_bin import is_cache_valid, get_cached_extension, update_cache

from pyrevit.extensions.parser import parse_dir_for_ext_type, get_parsed_extension, parse_comp_dir
from pyrevit.extensions.genericcomps import GenericUICommand
from pyrevit.extensions.components import Extension, LibraryExtension


logger = get_logger(__name__)


def _update_extension_syspaths(ui_ext, lib_ext_list):
    for lib_ext in lib_ext_list:
        ui_ext.add_syspath(lib_ext.directory)


def get_command_from_path(comp_path):
    return parse_comp_dir(comp_path, GenericUICommand)


def get_installed_extension_data(root_dir):
    ext_data_list = []
    ext_data_list.extend([ui_ext for ui_ext in parse_dir_for_ext_type(root_dir, Extension)])
    ext_data_list.extend([lib_ext for lib_ext in parse_dir_for_ext_type(root_dir, LibraryExtension)])
    return ext_data_list


def get_installed_lib_extensions(root_dir):
    return [lib_ext for lib_ext in parse_dir_for_ext_type(root_dir, LibraryExtension)]


def get_installed_ui_extensions(root_dir):
    ext_list = list()
    lib_ext_list = get_installed_lib_extensions(root_dir)
    for ext_info in parse_dir_for_ext_type(root_dir, Extension):
        # test if cache is valid for this ui_extension
        # it might seem unusual to create a ui_extension and then re-load it from cache but minimum information about
        # the ui_extension needs to be passed to the cache module for proper hash calculation and ui_extension recovery.
        # at this point `ui_extension` does not include any sub-components (e.g, tabs, panels, etc)
        # ui_extension object is very small and its creation doesn't add much overhead.
        try:
            # raise error if ui_extension does not have a valid cache
            if not is_cache_valid(ext_info):
                raise PyRevitException('Cache is not valid for: {}'.format(ext_info))

            # if cache is valid, load the cached ui_extension
            logger.debug('Cache is valid for: {}'.format(ext_info))
            # cacher module takes the ui_extension object and injects cache data into it.
            ui_extension = get_cached_extension(ext_info)
            logger.info('UI Extension successfuly loaded from cache: {}'.format(ui_extension.name))

        except PyRevitException as cache_err:
            logger.debug(cache_err)

            # Either cache is not available, not valid, or cache load has failed.
            # parse directory for components and return fully loaded ui_extension
            logger.debug('Parsing for ui_extension...')
            ui_extension = get_parsed_extension(ext_info)

            # update cache with newly parsed ui_extension
            logger.info('UI Extension successfuly parsed: {}'.format(ui_extension.name))
            logger.info('Updating cache for ui_extension: {}'.format(ui_extension.name))
            update_cache(ui_extension)

        # update extension master syspaths with lib address of other lib extensions
        # this is to support extensions that provide library only to be used by other extensions
        _update_extension_syspaths(ui_extension, lib_ext_list)

        ext_list.append(ui_extension)

    return ext_list
