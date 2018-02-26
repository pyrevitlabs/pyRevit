"""Misc Helper functions for pyRevit."""

import os
import os.path as op
import re
import ast
import hashlib
import time
import datetime
import shutil
import random
import stat
from collections import defaultdict

from pyrevit import HOST_APP, PyRevitException
from pyrevit.compat import safe_strtype
from pyrevit import framework
from pyrevit import api


# pylama:ignore=D105
DEFAULT_SEPARATOR = ';'


class Timer:
    """Timer class using python native time module.

    Example:
        >>> timer = Timer()
        >>> timer.get_time()
        12
    """

    def __init__(self):
        """Initialize and Start Timer."""
        self.start = time.time()

    def restart(self):
        """Restart Timer."""
        self.start = time.time()

    def get_time(self):
        """Get Elapsed Time."""
        return time.time() - self.start


class ScriptFileParser:
    """Parse python script to extract variables and docstrings.

    Primarily designed to assist pyRevit in determining script configurations
    but can work for any python script.

    Example:
        >>> finder = ScriptFileParser('/path/to/coreutils/__init__.py')
        >>> finder.docstring()
        ... "Misc Helper functions for pyRevit."
        >>> finder.extract_param('SomeValue', [])
        []
    """

    def __init__(self, file_address):
        """Initialize and read provided python script.

        Args:
            file_address (str): python script file path
        """
        self.file_addr = file_address
        try:
            with open(file_address, 'r') as f:
                self.ast_tree = ast.parse(f.read())
        except Exception as err:
            raise PyRevitException('Error parsing script file: {} | {}'
                                   .format(self.file_addr, err))

    def get_docstring(self):
        """Get global docstring."""
        doc_str = ast.get_docstring(self.ast_tree)
        if doc_str:
            return doc_str.decode('utf-8')
        return None

    def extract_param(self, param_name, default_value=None):
        """Find variable and extract its value.

        Args:
            param_name (str): variable name
            default_value (any):
                default value to be returned if variable does not exist

        Returns:
            any: value of the variable or :obj:`None`
        """
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
            raise PyRevitException('Error parsing parameter: {} '
                                   'in script file for : {} | {}'
                                   .format(param_name, self.file_addr, err))

        return default_value


class FileWatcher(object):
    """Simple file version watcher.

    This is a simple utility class to look for changes in a file based on
    its timestamp.

    Example:
        >>> watcher = FileWatcher('/path/to/file.ext')
        >>> watcher.has_changed
        True
    """

    def __init__(self, filepath):
        """Initialize and read timestamp of provided file.

        Args:
            filepath (str): file path
        """
        self._cached_stamp = 0
        self._filepath = filepath
        self.update_tstamp()

    def update_tstamp(self):
        """Update the cached timestamp for later comparison."""
        self._cached_stamp = os.stat(self._filepath).st_mtime

    @property
    def has_changed(self):
        """Compare current file timestamp to the cached timestamp."""
        return os.stat(self._filepath).st_mtime != self._cached_stamp


class SafeDict(dict):
    """Dictionary that does not fail on any key.

    This is a dictionary subclass to help with string formatting with unknown
    key values.

    Example:
        >>> string = '{target} {attr} is {color}.'
        >>> safedict = SafeDict({'target': 'Apple',
        ...                      'attr':   'Color'})
        >>> string.format(safedict)  # will not fail with missing 'color' key
        'Apple Color is {color}.'
    """

    def __missing__(self, key):
        return '{' + key + '}'


def get_all_subclasses(parent_classes):
    """Return all subclasses of a python class.

    Args:
        parent_classes (list): list of python classes

    Returns:
        list: list of python subclasses
    """
    sub_classes = []
    # if super-class, get a list of sub-classes.
    # Otherwise use component_class to create objects.
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
    """Get a list of all subfolders directly inside provided folder.

    Args:
        search_folder (str): folder path

    Returns:
        list: list of subfolder names
    """
    sub_folders = []
    for f in os.listdir(search_folder):
        if op.isdir(op.join(search_folder, f)):
            sub_folders.append(f)
    return sub_folders


def verify_directory(folder):
    """Check if the folder exists and if not create the folder.

    Args:
        folder (str): path of folder to verify

    Returns:
        str: path of verified folder, equals to provided folder

    Raises:
        OSError on folder creation error.
    """
    if not op.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as err:
            raise err
    return folder


def join_strings(str_list, separator=DEFAULT_SEPARATOR):
    """Join strings using provided separator.

    Args:
        str_list (list): list of string values
        separator (str): single separator character,
            defaults to DEFAULT_SEPARATOR

    Returns:
        str: joined string
    """
    if str_list:
        return separator.join(str_list)
    return ''


# character replacement list for cleaning up file names
SPECIAL_CHARS = {' ': '',
                 '~': '',
                 '!': 'EXCLAM',
                 '@': 'AT',
                 '#': 'SHARP',
                 '$': 'DOLLAR',
                 '%': 'PERCENT',
                 '^': '',
                 '&': 'AND',
                 '*': 'STAR',
                 '+': 'PLUS',
                 ';': '', ':': '', ',': '', '\"': '',
                 '{': '', '}': '', '[': '', ']': '', '\(': '', '\)': '',
                 '-': 'MINUS',
                 '=': 'EQUALS',
                 '<': '', '>': '',
                 '?': 'QMARK',
                 '.': 'DOT',
                 '_': 'UNDERS',
                 '|': 'VERT',
                 '\/': '', '\\': ''}


def cleanup_string(input_str):
    """Replace special characters in string with another string.

    This function was created to help cleanup pyRevit command unique names from
    any special characters so C# class names can be created based on those
    unique names.

    ``coreutils.SPECIAL_CHARS`` is the conversion table for this function.

    Args:
        input_str (str): input string to be cleaned

    Example:
        >>> src_str = 'TEST@Some*<value>'
        >>> cleanup_string(src_str)
        "TESTATSomeSTARvalue"
    """
    # remove spaces and special characters from strings
    for char, repl in SPECIAL_CHARS.items():
        input_str = input_str.replace(char, repl)

    return input_str


def get_revit_instance_count():
    """Return number of open host app instances.

    Returns:
        int: number of open host app instances.
    """
    return len(list(framework.Process.GetProcessesByName(HOST_APP.proc_name)))


def run_process(proc, cwd=''):
    """Run shell process silently.

    Args:
        proc (str): process executive name
        cwd (str): current working directory

    Exmaple:
        >>> run_process('notepad.exe', 'c:/')
    """
    import subprocess
    return subprocess.Popen(proc,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=cwd, shell=True)


def inspect_calling_scope_local_var(variable_name):
    """Trace back the stack to find the variable in the caller local stack.

    PyRevitLoader defines __revit__ in builtins and __window__ in locals.
    Thus, modules have access to __revit__ but not to __window__.
    This function is used to find __window__ in the caller stack.

    Args:
        variable_name (str): variable name to look up in caller local scope
    """
    import inspect

    frame = inspect.stack()[1][0]
    while variable_name not in frame.f_locals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[variable_name]


def inspect_calling_scope_global_var(variable_name):
    """Trace back the stack to find the variable in the caller global stack.

    Args:
        variable_name (str): variable name to look up in caller global scope
    """
    import inspect

    frame = inspect.stack()[1][0]
    while variable_name not in frame.f_globals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[variable_name]


def find_loaded_asm(asm_info, by_partial_name=False, by_location=False):
    """Find loaded assembly based on name, partial name, or location.

    Args:
        asm_info (str): name or location of the assembly
        by_partial_name (bool): returns all assemblies that has the asm_info
        by_location (bool): returns all assemblies matching location

    Returns:
        list: List of all loaded assemblies matching the provided info
        If only one assembly has been found, it returns the assembly.
        :obj:`None` will be returned if assembly is not loaded.
    """
    loaded_asm_list = []
    for loaded_assembly in framework.AppDomain.CurrentDomain.GetAssemblies():
        if by_partial_name:
            if asm_info.lower() in \
                    safe_strtype(loaded_assembly.GetName().Name).lower():
                loaded_asm_list.append(loaded_assembly)
        elif by_location:
            try:
                if op.normpath(loaded_assembly.Location) == \
                        op.normpath(asm_info):
                    loaded_asm_list.append(loaded_assembly)
            except Exception:
                continue
        elif asm_info.lower() == \
                safe_strtype(loaded_assembly.GetName().Name).lower():
            loaded_asm_list.append(loaded_assembly)

    return loaded_asm_list


def load_asm(asm_name):
    """Load assembly by name into current domain.

    Args:
        asm_name (str): assembly name

    Returns:
        returns the loaded assembly, None if not loaded.
    """
    return framework.AppDomain.CurrentDomain.Load(asm_name)


def load_asm_file(asm_file):
    """Load assembly by file into current domain.

    Args:
        asm_file (str): assembly file path

    Returns:
        returns the loaded assembly, None if not loaded.
    """
    try:
        return framework.Assembly.LoadFrom(asm_file)
    except Exception:
        return None


def find_type_by_name(assembly, type_name):
    """Find type by name in assembly.

    Args:
        assembly (:obj:`Assembly`): assembly to find the type in
        type_name (str): type name

    Returns:
        returns the type if found.

    Raises:
        :obj:`PyRevitException` if type not found.
    """
    base_class = assembly.GetType(type_name)
    if base_class is not None:
        return base_class
    else:
        raise PyRevitException('Can not find base class type: {}'
                               .format(type_name))


def make_canonical_name(*args):
    """Join arguments with dot creating a unique id.

    Args:
        *args: Variable length argument list of type :obj:`str`

    Returns:
        str: dot separated unique name

    Example:
        >>> make_canonical_name('somename', 'someid', 'txt')
        "somename.someid.txt"
    """
    return '.'.join(args)


def get_file_name(file_path):
    """Return file basename of the given file.

    Args:
        file_path (str): file path
    """
    return op.splitext(op.basename(file_path))[0]


def get_str_hash(source_str):
    """Calculate hash value of given string.

    Current implementation uses :func:`hashlib.md5` hash function.

    Args:
        source_str (str): source str

    Returns:
        str: hash value as string
    """
    return hashlib.md5(source_str.encode('utf-8', 'ignore')).hexdigest()


def calculate_dir_hash(dir_path, dir_filter, file_filter):
    r"""Create a unique hash to represent state of directory.

    Args:
        dir_path (str): target directory
        dir_filter (str): exclude directories matching this regex
        file_filter (str): exclude files matching this regex

    Returns:
        str: hash value as string

    Example:
        >>> calculate_dir_hash(source_path, '\.extension', '\.json')
        "1a885a0cae99f53d6088b9f7cee3bf4d"
    """
    mtime_sum = 0
    for root, dirs, files in os.walk(dir_path):
        if re.search(dir_filter, op.basename(root), flags=re.IGNORECASE):
            mtime_sum += op.getmtime(root)
            for filename in files:
                if re.search(file_filter, filename, flags=re.IGNORECASE):
                    modtime = op.getmtime(op.join(root, filename))
                    mtime_sum += modtime
    return get_str_hash(safe_strtype(mtime_sum))


def prepare_html_str(input_string):
    """Reformat html string and prepare for pyRevit output window.

    pyRevit output window renders html content. But this means that < and >
    characters in outputs from python (e.g. <class at xxx>) will be treated
    as html tags. To avoid this, all <> characters that are defining
    html content need to be replaced with special phrases. pyRevit output
    later translates these phrases back in to < and >. That is how pyRevit
    ditinquishes between <> printed from python and <> that define html.

    Args:
        input_string (str): input html string

    Example:
        >>> prepare_html_str('<p>Some text</p>')
        "&clt;p&cgt;Some text&clt;/p&cgt;"
    """
    return input_string.replace('<', '&clt;').replace('>', '&cgt;')


def reverse_html(input_html):
    """Reformat codified pyRevit output html string back to normal html.

    pyRevit output window renders html content. But this means that < and >
    characters in outputs from python (e.g. <class at xxx>) will be treated
    as html tags. To avoid this, all <> characters that are defining
    html content need to be replaced with special phrases. pyRevit output
    later translates these phrases back in to < and >. That is how pyRevit
    ditinquishes between <> printed from python and <> that define html.

    Args:
        input_html (str): input codified html string

    Example:
        >>> prepare_html_str('&clt;p&cgt;Some text&clt;/p&cgt;')
        "<p>Some text</p>"
    """
    return input_html.replace('&clt;', '<').replace('&cgt;', '>')


# def check_internet_connection():
#     client = framework.WebClient()
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
    """Check if internet connection is available.

    Pings a few well-known websites to check if internet connection is present.

    Args:
        timeout (int): timeout in milliseconds

    Returns:
        bool: True if internet connection is present.
    """
    def can_access(url_to_open):
        try:
            client = framework.WebRequest.Create(url_to_open)
            client.Method = "HEAD"
            client.Timeout = timeout
            client.Proxy = framework.WebProxy.GetDefaultProxy()
            response = client.GetResponse()
            response.GetResponseStream()
            return True
        except Exception:
                return False

    for url in ["http://google.com/",
                "http://github.com/",
                "http://bitbucket.com/"]:
        if can_access(url):
            return url

    return False


def touch(fname, times=None):
    """Update the timestamp on the given file.

    Args:
        fname (str): target file path
        times (int): number of times to touch the file
    """
    with open(fname, 'a'):
        os.utime(fname, times)


def read_source_file(source_file_path):
    """Read text file and return contents.

    Args:
        source_file_path (str): target file path

    Returns:
        str: file contents

    Raises:
        :obj:`PyRevitException` on read error
    """
    try:
        with open(source_file_path, 'r') as code_file:
            return code_file.read()
    except Exception as read_err:
        raise PyRevitException('Error reading source file: {} | {}'
                               .format(source_file_path, read_err))


def create_ext_command_attrs():
    """Create dotnet attributes for Revit extenrnal commads.

    This method is used in creating custom dotnet types for pyRevit commands
    and compiling them into a DLL assembly. Current implementation sets
    ``RegenerationOption.Manual`` and ``TransactionMode.Manual``

    Returns:
        list: list of :obj:`CustomAttributeBuilder` for
        :obj:`RegenerationOption` and :obj:`TransactionMode` attributes.
    """
    regen_const_info = \
        framework.clr.GetClrType(api.Attributes.RegenerationAttribute) \
        .GetConstructor(
               framework.Array[framework.Type](
                   (api.Attributes.RegenerationOption,)
                   )
               )

    regen_attr_builder = \
        framework.CustomAttributeBuilder(
            regen_const_info,
            framework.Array[object](
                (api.Attributes.RegenerationOption.Manual,)
                )
            )

    # add TransactionAttribute to framework.Type
    trans_constructor_info = \
        framework.clr.GetClrType(api.Attributes.TransactionAttribute) \
        .GetConstructor(
               framework.Array[framework.Type](
                   (api.Attributes.TransactionMode,)
                   )
               )

    trans_attrib_builder = \
        framework.CustomAttributeBuilder(
            trans_constructor_info,
            framework.Array[object](
                (api.Attributes.TransactionMode.Manual,)
                )
            )

    return [regen_attr_builder, trans_attrib_builder]


def create_type(modulebuilder,
                type_class, class_name, custom_attr_list, *args):
    """Create a dotnet type for a pyRevit command.

    See ``baseclasses.cs`` code for the template pyRevit command dotnet type
    and its constructor default arguments that must be provided here.

    Args:
        modulebuilder (:obj:`ModuleBuilder`): dotnet module builder
        type_class (type): source dotnet type for the command
        class_name (str): name for the new type
        custom_attr_list (:obj:`list`): list of dotnet attributes for the type
        *args: list of arguments to be used with type constructor

    Returns:
        type: returns created dotnet type

    Example:
        >>> asm_builder = AppDomain.CurrentDomain.DefineDynamicAssembly(
        ... win_asm_name, AssemblyBuilderAccess.RunAndSave, filepath
        ... )
        >>> module_builder = asm_builder.DefineDynamicModule(
        ... ext_asm_file_name, ext_asm_full_file_name
        ... )
        >>> create_type(
        ... module_builder,
        ... PyRevitCommand,
        ... "PyRevitSomeCommandUniqueName",
        ... coreutils.create_ext_command_attrs(),
        ... [scriptpath, atlscriptpath, searchpath, helpurl, name,
        ... bundle, extension, uniquename, False, False])
        <type PyRevitSomeCommandUniqueName>
    """
    # create type builder
    type_builder = \
        modulebuilder.DefineType(
            class_name,
            framework.TypeAttributes.Class | framework.TypeAttributes.Public,
            type_class
            )

    for custom_attr in custom_attr_list:
        type_builder.SetCustomAttribute(custom_attr)

    # prepare a list of input param types to find the matching constructor
    type_list = []
    param_list = []
    for param in args:
        if type(param) == str \
                or type(param) == int:
            type_list.append(type(param))
            param_list.append(param)

    # call base constructor
    ci = type_class.GetConstructor(framework.Array[framework.Type](type_list))
    # create class constructor builder
    const_builder = \
        type_builder.DefineConstructor(framework.MethodAttributes.Public,
                                       framework.CallingConventions.Standard,
                                       framework.Array[framework.Type](()))
    # add constructor parameters to stack
    gen = const_builder.GetILGenerator()
    gen.Emit(framework.OpCodes.Ldarg_0)  # Load "this" onto eval stack

    # add constructor input params to the stack
    for param_type, param in zip(type_list, param_list):
        if param_type == str:
            gen.Emit(framework.OpCodes.Ldstr, param)
        elif param_type == int:
            gen.Emit(framework.OpCodes.Ldc_I4, param)

    # call base constructor (consumes "this" and the created stack)
    gen.Emit(framework.OpCodes.Call, ci)
    # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(framework.OpCodes.Nop)
    gen.Emit(framework.OpCodes.Nop)
    gen.Emit(framework.OpCodes.Nop)
    gen.Emit(framework.OpCodes.Ret)
    type_builder.CreateType()


def open_folder_in_explorer(folder_path):
    """Open given folder in Windows Explorer.

    Args:
        folder_path (str): directory path
    """
    import subprocess
    subprocess.Popen(r'explorer /open,"{}"'
                     .format(os.path.normpath(folder_path)))


def fully_remove_dir(dir_path):
    """Remove directory recursively.

    Args:
        dir_path (str): directory path
    """
    def del_rw(action, name, exc):
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)

    shutil.rmtree(dir_path, onerror=del_rw)


def cleanup_filename(file_name):
    """Cleanup file name from special characters.

    Args:
        file_name (str): file name

    Returns:
        str: cleaned up file name

    Example:
        >>> cleanup_filename('Myfile-(3).txt')
        "Myfile3.txt"
    """
    return re.sub('[^\w_.)( -]', '', file_name)


def _inc_or_dec_string(str_id, shift):
    """Increment or decrement identifier.

    Args:
        str_id (str): identifier e.g. A310a
        shift (int): number of steps to change the identifier

    Returns:
        str: modified identifier

    Example:
        >>> _inc_or_dec_string('A319z')
        'A320a'
    """
    next_str = ""
    index = len(str_id) - 1
    carry = shift

    while index >= 0:
        if str_id[index].isalpha():
            if str_id[index].islower():
                reset_a = 'a'
                reset_z = 'z'
            else:
                reset_a = 'A'
                reset_z = 'Z'

            curr_digit = (ord(str_id[index]) + carry)
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

        elif str_id[index].isdigit():

            curr_digit = int(str_id[index]) + carry
            if curr_digit > 9:
                curr_digit = 0 + ((curr_digit - 9)-1)
                carry = shift
            elif curr_digit < 0:
                curr_digit = 9 - ((0 - curr_digit)-1)
                carry = shift
            else:
                carry = 0
            next_str += safe_strtype(curr_digit)

        else:
            next_str += str_id[index]

        index -= 1

    return next_str[::-1]


def increment_str(input_str, step):
    """Incremenet identifier.

    Args:
        input_str (str): identifier e.g. A310a
        step (int): number of steps to change the identifier

    Returns:
        str: modified identifier

    Example:
        >>> increment_str('A319z')
        'A320a'
    """
    return _inc_or_dec_string(input_str, abs(step))


def decrement_str(input_str, step):
    """Decrement identifier.

    Args:
        input_str (str): identifier e.g. A310a
        step (int): number of steps to change the identifier

    Returns:
        str: modified identifier

    Example:
        >>> decrement_str('A310a')
        'A309z'
    """
    return _inc_or_dec_string(input_str, -abs(step))


def filter_null_items(src_list):
    """Remove None items in the given list.

    Args:
        src_list (:obj:`list`): list of any items

    Returns:
        :obj:`list`: cleaned list
    """
    return list(filter(bool, src_list))


def reverse_dict(input_dict):
    """Reverse the key, value pairs.

    Args:
        input_dict (:obj:`dict`): source ordered dict

    Returns:
        :obj:`defaultdict`: reversed dictionary

    Example:
        >>> reverse_dict({1: 2, 3: 4})
        defaultdict(<type 'list'>, {2: [1], 4: [3]})
    """
    output_dict = defaultdict(list)
    for key, value in input_dict.items():
        output_dict[value].append(key)
    return output_dict


def timestamp():
    """Return timestamp for current time.

    Returns:
        str: timestamp in string format

    Example:
        >>> timestamp()
        '01003075032506808'
    """
    return datetime.datetime.now().strftime("%m%j%H%M%S%f")


def current_time():
    """Return formatted current time.

    Current implementation uses %H:%M:%S to format time.

    Returns:
        str: formatted current time.

    Example:
        >>> current_time()
        '07:50:53'
    """
    return datetime.datetime.now().strftime("%H:%M:%S")


def current_date():
    """Return formatted current date.

    Current implementation uses %Y-%m-%d to format date.

    Returns:
        str: formatted current date.

    Example:
        >>> current_date()
        '2018-01-03'
    """
    return datetime.datetime.now().strftime("%Y-%m-%d")


def is_blank(input_string):
    """Check if input string is blank (multiple white spaces is blank).

    Args:
        input_string (str): input string

    Returns:
        bool: True if string is blank

    Example:
        >>> is_blank('   ')
        True
    """
    if input_string and input_string.strip():
        return False
    return True


def is_url_valid(url_string):
    """Check if given URL is in valid format.

    Args:
        url_string (str): URL string

    Returns:
        bool: True if URL is in valid format

    Example:
        >>> is_url_valid('https://www.google.com')
        True
    """
    regex = re.compile(
            r'^(?:http|ftp)s?://'                   # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
            r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'                           # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'                            # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return regex.match(url_string)


def reformat_string(orig_str, orig_format, new_format):
    """Reformat a string into a new format.

    Extracts information from a string based on a given pattern,
    and recreates a new string based on the given new pattern.

    Args:
        orig_str (str): Original string to be reformatted
        orig_format (str): Pattern of the original str (data to be extracted)
        new_format (str): New pattern (how to recompose the data)

    Returns:
        str: Reformatted string

    Example:
        >>> reformat_string('150 - FLOOR/CEILING - WD - 1 HR - FLOOR ASSEMBLY',
                            '{section} - {loc} - {mat} - {rating} - {name}',
                            '{section}:{mat}:{rating} - {name} ({loc})'))
        '150:WD:1 HR - FLOOR ASSEMBLY (FLOOR/CEILING)'
    """
    # find the tags
    tag_extractor = re.compile('{(.*?)}')
    tags = tag_extractor.findall(orig_format)

    # replace the tags with regex patterns
    # to create a regex pattern that finds values
    tag_replacer = re.compile('{.*?}')
    value_extractor_pattern = tag_replacer.sub('(.+)', orig_format)
    # find all values
    value_extractor = re.compile(value_extractor_pattern)
    values = value_extractor.findall(orig_str)
    if len(values) > 0:
        values = values[0]

    # create a dictionary of tags and values
    reformat_dict = {}
    for k, v in zip(tags, values):
        reformat_dict[k] = v

    # use dictionary to reformat the string into new
    return new_format.format(**reformat_dict)


def get_mapped_drives_dict():
    """Return a dictionary of currently mapped network drives."""
    searcher = framework.ManagementObjectSearcher(
        "root\\CIMV2",
        "SELECT * FROM Win32_MappedLogicalDisk"
        )

    return {x['DeviceID']: x['ProviderName'] for x in searcher.Get()}


def dletter_to_unc(dletter_path):
    """Convert drive letter path into UNC path of that drive.

    Args:
        dletter_path (str): drive letter path

    Returns:
        str: UNC path

    Example:
        >>> # assuming J: is mapped to //filestore/server/jdrive
        >>> dletter_to_unc('J:/somefile.txt')
        '//filestore/server/jdrive/somefile.txt'
    """
    drives = get_mapped_drives_dict()
    dletter = dletter_path[:2]
    for mapped_drive, server_path in drives.items():
        if dletter.lower() == mapped_drive.lower():
            return dletter_path.replace(dletter, server_path)


def unc_to_dletter(unc_path):
    """Convert UNC path into drive letter path.

    Args:
        unc_path (str): UNC path

    Returns:
        str: drive letter path

    Example:
        >>> # assuming J: is mapped to //filestore/server/jdrive
        >>> unc_to_dletter('//filestore/server/jdrive/somefile.txt')
        'J:/somefile.txt'
    """
    drives = get_mapped_drives_dict()
    for mapped_drive, server_path in drives.items():
        if server_path in unc_path:
            return unc_path.replace(server_path, mapped_drive)


def random_color():
    """Return a random color channel value (between 0 and 255)."""
    return random.randint(0, 255)


def random_alpha():
    """Return a random alpha value (between 0 and 1.00)."""
    return round(random.random(), 2)


def random_hex_color():
    """Return a random color in hex format.

    Example:
        >>> random_hex_color()
        '#FF0000'
    """
    return '#%02X%02X%02X' % (random_color(),
                              random_color(),
                              random_color())


def random_rgb_color():
    """Return a random color in rgb format.

    Example:
        >>> random_rgb_color()
        'rgb(255, 0, 0)'
    """
    return 'rgb(%d, %d, %d)' % (random_color(),
                                random_color(),
                                random_color())


def random_rgba_color():
    """Return a random color in rgba format.

    Example:
        >>> random_rgba_color()
        'rgba(255, 0, 0, 0.5)'
    """
    return 'rgba(%d, %d, %d, %.2f)' % (random_color(),
                                       random_color(),
                                       random_color(),
                                       random_alpha())


def exract_range(formatted_str):
    """Extract range from formatted string.

    String must be formatted as below
    A103            No range
    A103-A106       A103 to A106
    A103:A106       A103 to A106
    A103,A105a      A103 and A105a
    A103;A105a      A103 and A105a

    Args:
        formatted_str (str): string specifying range

    Returns:
        list: list of names in the specified range

    Example:
        >>> exract_range('A103:A106')
        ['A103', 'A104', 'A105', 'A106']
        >>> exract_range('S203-S206')
        ['S203', 'S204', 'S205', 'S206']
        >>> exract_range('M00A,M00B')
        ['M00A', 'M00B']
    """
    for rchar, rchartype in {':': 'range', '-': 'range',
                             ',': 'list', ';': 'list'}.items():
        if rchar in formatted_str:
            if rchartype == 'range' \
                    and formatted_str.count(rchar) == 1:
                items = []
                start, end = formatted_str.split(rchar)
                items.append(start)
                item = increment_str(start, 1)
                while item != end:
                    items.append(item)
                    item = increment_str(item, 1)
                items.append(end)
                return items
            elif rchartype == 'list':
                return [x.strip() for x in formatted_str.split(rchar)]
    return [formatted_str]
