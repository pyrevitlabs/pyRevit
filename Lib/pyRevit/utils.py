class Timer:
    """Timer class using python native time module."""
    def __init__(self):
        import time
        self.start = time.time()

    def restart(self):
        import time
        self.start = time.time()

    def get_time_hhmmss(self):
        import time
        return "%02.2f seconds" % (time.time() - self.start)


class ScriptFileContents:
    def __init__(self, file_address):
        self.filecontents = ''
        with open(file_address, 'r') as f:
            self.filecontents = f.readlines()

    def extract_param(self, param):
        import re
        param_str_found = False
        param_str = ''
        param_finder = re.compile(param + '\s*=\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        param_finder_ex = re.compile('^\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        for thisline in self.filecontents:
            if not param_str_found:
                values = param_finder.findall(thisline)
                if values:
                    param_str = values[0]
                    param_str_found = True
                continue
            elif param_str_found:
                values = param_finder_ex.findall(thisline)
                if values:
                    param_str += values[0]
                    continue
                break
        cleaned_param_str = param_str.replace('\\\'', '\'').replace('\\"', '\"').replace('\\n', '\n').replace('\\t', '\t')
        if '' != cleaned_param_str:
            return cleaned_param_str
        else:
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


def assert_folder(folder):
    """Checks if the folder exists and if not creates the folder.
    Returns OSError on folder making errors."""
    import os
    if not op.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as err:
            raise err
    return True


def get_parent_directory(path):
    import os.path as op
    return op.dirname(path)


def run_process(proc, cwd=''):
    import subprocess
    return subprocess.Popen(proc, stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd, shell=True)


def join_paths(path_list):
    return ';'.join(path_list)


def cleanup_string(input_str):
    # remove spaces and special characters from strings
    from .config import SPECIAL_CHARS
    for char, repl in SPECIAL_CHARS.items():
        input_str = input_str.replace(char, repl)

    return input_str


def get_temp_file():
    """Returns a filename to be used by a user script to store temporary information.
    Temporary files are saved in USER_TEMP_DIR.
    """
    # todo temporary file
    pass


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
    from .config import PYREVIT_ISC_DICT_NAME, CURRENT_REVIT_APPDOMAIN
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
    from .config import PYREVIT_ISC_DICT_NAME, CURRENT_REVIT_APPDOMAIN
    data_dict = CURRENT_REVIT_APPDOMAIN.GetData(PYREVIT_ISC_DICT_NAME)
    if data_dict:
        data_dict[param_name] = param_value
    else:
        data_dict = {param_name: param_value}

    CURRENT_REVIT_APPDOMAIN.SetData(PYREVIT_ISC_DICT_NAME, data_dict)


# todo script option manager (pyrevit will get a command prompt and users can provide switches and options to commands
def get_options_dict():
    pass


# todo add transaction wrapper
def transaction_wrapper():
    pass