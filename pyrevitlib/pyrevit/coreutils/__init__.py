import os
import os.path as op
import re
import ast
import hashlib
import time
import datetime
import clr
import shutil
from collections import defaultdict

from pyrevit import HOST_APP, PyRevitException

# noinspection PyUnresolvedReferences
from System import AppDomain,  Array, Type
# noinspection PyUnresolvedReferences
from System.Diagnostics import Process
# noinspection PyUnresolvedReferences
from System.Reflection import Assembly, TypeAttributes, MethodAttributes, CallingConventions
# noinspection PyUnresolvedReferences
from System.Reflection.Emit import CustomAttributeBuilder, OpCodes
# noinspection PyUnresolvedReferences
from System.Net import WebClient, WebRequest

# noinspection PyUnresolvedReferences
from Autodesk.Revit.Attributes import RegenerationAttribute, RegenerationOption, TransactionAttribute, TransactionMode


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

    def get_docstring(self):
        doc_str = ast.get_docstring(self.ast_tree)
        if doc_str:
            return doc_str.decode('utf-8')
        return None

    def extract_param(self, param_name):
        try:
            for child in ast.iter_child_nodes(self.ast_tree):
                if hasattr(child, 'targets'):
                    for target in child.targets:
                        if hasattr(target, 'id') and target.id == param_name:
                            param_value = ast.literal_eval(child.value)
                            if isinstance(param_value, str):
                                param_value = param_value.decode('utf-8')
                            return param_value
        except Exception as err:
            raise PyRevitException('Error parsing parameter: {} in script file for : {} | {}'.format(param_name,
                                                                                                     self.file_addr,
                                                                                                     err))

        return None


def get_all_subclasses(parent_classes):
    sub_classes = []
    # if super-class, get a list of sub-classes. Otherwise use component_class to create objects.
    for parent_class in parent_classes:
        try:
            derived_classes = parent_class.__subclasses__()
            if len(derived_classes) == 0:
                sub_classes.append(parent_class)
            else:
                sub_classes.extend(derived_classes)
        except AttributeError:
            sub_classes.append(parent_class)
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
    return folder


def get_parent_directory(path):
    return op.dirname(path)


def join_strings(path_list, separator=';'):
    if path_list:
        return separator.join(path_list)
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


def get_revit_instance_count():
    return len(list(Process.GetProcessesByName(HOST_APP.proc_name)))


def run_process(proc, cwd=''):
    import subprocess
    return subprocess.Popen(proc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, shell=True)


def inspect_calling_scope_local_var(variable_name):
    """Traces back the stack to find the variable in the caller local stack.
    Example:
    PyRevitLoader defines __revit__ in builtins and __window__ in locals. Thus, modules have access to
    __revit__ but not to __window__. This function is used to find __window__ in the caller stack.
    """
    import inspect

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
    import inspect

    frame = inspect.stack()[1][0]
    while variable_name not in frame.f_globals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[variable_name]


def find_loaded_asm(asm_info, by_partial_name=False, by_location=False):
    """

    Args:
        asm_info (str): name or location of the assembly
        by_partial_name (bool): returns all assemblies that include the asm_info
        by_location (bool): returns all assemblies with their location matching asm_info

    Returns:
        list: List of all loaded assemblies matching the provided info
              If only one assembly has been found, it returns the assembly.
              None will be returned if assembly is not loaded.
    """
    loaded_asm_list = []
    for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
        if by_partial_name:
            if asm_info.lower() in unicode(loaded_assembly.GetName().Name).lower():
                loaded_asm_list.append(loaded_assembly)
        elif by_location:
            try:
                if op.normpath(loaded_assembly.Location) == op.normpath(asm_info):
                    loaded_asm_list.append(loaded_assembly)
            except:
                continue
        elif asm_info.lower() == unicode(loaded_assembly.GetName().Name).lower():
            loaded_asm_list.append(loaded_assembly)

    return loaded_asm_list


def load_asm(asm_name):
    return AppDomain.CurrentDomain.Load(asm_name)


def load_asm_file(asm_file):
    return Assembly.LoadFrom(asm_file)


def find_type_by_name(assembly, type_name):
    base_class = assembly.GetType(type_name)
    if base_class is not None:
        return base_class
    else:
        raise PyRevitException('Can not find base class type: {}'.format(type_name))


def make_canonical_name(*args):
    return '.'.join(args)


def get_file_name(file_path):
    return op.splitext(op.basename(file_path))[0]


def get_str_hash(source_str):
    return hashlib.md5(source_str.encode('utf-8', 'ignore')).hexdigest()


def calculate_dir_hash(dir_path, dir_filter, file_filter):
    """Creates a unique hash # to represent state of directory."""
    mtime_sum = 0
    for root, dirs, files in os.walk(dir_path):
        if re.search(dir_filter, op.basename(root), flags=re.IGNORECASE):
            mtime_sum += op.getmtime(root)
            for filename in files:
                if re.search(file_filter, filename, flags=re.IGNORECASE):
                    modtime = op.getmtime(op.join(root, filename))
                    mtime_sum += modtime
    return get_str_hash(unicode(mtime_sum))


def prepare_html_str(input_string):
    return input_string.replace('<', '&clt;').replace('>', '&cgt;')


def reverse_html(input_html):
    return input_html.replace('&clt;', '<').replace('&cgt;', '>')


# def check_internet_connection():
#     client = WebClient()
#     try:
#         client.OpenRead("http://www.google.com")
#         return True
#     except:
#         return False
#


# def check_internet_connection():
    # import urllib2
    #
    # def internet_on():
    #     try:
    #         urllib2.urlopen('http://216.58.192.142', timeout=1)
    #         return True
    #     except urllib2.URLError as err:
    #         return False


def check_internet_connection(timeout=1000):
    def can_access(url_to_open):
        try:
            client = WebRequest.Create(url_to_open)
            client.Method = "HEAD"
            client.Timeout = timeout
            response = client.GetResponse()
            response.GetResponseStream()
            return True
        except:
            return False

    for url in ["http://google.com/", "http://github.com/", "http://bitbucket.com/"]:
        if can_access(url):
            return url

    return False


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def read_source_file(source_file_path):
    try:
        with open(source_file_path, 'r') as code_file:
            return code_file.read()
    except Exception as read_err:
        raise PyRevitException('Error reading source file: {} | {}'.format(source_file_path, read_err))


def create_ext_command_attrs():
    regen_const_info = clr.GetClrType(RegenerationAttribute).GetConstructor(Array[Type]((RegenerationOption,)))
    regen_attr_builder = CustomAttributeBuilder(regen_const_info, Array[object]((RegenerationOption.Manual,)))
    # add TransactionAttribute to type
    trans_constructor_info = clr.GetClrType(TransactionAttribute).GetConstructor(Array[Type]((TransactionMode,)))
    trans_attrib_builder = CustomAttributeBuilder(trans_constructor_info, Array[object]((TransactionMode.Manual,)))

    return [regen_attr_builder, trans_attrib_builder]


def create_type(modulebuilder, type_class, class_name, custom_attr_list, *args):
    # create type builder
    type_builder = modulebuilder.DefineType(class_name, TypeAttributes.Class | TypeAttributes.Public, type_class)

    for custom_attr in custom_attr_list:
        type_builder.SetCustomAttribute(custom_attr)

    # prepare a list of input param types to find the matching constructor
    type_list = []
    param_list = []
    for param in args:
        if type(param) == str:
            type_list.append(type(param))
            param_list.append(param)

    # call base constructor
    ci = type_class.GetConstructor(Array[Type](type_list))
    # create class constructor builder
    const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                   CallingConventions.Standard,
                                                   Array[Type](()))
    # add constructor parameters to stack
    gen = const_builder.GetILGenerator()
    gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack

    # add constructor input params to the stack
    for param in param_list:
        gen.Emit(OpCodes.Ldstr, param)

    gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
    gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Ret)
    type_builder.CreateType()


def show_file_in_explorer(file_path):
    import subprocess
    subprocess.Popen(r'explorer /select,"{}"'.format(os.path.normpath(file_path)))


def open_folder_in_explorer(folder_path):
    import subprocess
    subprocess.Popen(r'explorer /open,"{}"'.format(os.path.normpath(folder_path)))


def open_url(url):
    """Opens url in a new tab in the default web browser."""
    import webbrowser
    return webbrowser.open_new_tab(url)


def fully_remove_tree(dir_path):
    import stat

    # noinspection PyUnusedLocal
    def del_rw(action, name, exc):
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)

    shutil.rmtree(dir_path, onerror=del_rw)


def cleanup_filename(file_name):
    return re.sub('[^\w_.)( -]', '', file_name)


def _inc_or_dec_string(st, shift):
    next_str = ""
    index = len(st) - 1
    carry = shift

    while index >= 0:
        if st[index].isalpha():
            if st[index].islower():
                reset_a = 'a'
                reset_z = 'z'
            else:
                reset_a = 'A'
                reset_z = 'Z'

            curr_digit = (ord(st[index]) + carry)
            if curr_digit < ord(reset_a):
                curr_digit = ord(reset_z) - ((ord(reset_a) - curr_digit) - 1)
                carry = shift
            elif curr_digit > ord(reset_z):
                curr_digit = ord(reset_a) + ((curr_digit - ord(reset_z)) - 1)
                carry = shift
            else:
                carry = 0

            curr_digit = chr(curr_digit)
            next_str += curr_digit

        elif st[index].isdigit():

            curr_digit = int(st[index]) + carry
            if curr_digit > 9:
                curr_digit = 0 + ((curr_digit - 9)-1)
                carry = shift
            elif curr_digit < 0:
                curr_digit = 9 - ((0 - curr_digit)-1)
                carry = shift
            else:
                carry = 0
            next_str += unicode(curr_digit)

        else:
            next_str += st[index]

        index -= 1

    return next_str[::-1]


def increment_str(input_str, step):
    return _inc_or_dec_string(input_str, abs(step))


def decrement_str(input_str, step):
    return _inc_or_dec_string(input_str, -abs(step))


def filter_null_items(src_list):
    return list(filter(bool, src_list))


def reverse_dict(input_dict):
    output_dict = defaultdict(list)
    for key, value in input_dict.items():
        output_dict[value].append(key)
    return output_dict


def pairwise(iterable):
    from itertools import tee, izip
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def timestamp():
    return datetime.datetime.now().strftime("%m%j%H%M%S%f")

def current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")

def current_date():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def is_blank(input_string):
    if input_string and input_string.strip():
        return False
    return True
