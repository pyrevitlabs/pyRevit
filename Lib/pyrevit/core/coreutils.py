import ast
import inspect
import os
import os.path as op
import time

from pyrevit.config import HOST_ADSK_PROCESS_NAME
from pyrevit.config.coreconfig import PYREVIT_ISC_DICT_NAME, CURRENT_REVIT_APPDOMAIN

from pyrevit.core.exceptions import PyRevitException

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process


def enum(**enums):
    return type('Enum', (), enums)


class Timer:
    """Timer class using python native time module."""
    def __init__(self):
        self.start = time.time()

    def restart(self):
        self.start = time.time()

    def get_time(self):
        return time.time() - self.start


class ScriptFileParser:
    def __init__(self, file_address):
        self.file_addr = file_address
        try:
            with open(file_address, 'r') as f:
                self.ast_tree = ast.parse(f.read())
        except Exception as err:
            raise PyRevitException('Error parsing script file: {} | {}'.format(self.file_addr, err))

    def extract_param(self, param_name):
        try:
            for child in ast.iter_child_nodes(self.ast_tree):
                if hasattr(child, 'targets'):
                    for target in child.targets:
                        if hasattr(target, 'id') and target.id == param_name:
                            return ast.literal_eval(child.value)
        except Exception as err:
            raise PyRevitException('Error parsing parameter: {} in script file for : {} | {}'.format(param_name,
                                                                                                     self.file_addr,
                                                                                                     err))

        return None


def get_all_subclasses(parent_classes):
    sub_classes = []
    # if super-class, get a list of sub-classes. Otherwise use component_class to create objects.
    for sub_class in parent_classes:
        try:
            derived_classes = sub_class.__subclasses__()
            if len(derived_classes) == 0:
                sub_classes.append(sub_class)
            else:
                sub_classes.extend(derived_classes)
        except AttributeError:
            sub_classes.append(sub_class)
    return sub_classes


def get_sub_folders(search_folder):
    sub_folders = []
    for f in os.listdir(search_folder):
        if op.isdir(op.join(search_folder, f)):
            sub_folders.append(f)
    return sub_folders


def verify_directory(folder):
    """Checks if the folder exists and if not creates the folder.
    Returns OSError on folder making errors."""
    if not op.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as err:
            raise err
    return True


def get_parent_directory(path):
    return op.dirname(path)


def join_strings(path_list):
    if path_list:
        return ';'.join(path_list)
    return ''


# character replacement list for cleaning up file names
SPECIAL_CHARS = {' ': '',
                 '~': '',
                 '!': 'EXCLAM',
                 '@': 'AT',
                 '#': 'NUM',
                 '$': 'DOLLAR',
                 '%': 'PERCENT',
                 '^': '',
                 '&': 'AND',
                 '*': 'STAR',
                 '+': 'PLUS',
                 ';': '', ':': '', ',': '', '\"': '', '{': '', '}': '', '[': '', ']': '', '\(': '', '\)': '',
                 '-': 'MINUS',
                 '=': 'EQUALS',
                 '<': '', '>': '',
                 '?': 'QMARK',
                 '.': 'DOT',
                 '_': 'UNDERS',
                 '|': 'VERT',
                 '\/': '', '\\': ''}


def cleanup_string(input_str):
    # remove spaces and special characters from strings
    for char, repl in SPECIAL_CHARS.items():
        input_str = input_str.replace(char, repl)

    return input_str


def get_revit_instances():
    return len(list(Process.GetProcessesByName(HOST_ADSK_PROCESS_NAME)))


def run_process(proc, cwd=''):
    import subprocess as sp
    return sp.Popen(proc, stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd, shell=True)


def inspect_calling_scope_local_var(variable_name):
    """Traces back the stack to find the variable in the caller local stack.
    Example:
    PyRevitLoader defines __revit__ in builtins and __window__ in locals. Thus, modules have access to
    __revit__ but not to __window__. This function is used to find __window__ in the caller stack.
    """
    frame = inspect.stack()[1][0]
    while variable_name not in frame.f_locals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[variable_name]


def inspect_calling_scope_global_var(variable_name):
    """Traces back the stack to find the variable in the caller local stack.
    Example:
    PyRevitLoader defines __revit__ in builtins and __window__ in locals. Thus, modules have access to
    __revit__ but not to __window__. This function is used to find __window__ in the caller stack.
    """
    frame = inspect.stack()[1][0]
    while variable_name not in frame.f_globals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[variable_name]


def get_interscript_comm_data(param_name):
    """Gets value of a parameter shared between all scripts. (Interscript communication ISC)
    Some settings needs to be set for the current session and should affect the behaviour of all individual scripts
    inside the packages. (e.g. If user activates the DEBUG mode, all scripts should follow and log the debug entries.)
    The information is saved using AppDomain.GetData and SetData in a dictionary parameter (PYREVIT_ISC_DICT_NAME).
    The dictionary is used to minimise the addition of named parameters to the AppDomain. The dictionary then includes
    all the internal parameters and their associated value (e.g. DEBUG_ISC_NAME). This way each script does not need
    to read the usersettings data which reduces file io and saves time.
    """
    # This function returns None if it can not find the parameter. Thus value of None should not be used for params
    data_dict = CURRENT_REVIT_APPDOMAIN.GetData(PYREVIT_ISC_DICT_NAME)
    if data_dict:
        try:
            return data_dict[param_name]
        except KeyError:
            return None
    else:
        return None


def set_interscript_comm_data(param_name, param_value):
    """Sets value of a parameter shared between all scripts. (Interscript communication ISC)
    Some settings needs to be set for the current session and should affect the behaviour of all individual scripts
    inside the packages. (e.g. If user activates the DEBUG mode, all scripts should follow and log the debug entries.)
    The information is saved using AppDomain.GetData and SetData in a dictionary parameter (PYREVIT_ISC_DICT_NAME).
    The dictionary is used to minimise the addition of named parameters to the AppDomain. The dictionary then includes
    all the internal parameters and their associated value (e.g. DEBUG_ISC_NAME). This way each script does not need
    to read the usersettings data which reduces file io and saves time.
    """
    # Get function returns None if it can not find the parameter. Thus value of None should not be used for params
    data_dict = CURRENT_REVIT_APPDOMAIN.GetData(PYREVIT_ISC_DICT_NAME)
    if data_dict:
        data_dict[param_name] = param_value
    else:
        data_dict = {param_name: param_value}

    CURRENT_REVIT_APPDOMAIN.SetData(PYREVIT_ISC_DICT_NAME, data_dict)
