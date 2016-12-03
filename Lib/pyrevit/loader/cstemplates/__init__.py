import os
import os.path as op

from pyrevit.core.exceptions import PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader import ASSEMBLY_FILE_TYPE
from pyrevit.coreutils import make_full_classname, find_loaded_asm, load_asm_file
from pyrevit.coreutils.cscompiler import compile_to_asm
from pyrevit.coreutils.appdata import get_data_file


logger = get_logger(__name__)


# base classes for pyRevit commands ------------------------------------------------------------------------------------
LOADER_BASE_NAMESPACE = 'PyRevitBaseClasses'

# template python command class
CMD_EXECUTOR_CLASS_NAME = '{}.{}'.format(LOADER_BASE_NAMESPACE, 'PyRevitCommand')

# template python command availability class
CMD_AVAIL_CLS_NAME = make_full_classname(LOADER_BASE_NAMESPACE, 'PyRevitCommandDefaultAvail')
CMD_AVAIL_CLS_NAME_CATEGORY = make_full_classname(LOADER_BASE_NAMESPACE, 'PyRevitCommandCategoryAvail')
CMD_AVAIL_CLS_NAME_SELECTION = make_full_classname(LOADER_BASE_NAMESPACE, 'PyRevitCommandSelectionAvail')


BASE_CLASSES_ASM_FILE = get_data_file(LOADER_BASE_NAMESPACE, ASSEMBLY_FILE_TYPE)
# taking the name of the generated data file and use it as assembly name
BASE_CLASSES_ASM_NAME = op.splitext(op.basename(BASE_CLASSES_ASM_FILE))[0]


def _get_source_files():
    source_files = list()
    source_dir = op.dirname(__file__)
    for source_file in os.listdir(source_dir):
        if op.isfile(source_file) and op.splitext(source_file)[1].lower() == '.cs':
            source_files.append(op.join(source_dir, source_file))

    return source_files


def _generate_base_classes_asm():
    source_string = ''
    for source_file in _get_source_files():
        # fixme: handle read errors
        with open(source_file, 'r') as code_file:
            source_string += code_file.read()
    try:
        baseclass_asm = compile_to_asm(source_string, BASE_CLASSES_ASM_FILE,
                                       reference_list=[find_loaded_asm('PresentationCore').Location,
                                                       find_loaded_asm('WindowsBase').Location,
                                                       'RevitAPI.dll', 'RevitAPIUI.dll'])
    except PyRevitException as compile_err:
        logger.critical('Can not compile cstemplates code into assembly. | {}'.format(compile_err))
        raise compile_err

    return load_asm_file(baseclass_asm)


def _find_pyrevit_base_class(base_class_name):
    base_class = BASE_CLASSES_ASM.GetType(base_class_name)
    if base_class is not None:
        return base_class
    else:
        raise PyRevitException('Can not find base class type: {}'.format(base_class_name))


# see it the assembly is already loaded
BASE_CLASSES_ASM = find_loaded_asm(BASE_CLASSES_ASM_NAME)
# else, let's generate the assembly and load it
if not BASE_CLASSES_ASM:
    BASE_CLASSES_ASM = _generate_base_classes_asm()


CMD_EXECUTOR_CLASS = _find_pyrevit_base_class(CMD_EXECUTOR_CLASS_NAME)
CMD_AVAIL_CLS = _find_pyrevit_base_class(CMD_AVAIL_CLS_NAME)
CMD_AVAIL_CLS_CATEGORY = _find_pyrevit_base_class(CMD_AVAIL_CLS_NAME_CATEGORY)
CMD_AVAIL_CLS_SELECTION = _find_pyrevit_base_class(CMD_AVAIL_CLS_NAME_SELECTION)


def get_cmd_class(cmd_comp):
    # return executor_class for this given command
    # fixme: check for command type and type of executor
    if cmd_comp:
        return CMD_EXECUTOR_CLASS


def get_cmd_avail_class(cmd_context):
    # return (avail_class, class_name) for this given command
    if cmd_context == 'Selection':
        return CMD_AVAIL_CLS_SELECTION
    else:
        return CMD_AVAIL_CLS_CATEGORY


def get_shared_classes():
    # return list of tuples (default_avail_class, class_name)
    return [(CMD_AVAIL_CLS, CMD_AVAIL_CLS_NAME)]
