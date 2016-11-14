import os
import os.path as op

from .logger import get_logger
logger = get_logger(__name__)

from .utils import get_all_subclasses
from .exceptions import PyRevitException
from .loader.components import GenericCommand


def get_script_info(script_dir):
    # fixme: test
    for component_type in get_all_subclasses(GenericCommand):
        logger.debug('Testing sub_directory {} for {}'.format(script_dir, component_type))
        try:
            # if cmp_class can be created for this sub-dir, the add to list
            # cmp_class will raise error if full_path is not of cmp_class type.
            component = component_type()
            component.__init_from_dir__(script_dir)
            logger.debug('Successfuly created component: {} from: {}'.format(component, script_dir))
            return component
        except PyRevitException:
            logger.debug('Can not create component of type: {} from: {}'.format(component_type, script_dir))
    return None


def get_ui_button():
    # fixme: implement get_ui_button
    pass


def get_temp_file():
    """Returns a filename to be used by a user script to store temporary information.
    Temporary files are saved in USER_TEMP_DIR.
    """
    # fixme temporary file
    pass
