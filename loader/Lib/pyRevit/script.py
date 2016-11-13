# todo: implement script info functions
import os
import os.path as op

from .logger import get_logger
logger = get_logger(__name__)

from .utils import get_all_subclasses
from .loader.components import GenericCommand


def get_script_info():
    # fixme: test
    for component_type in get_all_subclasses(GenericCommand):
        logger.debug('Testing sub_directory {} for {}'.format(file_or_dir, component_type))
        try:
            # if cmp_class can be created for this sub-dir, the add to list
            # cmp_class will raise error if full_path is not of cmp_class type.
            component = component_type()
            component.__init_from_dir__(full_path)
            logger.debug('Successfuly created component: {} from: {}'.format(component, full_path))
            return component
        except PyRevitException:
            logger.debug('Can not create component of type: {} from: {}'.format(component_type, full_path))
    return None


def get_ui_button():
    pass


def get_ui_button_group():
    pass


def get_ui_panel():
    pass


def get_ui_tab():
    pass
