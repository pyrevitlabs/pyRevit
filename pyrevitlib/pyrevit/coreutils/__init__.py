"""Misc Helper functions for pyRevit.

Example:
    >>> from pyrevit import coreutils
    >>> coreutils.cleanup_string('some string')
"""
#pylint: disable=invalid-name
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
import codecs
import math
import socket
from collections import defaultdict

#pylint: disable=E0401
from pyrevit import HOST_APP, PyRevitException
from pyrevit import compat
from pyrevit.compat import safe_strtype
from pyrevit.compat import winreg as wr
from pyrevit import framework
from pyrevit import api

# RE: https://github.com/eirannejad/pyRevit/issues/413
# import uuid
from System import Guid

#pylint: disable=W0703,C0302
DEFAULT_SEPARATOR = ';'

# extracted from
# https://www.fileformat.info/info/unicode/block/general_punctuation/images.htm
UNICODE_NONPRINTABLE_CHARS = [
    u'\u2000', u'\u2001', u'\u2002', u'\u2003', u'\u2004', u'\u2005', u'\u2006',
    u'\u2007', u'\u2008', u'\u2009', u'\u200A', u'\u200B', u'\u200C', u'\u200D',
    u'\u200E', u'\u200F',
    u'\u2028', u'\u2029', u'\u202A', u'\u202B', u'\u202C', u'\u202D', u'\u202E',
    u'\u202F',
    u'\u205F', u'\u2060',
    u'\u2066', u'\u2067', u'\u2068', u'\u2069', u'\u206A', u'\u206B', u'\u206C'
    u'\u206D', u'\u206E', u'\u206F'
    ]


class Timer(object):
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


class ScriptFileParser(object):
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
        self.ast_tree = None
        self.file_addr = file_address
        with codecs.open(file_address, 'r', 'utf-8') as source_file:
            contents = source_file.read()
            if contents:
                self.ast_tree = ast.parse(contents)

    def extract_node_value(self, node):
        """Manual extraction of values from node"""
        if isinstance(node, ast.Assign):
            node_value = node.value
        else:
            node_value = node

        if isinstance(node_value, ast.Num):
            return node_value.n
        elif compat.PY2 and isinstance(node_value, ast.Name):
            return node_value.id
        elif compat.PY3 and isinstance(node_value, ast.NameConstant):
            return node_value.value
        elif isinstance(node_value, ast.Str):
            return node_value.s
        elif isinstance(node_value, ast.List):
            return node_value.elts
        elif isinstance(node_value, ast.Dict):
            return {self.extract_node_value(k):self.extract_node_value(v)
                    for k, v in zip(node_value.keys, node_value.values)}

    def get_docstring(self):
        """Get global docstring."""
        if self.ast_tree:
            doc_str = ast.get_docstring(self.ast_tree)
            if doc_str:
                return doc_str.decode('utf-8')

    def extract_param(self, param_name, default_value=None):
        """Find variable and extract its value.

        Args:
            param_name (str): variable name
            default_value (any):
                default value to be returned if variable does not exist

        Returns:
            any: value of the variable or :obj:`None`
        """
        if self.ast_tree:
            try:
                for node in ast.iter_child_nodes(self.ast_tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if hasattr(target, 'id') \
                                    and target.id == param_name:
                                return ast.literal_eval(node.value)
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
            if not derived_classes:
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
    for sub_folder in os.listdir(search_folder):
        if op.isdir(op.join(search_folder, sub_folder)):
            sub_folders.append(sub_folder)
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
        if any(not isinstance(x, str) for x in str_list):
            str_list = [str(x) for x in str_list]
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
                 '{': '', '}': '', '[': '', ']': '', r'\(': '', r'\)': '',
                 '-': 'MINUS',
                 '=': 'EQUALS',
                 '<': '', '>': '',
                 '?': 'QMARK',
                 '.': 'DOT',
                 '_': 'UNDERS',
                 '|': 'VERT',
                 r'\/': '', '\\': ''}


def cleanup_string(input_str, skip=None):
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
        if skip and char in skip:
            continue
        input_str = input_str.replace(char, repl)

    return input_str


def get_revit_instance_count():
    """Return number of open host app instances.

    Returns:
        int: number of open host app instances.
    """
    return len(list(framework.Process.GetProcessesByName(HOST_APP.proc_name)))


def run_process(proc, cwd='C:'):
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


def get_canonical_parts(canonical_string):
    """Splots argument using dot, returning all composing parts.

    Args:
        canonical_string(:obj:`str`): Source string e.g. "Config.SubConfig"

    Returns:
        list[:obj:`str`]: list of composing parts

    Example:
        >>> get_canonical_parts("Config.SubConfig")
        ['Config', 'SubConfig']
    """
    return canonical_string.split('.')


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
    for root, dirs, files in os.walk(dir_path): #pylint: disable=W0612
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
    distinquishes between <> printed from python and <> that define html.

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
    distinquishes between <> printed from python and <> that define html.

    Args:
        input_html (str): input codified html string

    Example:
        >>> prepare_html_str('&clt;p&cgt;Some text&clt;/p&cgt;')
        "<p>Some text</p>"
    """
    return input_html.replace('&clt;', '<').replace('&cgt;', '>')


def escape_for_html(input_string):
    return input_string.replace('<', '&lt;').replace('>', '&gt;')


# def check_internet_connection():
    # import urllib2
    #
    # def internet_on():
    #     try:
    #         urllib2.urlopen('http://216.58.192.142', timeout=1)
    #         return True
    #     except urllib2.URLError as err:
    #         return False


def can_access_url(url_to_open, timeout=1000):
    """Check if url is accessible within timeout.

    Args:
        url_to_open (str): url to check access for
        timeout (int): timeout in milliseconds

    Returns:
        bool: true if accessible
    """
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


def read_url(url_to_open):
    """Get the url and return response.

    Args:
        url_to_open (str): url to check access for
    """
    client = framework.WebClient()
    return client.DownloadString(url_to_open)


def check_internet_connection(timeout=1000):
    """Check if internet connection is available.

    Pings a few well-known websites to check if internet connection is present.

    Args:
        timeout (int): timeout in milliseconds

    Returns:
        url if internet connection is present, None if no internet.
    """
    solid_urls = ["http://google.com/",
                  "http://github.com/",
                  "http://bitbucket.com/",
                  "http://airtable.com/",
                  "http://todoist.com/",
                  "http://stackoverflow.com/",
                  "http://twitter.com/",
                  "http://youtube.com/"]
    random.shuffle(solid_urls)
    for url in solid_urls:
        if can_access_url(url, timeout):
            return url

    return None


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


def open_folder_in_explorer(folder_path):
    """Open given folder in Windows Explorer.

    Args:
        folder_path (str): directory path
    """
    import subprocess
    subprocess.Popen(r'explorer /open,"{}"'
                     .format(os.path.normpath(folder_path)))


def show_entry_in_explorer(entry_path):
    """Show given entry in Windows Explorer.

    Args:
        entry_path (str): directory or file path
    """
    import subprocess
    subprocess.Popen(r'explorer /select,"{}"'
                     .format(os.path.normpath(entry_path)))


def fully_remove_dir(dir_path):
    """Remove directory recursively.

    Args:
        dir_path (str): directory path
    """
    def del_rw(action, name, exc):   #pylint: disable=W0613
        """Force delete entry."""
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)

    shutil.rmtree(dir_path, onerror=del_rw)


def cleanup_filename(file_name, windows_safe=False):
    """Cleanup file name from special characters.

    Args:
        file_name (str): file name

    Returns:
        str: cleaned up file name

    Example:
        >>> cleanup_filename('Myfile-(3).txt')
        "Myfile(3).txt"

        >>> cleanup_filename('Perforations 1/8" (New)')
        "Perforations 18 (New).txt"
    """
    if windows_safe:
        return re.sub(r'[\/:*?"<>|]', '', file_name)
    else:
        return re.sub(r'[^\w_.() -#]|["]', '', file_name)


def _inc_or_dec_string(str_id, shift, refit=False, logger=None):
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
    # if no shift, return given string
    if shift == 0:
        return str_id

    # otherwise lets process the shift
    next_str = ""
    index = len(str_id) - 1
    carry = shift

    while index >= 0:
        # pick chars from right
        # A1.101a <--
        this_char = str_id[index]

        # determine character range (# of chars, starting index)
        if this_char.isdigit():
            char_range = ('0', '9')
        elif this_char.isalpha():
            # if this_char.isupper()
            char_range = ('A', 'Z')
            if this_char.islower():
                char_range = ('a', 'z')
        else:
            next_str += this_char
            index -= 1
            continue

        # get character range properties
        direction = int(carry / abs(carry)) if carry != 0 else 1
        start_char, end_char = \
            char_range if direction > 0 else char_range[::-1]
        char_steps = abs(ord(end_char) - ord(start_char)) + 1
        # calculate offset

        # positive carry -> start_char=0    end_char=9
        # +----------++        ++          +  char_steps
        # +--------+                          dist
        #          +---------------+          carry (abs)
        # 01234567[8]9012345678901[2]3456789
        # ----------------------+==+          offset

        # negative carry -> start_char=9    end_char=0
        # +----------++        ++          +  char_steps
        # +-------+                           dist
        #         +---------------+           carry (abs)
        # 9876543[2]1098765432109[8]76543210
        # ----------------------+=+           offset

        dist = abs(ord(this_char) - ord(start_char))
        offset = (dist + abs(carry)) % char_steps
        next_char = chr(ord(start_char) + (offset * direction))
        next_str += next_char
        carry = int((dist + abs(carry)) / char_steps) * direction
        if logger:
            logger.debug(
                '\"{}\" index={} start_char=\"{}\" end_char=\"{}\" '
                'next_carry={} direction={} dist={} offset={} next_char=\"{}\"'
                .format(
                    this_char,
                    index,
                    start_char,
                    end_char,
                    carry,
                    direction,
                    dist,
                    offset,
                    next_char))
        index -= 1
        # refit the final value
        # 009 --> 9
        # ZZA --> ZA
        if refit and index == -1:
            if carry > 0:
                str_id = start_char + str_id
                if start_char.isalpha():
                    carry -= 1
                index = 0
            elif direction == -1:
                if next_str.endswith(start_char):
                    next_str = next_str[:-1]
                else:
                    while next_str.endswith(end_char):
                        next_str = next_str[:-1]

    return next_str[::-1]


def increment_str(input_str, step=1, expand=False):
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
    return _inc_or_dec_string(input_str, abs(step), refit=expand)


def decrement_str(input_str, step=1, shrink=False):
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
    return _inc_or_dec_string(input_str, -abs(step), refit=shrink)


def extend_counter(input_str, upper=True, use_zero=False):
    """Add a new level to identifier. e.g. A310 -> A310A

    Args:
        input_str (str): identifier e.g. A310
        upper (bool): use UPPERCASE characters for extension
        use_zero (bool): start from 0 for numeric extension

    Returns:
        str: extended identifier

    Example:
        >>> extend_counter('A310')
        'A310A'
        >>> extend_counter('A310A', use_zero=True)
        'A310A0'
    """
    if input_str[-1].isdigit():
        return input_str + ("A" if upper else "a")
    else:
        return input_str + ("0" if use_zero else "1")


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
    tag_extractor = re.compile('{(.+?)}')
    tags = tag_extractor.findall(orig_format)

    # replace the tags with regex patterns
    # to create a regex pattern that finds values
    tag_replacer = re.compile('{.+?}')
    value_extractor_pattern = tag_replacer.sub('(.+)', orig_format)
    # find all values
    value_extractor = re.compile(value_extractor_pattern)
    match = value_extractor.match(orig_str)
    values = match.groups()

    # create a dictionary of tags and values
    reformat_dict = {}
    for key, value in zip(tags, values):
        reformat_dict[key] = value

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


def extract_range(formatted_str, max_range=500):
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
    for rchar, rchartype in {'::': 'range', '--': 'range',
                             ',': 'list', ';': 'list'}.items():
        if rchar in formatted_str:
            if rchartype == 'range' \
                    and formatted_str.count(rchar) == 1:
                items = []
                start, end = formatted_str.split(rchar)
                assert len(start) == len(end), \
                    'Range start and end must have same length'
                items.append(start)
                item = increment_str(start, 1)
                safe_counter = 0
                while item != end:
                    items.append(item)
                    item = increment_str(item, 1)
                    safe_counter += 1
                    assert safe_counter < max_range, 'Max range reached.'
                items.append(end)
                return items
            elif rchartype == 'list':
                return [x.strip() for x in formatted_str.split(rchar)]
    return [formatted_str]


def check_encoding_bom(filename, bom_bytes=codecs.BOM_UTF8):
    """Check if given file contains the given BOM bytes at the start

    Args:
        filename (str): file path
        bom_bytes (bytes, optional): BOM bytes to check
    """
    with open(filename, 'rb') as rtfile:
        return rtfile.read()[:len(bom_bytes)] == bom_bytes


def has_nonprintable(input_str):
    """Check input string for non-printable characters.

    Args:
        input_str (str): input string

    Returns:
        bool: True if contains non-printable characters
    """
    return any([x in input_str for x in UNICODE_NONPRINTABLE_CHARS])


def get_enum_values(enum_type):
    """Returns enum values."""
    return framework.Enum.GetValues(enum_type)


def get_enum_value(enum_type, value_string):
    """Return enum value matching given value string (case insensitive)"""
    for ftype in get_enum_values(enum_type):
        if str(ftype).lower() == value_string.lower():
            return ftype


def get_enum_none(enum_type):
    """Returns the None value in given Enum."""
    for val in get_enum_values(enum_type):
        if str(val) == 'None':
            return val


def extract_guid(source_str):
    """Extract GUID number from a string."""
    guid_match = re.match(".*([0-9A-Fa-f]{8}"
                          "[-][0-9A-Fa-f]{4}"
                          "[-][0-9A-Fa-f]{4}"
                          "[-][0-9A-Fa-f]{4}"
                          "[-][0-9A-Fa-f]{12}).*", source_str)
    if guid_match:
        return guid_match.groups()[0]


def format_hex_rgb(rgb_value):
    """Formats rgb value as #RGB value string."""
    if isinstance(rgb_value, str):
        if not rgb_value.startswith('#'):
            return '#%s' % rgb_value
        else:
            return rgb_value
    elif isinstance(rgb_value, int):
        return '#%x' % rgb_value


def new_uuid():
    """Create a new UUID (using dotnet Guid.NewGuid)"""
    # RE: https://github.com/eirannejad/pyRevit/issues/413
    # return uuid.uuid1()
    return str(Guid.NewGuid())


def is_box_visible_on_screens(left, top, width, height):
    """Check if given box is visible on any screen."""
    bounds = \
        framework.Drawing.Rectangle(
            framework.Convert.ToInt32(0 if math.isnan(left) else left),
            framework.Convert.ToInt32(0 if math.isnan(top) else top),
            framework.Convert.ToInt32(0 if math.isnan(width) else width),
            framework.Convert.ToInt32(0 if math.isnan(height) else height)
            )
    for scr in framework.Forms.Screen.AllScreens:
        if bounds.IntersectsWith(scr.Bounds):
            return True
    return False


def fuzzy_search_ratio(target_string, sfilter, regex=False):
    """Match target string against the filter and return a match ratio.

    Args:
        target_string (str): target string
        sfilter (str): search term
        regex (bool): treat the sfilter as regular expression pattern

    Returns:
        int: integer between 0 to 100, with 100 being the exact match
    """
    tstring = target_string

    # process regex here. It's a yes no situation (100 or 0)
    if regex:
        try:
            if re.search(sfilter, tstring):
                return 100
        except Exception:
            pass
        return 0

    # 100 for identical matches
    if sfilter == tstring:
        return 100

    # 98 to 99 reserved (2 scores)

    # 97 for identical non-case-sensitive matches
    lower_tstring = tstring.lower()
    lower_sfilter_str = sfilter.lower()
    if lower_sfilter_str == lower_tstring:
        return 97

    # 95  to 96 reserved (2 scores)

    # 93 to 94 for inclusion matches
    if sfilter in tstring:
        return 94
    if lower_sfilter_str in lower_tstring:
        return 93

    # 91  to 92 reserved (2 scores)

    ## 80 to 90 for parts matches
    tstring_parts = tstring.split()
    sfilter_parts = sfilter.split()
    if all(x in tstring_parts for x in sfilter_parts):
        return 90

    # 88 to 89 reserved (2 scores)

    lower_tstring_parts = [x.lower() for x in tstring_parts]
    lower_sfilter_parts = [x.lower() for x in sfilter_parts]
    # exclude override
    if any(x[0] == '!' for x in sfilter_parts):
        exclude_indices = [
            lower_sfilter_parts.index(i) for i in lower_sfilter_parts
            if i[0] == '!'
        ]
        exclude_indices.reverse()
        exclude_list = [
            lower_sfilter_parts.pop(i) for i in exclude_indices
        ]
        for e in exclude_list:
            # doesn't contain
            if len(e) > 1:
                exclude_string = e[1:]
                if any(
                        [exclude_string in
                        part for part in lower_tstring_parts]
                ):
                    return 0
    if all(x in lower_tstring_parts for x in lower_sfilter_parts):
        return 87

    # 85 to 86 reserved (2 scores)

    if all(x in tstring for x in sfilter_parts):
        return 84

    # 82 to 83 reserved (2 scores)

    if all(x in lower_tstring for x in lower_sfilter_parts):
        return 81

    # 80 reserved

    return 0


def get_exe_version(exepath):
    """Extract Product Version value from EXE file."""
    version_info = framework.Diagnostics.FileVersionInfo.GetVersionInfo(exepath)
    return version_info.ProductVersion


def get_reg_key(key, subkey):
    """Get value of the given Windows registry key and subkey.

    Args:
        key (PyHKEY): parent registry key
        subkey (str): subkey path

    Returns:
        PyHKEY: registry key if found, None if not found

    Example:
        >>> get_reg_key(wr.HKEY_CURRENT_USER, 'Control Panel/International')
        ... <PyHKEY at 0x...>
    """
    try:
        return wr.OpenKey(key, subkey, 0, wr.KEY_READ)
    except Exception:
        return None


def kill_tasks(task_name):
    """Kill running tasks matching task_name

    Args:
        task_name (str): task name

    Example:
        >>> kill_tasks('Revit.exe')
    """
    os.system("taskkill /f /im %s" % task_name)


def int2hex_long(number):
    """Integer to hexadecimal string."""
    # python 2 fix of addin 'L' to long integers
    return hex(number).replace('L', '')


def hex2int_long(hex_string):
    """Hexadecimal string to Integer."""
    # python 2 fix of addin 'L' to long integers
    hex_string.replace('L', '')
    return int(hex_string, 16)


def split_words(input_string):
    """Splits given string by uppercase characters

    Args:
        input_string (str): input string

    Returns:
        list[str]: split string

    Example:
        >>> split_words("UIApplication_ApplicationClosing")
        ... ['UIApplication', 'Application', 'Closing']
    """
    parts = []
    part = ""
    for c in input_string:
        if c.isalpha():
            if c.isupper() and part and part[-1].islower():
                if part:
                    parts.append(part.strip())
                part = c
            else:
                part += c
    parts.append(part)
    return parts


def get_paper_sizes(printer_name=None):
    """Get paper sizes defined on this system

    Returns:
        list[]: list of papersize instances
    """
    print_settings = framework.Drawing.Printing.PrinterSettings()
    if printer_name:
        print_settings.PrinterName = printer_name
    return list(print_settings.PaperSizes)


def get_integer_length(number):
    """Return digit length of given number."""
    return 1 if number == 0 else (math.floor(math.log10(number)) + 1)


def get_my_ip():
    """Return local ip address of this machine"""
    return socket.gethostbyname(socket.gethostname())
