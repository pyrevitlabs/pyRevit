import sys
import uuid

from pyrevit import PYREVIT_ADDON_NAME, HOST_APP, HOME_DIR

from pyrevit.versionmgr import PYREVIT_VERSION
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.envvars import set_pyrevit_env_var, get_pyrevit_env_var
from pyrevit.userconfig import user_config

from pyrevit.loader.basetypes import BASE_TYPES_ASM_NAME


logger = get_logger(__name__)


SESSION_UUID_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_uuidISC'


def set_session_uuid(uuid_str):
    set_pyrevit_env_var(SESSION_UUID_ISC_KEYNAME, uuid_str)


def get_session_uuid():
    return get_pyrevit_env_var(SESSION_UUID_ISC_KEYNAME)


def new_session_uuid():
    uuid_str = unicode(uuid.uuid1())
    set_session_uuid(uuid_str)
    return uuid_str


def report_env():
    # log python version, home directory, config file, ...
    # get python version that includes last commit hash
    pyrvt_ver = PYREVIT_VERSION.get_formatted()

    logger.info('pyRevit version: {} - '
                ':coded: with :small-black-heart: '
                'in Portland, OR'.format(pyrvt_ver))
    logger.info('Host is {} (build: {} id: {})'.format(HOST_APP.version_name,
                                                       HOST_APP.build,
                                                       HOST_APP.proc_id))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Session uuid is: {}'.format(get_session_uuid()))
    logger.info('Base assembly is: {}'.format(BASE_TYPES_ASM_NAME))
    logger.info('Config file is: {}'.format(user_config.config_file))
