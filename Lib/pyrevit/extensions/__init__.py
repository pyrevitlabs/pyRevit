from pyrevit.core.exceptions import PyRevitException
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

from pyrevit.extensions.parser import get_installed_extension_data, get_installed_lib_extension_data
from pyrevit.extensions.parser import get_parsed_extension


logger = get_logger(__name__)


# Extension types
# ----------------------------------------------------------------------------------------------------------------------
LIB_EXTENSION_POSTFIX = '.lib'
UI_EXTENSION_POSTFIX = '.extension'

# UI_EXTENSION_POSTFIX components
# ----------------------------------------------------------------------------------------------------------------------
TAB_POSTFIX = '.tab'
PANEL_POSTFIX = '.panel'
LINK_BUTTON_POSTFIX = '.linkbutton'
PUSH_BUTTON_POSTFIX = '.pushbutton'
TOGGLE_BUTTON_POSTFIX = '.toggle'
SMART_BUTTON_POSTFIX = '.smartbutton'
PULLDOWN_BUTTON_POSTFIX = '.pulldown'
STACKTHREE_BUTTON_POSTFIX = '.stack3'
STACKTWO_BUTTON_POSTFIX = '.stack2'
SPLIT_BUTTON_POSTFIX = '.splitbutton'
SPLITPUSH_BUTTON_POSTFIX = '.splitpushbutton'

# Component layout elements
DEFAULT_LAYOUT_FILE_NAME = '_layout'
SEPARATOR_IDENTIFIER = '---'
SLIDEOUT_IDENTIFIER = '>>>'

# Component icon
ICON_FILE_FORMAT = '.png'
SCRIPT_FILE_FORMAT = '.py'

DEFAULT_ICON_FILE = 'icon' + ICON_FILE_FORMAT
DEFAULT_ON_ICON_FILE = 'on' + ICON_FILE_FORMAT
DEFAULT_OFF_ICON_FILE = 'off' + ICON_FILE_FORMAT

# Component scripts
DEFAULT_SCRIPT_FILE = 'script' + SCRIPT_FILE_FORMAT
DEFAULT_CONFIG_SCRIPT_FILE = 'config' + SCRIPT_FILE_FORMAT

# Command component defaults
UI_TITLE_PARAM = '__title__'
DOCSTRING_PARAM = '__doc__'
AUTHOR_PARAM = '__author__'

COMMAND_OPTIONS_PARAM = '__cmdoptions__'
COMMAND_CONTEXT_PARAM = '__context__'
MIN_REVIT_VERSION_PARAM = '__min_req_revit_ver__'
MIN_PYREVIT_VERSION_PARAM = '__min_req_pyrevit_ver__'
SHIFT_CLICK_PARAM = '__shiftclick__'

LINK_BUTTON_ASSEMBLY_PARAM = '__assembly__'
LINK_BUTTON_COMMAND_CLASS_PARAM = '__commandclass__'


COMMAND_AVAILABILITY_NAME_POSTFIX = 'Availab'
COMP_LIBRARY_DIR_NAME = 'lib'


def _update_extension_syspaths(ui_ext, lib_ext_list):
    for lib_ext in lib_ext_list:
        ui_ext.add_syspath(lib_ext.directory)


def get_installed_ui_extensions(root_dir):
    ext_list = list()
    lib_ext_list = [lib_ext for lib_ext in get_installed_lib_extension_data(root_dir)]
    for ext_info in get_installed_extension_data(root_dir):
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
