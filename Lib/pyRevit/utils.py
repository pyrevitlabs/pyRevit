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
    # todo
    pass


def get_mutex(mutex_name):
    from System.Threading import Mutex
    stat = Mutex.TryOpenExisting(mutex_name)
    return stat[1]


def set_mutex(mutex_name, status):
    from System.Threading import Mutex
    if status:
        print('setting {}'.format(mutex_name))
        mtx = Mutex(False, mutex_name)
        # mtx.WaitOne(0, False)
        return mtx
    else:
        mtx = get_mutex(mutex_name)
        if mtx:
            mtx.Close()


# todo script option manager (pyrevit will get a command prompt and users can provide switches and options to commands
def get_options_dict():
    pass


# todo add transaction wrapper
