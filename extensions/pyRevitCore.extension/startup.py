"""pyRevit core startup script"""
#pylint: disable=import-error,unused-import,invalid-name
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config


mlogger = get_logger(__name__)


# decide to load the core api
if user_config.load_core_api:
    import pyrevitcore_api
    # mlogger.info("pyRevit Core Routes API is activated")
