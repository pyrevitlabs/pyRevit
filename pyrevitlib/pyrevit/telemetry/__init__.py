"""This module manages the telemetry system.

This function is used to setup the telemetry system on pyRevit startup:
    ```python
    setup_telemetry()
    ```

These functions are used to query information about the logging system:
    ```python
    get_telemetry_state()
    ```

    ```python
    get_apptelemetry_state()
    ```

This module also provides a wrapper class around the command results
dictionary that is included with the telemetry record.

Scripts should use the instance of this class provided by the
script module. See `script.get_results()` for examples
"""
import os.path as op
import json

from pyrevit import HOST_APP, PYREVIT_VERSION_APP_DIR, PYREVIT_FILE_PREFIX
from pyrevit.runtime.types import EventType, EventTelemetry
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.compat import urlopen

from pyrevit.loader import sessioninfo
from pyrevit.userconfig import user_config

from pyrevit.labs import PyRevit

from pyrevit.telemetry import events as telemetry_events


# templates for telemetry file naming
FILE_LOG_EXT = 'json'
FILE_LOG_FILENAME_TEMPLATE = '{}_{}_telemetry.{}'


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)

# pyrevit global consts
consts = PyRevit.PyRevitConsts


def get_default_telemetry_filepath():
    return PYREVIT_VERSION_APP_DIR


def get_telemetry_state():
    return envvars.get_pyrevit_env_var(envvars.TELEMETRYSTATE_ENVVAR)


def get_telemetry_utc_timestamp():
    return envvars.get_pyrevit_env_var(envvars.TELEMETRYUTCTIMESTAMPS_ENVVAR)


def get_telemetry_file_dir():
    return envvars.get_pyrevit_env_var(envvars.TELEMETRYDIR_ENVVAR)


def get_telemetry_file_path():
    return envvars.get_pyrevit_env_var(envvars.TELEMETRYFILE_ENVVAR)


def get_telemetry_server_url():
    return envvars.get_pyrevit_env_var(envvars.TELEMETRYSERVER_ENVVAR)


def get_telemetry_include_hooks():
    return envvars.get_pyrevit_env_var(envvars.TELEMETRYINCLUDEHOOKS_ENVVAR)


def set_telemetry_state(state):
    envvars.set_pyrevit_env_var(envvars.TELEMETRYSTATE_ENVVAR, state)
    user_config.telemetry_status = state


def set_telemetry_utc_timestamp(state):
    envvars.set_pyrevit_env_var(envvars.TELEMETRYUTCTIMESTAMPS_ENVVAR, state)
    user_config.telemetry_utc_timestamp = state


def set_telemetry_file_dir(file_dir):
    if not file_dir or not op.isdir(file_dir):
        disable_telemetry_to_file()
    envvars.set_pyrevit_env_var(envvars.TELEMETRYDIR_ENVVAR, file_dir)
    user_config.telemetry_file_dir = file_dir


def set_telemetry_file_path(file_path):
    envvars.set_pyrevit_env_var(envvars.TELEMETRYFILE_ENVVAR, file_path)


def set_telemetry_server_url(server_url):
    envvars.set_pyrevit_env_var(envvars.TELEMETRYSERVER_ENVVAR, server_url)
    user_config.telemetry_server_url = server_url


def set_telemetry_include_hooks(state):
    envvars.set_pyrevit_env_var(envvars.TELEMETRYINCLUDEHOOKS_ENVVAR, state)
    user_config.telemetry_include_hooks = state


def disable_telemetry():
    set_telemetry_state(False)


def disable_telemetry_to_file():
    set_telemetry_file_path('')


def disable_telemetry_to_server():
    set_telemetry_server_url('')


def get_apptelemetry_state():
    return envvars.get_pyrevit_env_var(envvars.APPTELEMETRYSTATE_ENVVAR)


def set_apptelemetry_state(state):
    envvars.set_pyrevit_env_var(envvars.APPTELEMETRYSTATE_ENVVAR, state)
    user_config.apptelemetry_status = state


def get_apptelemetry_handler():
    return envvars.get_pyrevit_env_var(envvars.APPTELEMETRYHANDLER_ENVVAR)


def set_apptelemetry_handler(handler):
    envvars.set_pyrevit_env_var(envvars.APPTELEMETRYHANDLER_ENVVAR, handler)


def get_apptelemetry_server_url():
    return envvars.get_pyrevit_env_var(envvars.APPTELEMETRYSERVER_ENVVAR)


def get_apptelemetry_event_flags():
    # default value is 16 bytes of 0
    flags_hex = \
        user_config.apptelemetry_event_flags or '0x00000000000000000000000000000000'
    return coreutils.hex2int_long(flags_hex)


def set_apptelemetry_server_url(server_url):
    envvars.set_pyrevit_env_var(envvars.APPTELEMETRYSERVER_ENVVAR, server_url)
    user_config.apptelemetry_server_url = server_url


def set_apptelemetry_event_flags(event_flags):
    flags_hex = coreutils.int2hex_long(event_flags)
    user_config.apptelemetry_event_flags = flags_hex
    envvars.set_pyrevit_env_var(
        envvars.APPTELEMETRYEVENTFLAGS_ENVVAR, flags_hex)


def disable_apptelemetry():
    set_apptelemetry_state(False)


def disable_apptelemetry_to_server():
    set_apptelemetry_server_url('')


def get_apptelemetry_event_types():
    return list(coreutils.get_enum_values(EventType))


def get_apptelemetry_event_state(flags, event_type):
    event_idx = get_apptelemetry_event_types().index(event_type)
    return flags & (1<<event_idx)


def set_apptelemetry_event_state(flags, event_type):
    return flags | (1<<int(event_type))


def unset_apptelemetry_event_state(flags, event_type):
    return flags & ~(1<<int(event_type))


def _setup_default_logfile(telemetry_fullpath):
    # setup default telemetry file name
    if not op.exists(telemetry_fullpath):
        # if file does not exist, let's write the basic JSON list to it.
        with open(telemetry_fullpath, 'w') as log_file:
            log_file.write('[]')


def get_status_from_url(server_url):
    server_url = server_url.lower()
    if server_url.endswith('scripts/'):
        server_url = server_url.replace('scripts/', 'status')
    elif server_url.endswith('events/'):
        server_url = server_url.replace('events/', 'status')

    try:
        return json.loads(urlopen(server_url).read())
    except Exception:
        return None


def get_status():
    return get_status_from_url(
        get_telemetry_server_url()
        or get_apptelemetry_server_url()
        )


def setup_telemetry(session_id=None):
    """Sets up the telemetry default config and environment values."""
    # make sure session id is availabe
    if not session_id:
        session_id = sessioninfo.get_session_uuid()

    # PYREVIT TELEMETRY -------------------------------------------------------
    # utc timestamp
    telemetry_utc_timestamp = user_config.telemetry_utc_timestamp
    set_telemetry_utc_timestamp(telemetry_utc_timestamp)

    # global telemetry toggle
    telemetry_state = user_config.telemetry_status
    set_telemetry_state(telemetry_state)

    # read or setup default values for file telemetry
    # default file path and name for telemetry
    telemetry_file_dir = user_config.telemetry_file_dir
    set_telemetry_file_dir(telemetry_file_dir)

    # check file telemetry config and setup destination
    if not telemetry_file_dir or coreutils.is_blank(telemetry_file_dir):
        # if no config is provided, disable output
        disable_telemetry_to_file()
    # if config exists, create new telemetry file under the same address
    elif telemetry_state:
        if op.isdir(telemetry_file_dir):
            telemetry_file_name = \
                FILE_LOG_FILENAME_TEMPLATE.format(PYREVIT_FILE_PREFIX,
                                                  session_id,
                                                  FILE_LOG_EXT)
            # if directory is valid
            telemetry_fullfilepath = \
                op.join(telemetry_file_dir, telemetry_file_name)
            set_telemetry_file_path(telemetry_fullfilepath)
            # setup telemetry file or disable if failed
            try:
                _setup_default_logfile(telemetry_fullfilepath)
            except Exception as write_err:
                mlogger.error('Telemetry is active but log file location '
                              'is not accessible. | %s', write_err)
                disable_telemetry_to_file()
        else:
            # if not, show error and disable telemetry
            mlogger.error('Provided telemetry address does not exits or is '
                          'not a directory. Telemetry disabled.')
            disable_telemetry_to_file()

    # read or setup default values for server telemetry
    telemetry_server_url = user_config.telemetry_server_url

    # check server telemetry config and setup destination
    if not telemetry_server_url or coreutils.is_blank(telemetry_server_url):
        # if no config is provided, disable output
        disable_telemetry_to_server()
    else:
        # if config exists, setup server logging
        set_telemetry_server_url(telemetry_server_url)

    # set telemetry script types
    set_telemetry_include_hooks(user_config.telemetry_include_hooks)

    # APP TELEMETRY ------------------------------------------------------------
    # setup default value for telemetry global switch
    apptelemetry_state = user_config.apptelemetry_status
    set_apptelemetry_state(apptelemetry_state)

    # read or setup default values for server telemetry
    apptelemetry_server_url = user_config.apptelemetry_server_url

    # check server telemetry config and setup destination
    if not apptelemetry_server_url \
            or coreutils.is_blank(apptelemetry_server_url):
        # if no config is provided, disable output
        disable_apptelemetry_to_server()
    else:
        # if config exists, setup server logging
        set_apptelemetry_server_url(apptelemetry_server_url)

    # setup events
    new_telemetry_handler = EventTelemetry(session_id, HOST_APP.username)
    telemetry_handler = get_apptelemetry_handler()
    if telemetry_handler:
        # clear existing
        telemetry_events.unregister_all_event_telemetries(telemetry_handler)

    set_apptelemetry_handler(new_telemetry_handler)
    # register handlers only if telemetry system is active
    if apptelemetry_state:
        apptelemetry_event_flags = get_apptelemetry_event_flags()
        # re-register events with new telemetry_handler
        telemetry_events.register_event_telemetry(
            new_telemetry_handler,
            apptelemetry_event_flags
        )

    user_config.save_changes()
