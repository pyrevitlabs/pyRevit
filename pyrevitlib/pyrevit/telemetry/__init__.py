"""
This module manages the telemetry system.

    This function is used to setup the telemetry system on pyRevit startup:
        >>> setup_telemetry_file()

    These functions are used to query information about the logging system:
        >>> get_default_telemetry_filepath()
        >>> get_current_telemetry_path()

        >>> get_current_telemetry_file()
        >>> get_current_telemetry_serverurl()
        >>> is_active()

    This module also provides a wrapper class around the command results
    dictionary that is included with the telemetry record.

    Scripts should use the instance of this class provided by the
    scriptutils module. See scriptutils for examples

"""
import os.path as op

from pyrevit import PYREVIT_ADDON_NAME, PYREVIT_VERSION_APP_DIR,\
                    PYREVIT_FILE_PREFIX
from pyrevit.coreutils import is_blank
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars

from pyrevit.loader.sessioninfo import get_session_uuid
from pyrevit.userconfig import user_config


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


PYREVIT_TELEMETRYSTATE_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_TELEMETRYSTATE'
PYREVIT_TELEMETRYFILE_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_TELEMETRYFILE'
PYREVIT_TELEMETRYSERVER_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_TELEMETRYSERVER'


# templates for telemetry file naming
FILE_LOG_EXT = 'json'
FILE_LOG_FILENAME_TEMPLATE = '{}_{}_telemetry.{}'


def _init_telemetry_envvars():
    # init all env variables related to telemetry
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYSTATE_ENVVAR, False)
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYFILE_ENVVAR, '')
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYSERVER_ENVVAR, '')


def _disable_telemetry():
    # set telemetry env variable to False, disabling the telemetry
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYSTATE_ENVVAR, False)


def _disable_file_telemetry():
    # set file logging env variable to empty, disabling the file logging
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYFILE_ENVVAR, '')


def _disable_server_telemetry():
    # set server logging env variable to empty, disabling the remote logging
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYSERVER_ENVVAR, '')


def _setup_default_logfile(telemetry_fullfilepath):
    # setup default telemetry file name
    envvars.set_pyrevit_env_var(
        PYREVIT_TELEMETRYFILE_ENVVAR, telemetry_fullfilepath
        )
    if not op.exists(telemetry_fullfilepath):
        # if file does not exist, let's write the basic JSON list to it.
        try:
            with open(telemetry_fullfilepath, 'w') as log_file:
                log_file.write('[]')
        except Exception as write_err:
            mlogger.error('Telemetry is active but log file location '
                          'is not accessible. | %s', write_err)
            _disable_telemetry()


def setup_telemetry_file(session_id=None):
    """Sets up the telemetry default config and environment values."""

    if not session_id:
        session_id = get_session_uuid()

    # default file path and name for telemetry
    filelogging_filename = FILE_LOG_FILENAME_TEMPLATE \
        .format(PYREVIT_FILE_PREFIX, session_id, FILE_LOG_EXT)

    # default server url for telemetry
    telemetry_serverurl = ''

    # initialize env variables related to telemetry
    _init_telemetry_envvars()

    # setup config section if does not exist
    if not user_config.has_section('telemetry'):
        user_config.add_section('telemetry')

    # GLOBAL SWITCH ------------------------------------------------------------
    # setup default value for telemetry global switch
    ul_config = user_config.telemetry
    telemetryactive = ul_config.get_option('active', default_value=False)
    envvars.set_pyrevit_env_var(
        PYREVIT_TELEMETRYSTATE_ENVVAR, telemetryactive
        )

    # FILE telemetry -------------------------------------------------------
    # read or setup default values for file telemetry
    telemetrypath = ul_config.get_option('telemetrypath',
                                       default_value=PYREVIT_VERSION_APP_DIR)

    # check file telemetry config and setup destination
    if not telemetrypath or is_blank(telemetrypath):
        # if no config is provided, disable output
        _disable_file_telemetry()
    else:
        # if config exists, create new telemetry file under the same address
        if telemetryactive:
            if op.isdir(telemetrypath):
                # if directory is valid
                logfile_fullpath = op.join(telemetrypath, filelogging_filename)
                _setup_default_logfile(logfile_fullpath)
            else:
                # if not, show error and disable telemetry
                mlogger.error('Provided telemetry address does not exits or is '
                              'not a directory. Telemetry disabled.')
                _disable_telemetry()

    # SERVER telemetry -----------------------------------------------------
    # read or setup default values for server telemetry
    telemetryserverurl = ul_config.get_option('telemetryserverurl',
                                        default_value=telemetry_serverurl)

    # check server telemetry config and setup destination
    if not telemetryserverurl or is_blank(telemetryserverurl):
        # if no config is provided, disable output
        _disable_server_telemetry()
    else:
        # if config exists, setup server logging
        envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYSERVER_ENVVAR, telemetryserverurl)


def get_default_telemetry_filepath():
    """Returns default telemetry path. This path is automatically
    generated at module execution.

    Returns:
        str: Default telemetry path. This might not be the active path.
    """
    return PYREVIT_VERSION_APP_DIR


def get_current_telemetry_path():
    """Returns active telemetry path. This path might be the default,
    or set by user in user config.

    Returns:
        str: Active telemetry path.
    """
    return op.dirname(envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYFILE_ENVVAR))


def get_current_telemetry_file():
    """
    Returns active telemetry full file path. This is the file that telemetry
    records are being written to in current pyRevit session. Telemetry
    filenames are automatically generated at this module execution.

    Returns:
        str: Active telemetry full file path.
    """
    return envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYFILE_ENVVAR)


def get_current_telemetry_serverurl():
    """
    Returns active telemetry server url. This is the server that telemetry
    records are being sent to in current pyRevit session.
    Server url must be set by the user in config.

    Returns:
        str: Active telemetry server url.
    """
    return envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYSERVER_ENVVAR)


def is_active():
    """Returns status of telemetry system.

    Returns:
        bool: True if telemetry is active, False if not.
    """
    return envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYSTATE_ENVVAR)
