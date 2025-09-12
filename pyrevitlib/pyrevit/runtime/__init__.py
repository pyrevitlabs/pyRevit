"""Module that compiles the base DLL on load."""
import os
import os.path as op
import sys
import json

from pyrevit import PyRevitException, EXEC_PARAMS, HOST_APP
import pyrevit.engine as eng
from pyrevit import framework
from pyrevit.framework import List, Array
from pyrevit import api
from pyrevit import labs
from pyrevit.compat import safe_strtype, NETCORE
from pyrevit import BIN_DIR, RUNTIME_DIR
from pyrevit import coreutils
from pyrevit.coreutils import assmutils
from pyrevit.coreutils import logger
from pyrevit.coreutils import appdata
from pyrevit.loader import HASH_CUTOFF_LENGTH
from pyrevit.userconfig import user_config
import pyrevit.extensions as exts

#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


# C:\Windows\Microsoft.NET\Framework\

INTERFACE_TYPES_DIR = RUNTIME_DIR

DOTNET_DIR = op.join(os.getenv('windir'), 'Microsoft.NET', 'Framework')
DOTNET64_DIR = op.join(os.getenv('windir'), 'Microsoft.NET', 'Framework64')

DOTNET_SDK_DIR = op.join(os.getenv('programfiles(x86)'),
                            'Reference Assemblies',
                            'Microsoft', 'Framework', '.NETFramework')


try:
    # get sorted list of installed frawework paths
    DOTNET_FRAMEWORK_DIRS = sorted(
        [x for x in os.listdir(DOTNET_DIR)
            if x.startswith('v4.') and 'X' not in x], reverse=True)
except Exception as fw_err:
    DOTNET_FRAMEWORK_DIRS = []
    mlogger.debug('Dotnet Frawework is not installed. | %s', fw_err)

try:
    # get sorted list of installed frawework paths
    DOTNET64_FRAMEWORK_DIRS = sorted(
        [x for x in os.listdir(DOTNET64_DIR)
            if x.startswith('v4.') and 'X' not in x], reverse=True)
except Exception as fw_err:
    DOTNET64_FRAMEWORK_DIRS = []
    mlogger.debug('Dotnet64 Frawework is not installed. | %s', fw_err)

try:
    # get sorted list of installed frawework sdk paths
    DOTNET_TARGETPACK_DIRS = sorted(
        [x for x in os.listdir(DOTNET_SDK_DIR)
            if x.startswith('v4.') and 'X' not in x], reverse=True)
except Exception as dotnet_sdk_err:
    DOTNET_TARGETPACK_DIRS = []
    mlogger.debug('Dotnet SDK is not installed. | %s', dotnet_sdk_err)


# base classes for pyRevit commands --------------------------------------------
RUNTIME_NAMESPACE = 'PyRevitLabs.PyRevit.Runtime'

# template python command class
CMD_EXECUTOR_TYPE_NAME = '{}.{}'\
    .format(RUNTIME_NAMESPACE, 'ScriptCommand')

# template python command availability class
CMD_AVAIL_TYPE_NAME_EXTENDED = \
    coreutils.make_canonical_name(RUNTIME_NAMESPACE, 'ScriptCommandExtendedAvail')
CMD_AVAIL_TYPE_NAME_SELECTION = \
    coreutils.make_canonical_name(RUNTIME_NAMESPACE, 'ScriptCommandSelectionAvail')
CMD_AVAIL_TYPE_NAME_ZERODOC = \
    coreutils.make_canonical_name(RUNTIME_NAMESPACE, 'ScriptCommandZeroDocAvail')

CMD_AVAIL_NAME_POSTFIX = '-avail'

SOURCE_FILE_EXT = '.cs'
SOURCE_FILE_FILTER = r'(\.cs)'

# get and load the active Cpython engine
CPYTHON_ENGINE = user_config.get_active_cpython_engine()

# create a hash for the loader assembly
# this hash is calculated based on:
# - runtime csharp files
# - runtime engine version
# - cpython engine version
mlogger.debug('Building on IronPython engine: %s', EXEC_PARAMS.engine_ver)
BASE_TYPES_DIR_HASH = \
    coreutils.get_str_hash(
        coreutils.calculate_dir_hash(
            INTERFACE_TYPES_DIR, '', SOURCE_FILE_FILTER
        )
        + EXEC_PARAMS.engine_ver
        + str(CPYTHON_ENGINE.Version) if CPYTHON_ENGINE else "0"
        )[:HASH_CUTOFF_LENGTH]
RUNTIME_ASSM_FILE_ID = '{}_{}'\
    .format(BASE_TYPES_DIR_HASH, RUNTIME_NAMESPACE)

RUNTIME_ASSM_FILE = \
    op.join(BIN_DIR, "pyRevitLabs.PyRevit.Runtime.{}.dll".format(HOST_APP.version))

# taking the name of the generated data file and use it as assembly name
RUNTIME_ASSM_NAME = op.splitext(op.basename(RUNTIME_ASSM_FILE))[0]
mlogger.debug('Interface types assembly file is: %s', RUNTIME_ASSM_NAME)


def _get_source_files_in(source_files_path):
    source_files = {}
    for source_file in os.listdir(source_files_path):
        if op.splitext(source_file)[1].lower() == SOURCE_FILE_EXT:
            source_filepath = op.join(source_files_path, source_file)
            mlogger.debug('Source file found: %s', source_filepath)
            source_files[source_file] = source_filepath
    return source_files


def _get_source_files():
    source_files = []
    source_dir = op.dirname(__file__)
    mlogger.debug('Source files location: %s', source_dir)
    all_sources = _get_source_files_in(source_dir)

    version_source_dir = op.join(op.dirname(__file__), HOST_APP.version)
    if op.exists(version_source_dir):
        mlogger.debug('Version-specific Source files location: %s',
                      version_source_dir)
        version_sources = _get_source_files_in(version_source_dir)
        all_sources.update(version_sources)

    source_files = all_sources.values()
    mlogger.debug('Source files to be compiled: %s', source_files)
    return source_files


def _get_framework_module(fw_module, fw64=False):
    # start with the newest sdk folder and
    # work backwards trying to find the dll
    fw_dir = DOTNET64_DIR if fw64 else DOTNET_DIR
    fw_folders = DOTNET64_FRAMEWORK_DIRS if fw64 else DOTNET_FRAMEWORK_DIRS
    for fw_folder in fw_folders:
        fw_module_file = op.join(
            fw_dir,
            fw_folder,
            coreutils.make_canonical_name(fw_module,
                                          framework.ASSEMBLY_FILE_TYPE))
        mlogger.debug('Searching for installed: %s', fw_module_file)
        if op.exists(fw_module_file):
            mlogger.debug('Found installed: %s', fw_module_file)
            sys.path.append(op.join(fw_dir, fw_folder))
            return fw_module_file

    return None


def _get_framework_sdk_module(fw_module):
    # start with the newest sdk folder and
    # work backwards trying to find the dll
    for sdk_folder in DOTNET_TARGETPACK_DIRS:
        fw_module_file = op.join(
            DOTNET_SDK_DIR,
            sdk_folder,
            coreutils.make_canonical_name(fw_module,
                                          framework.ASSEMBLY_FILE_TYPE))
        mlogger.debug('Searching for sdk: %s', fw_module_file)
        if op.exists(fw_module_file):
            mlogger.debug('Found sdk: %s', fw_module_file)
            sys.path.append(op.join(DOTNET_SDK_DIR, sdk_folder))
            return fw_module_file

    return None


def _get_reference_file(ref_name):
    mlogger.debug('Searching for dependency: %s', ref_name)
    # First try to find the dll in the project folder
    addin_file = framework.get_dll_file(ref_name)
    if addin_file:
        assmutils.load_asm_file(addin_file)
        return addin_file

    mlogger.debug('Dependency is not shipped: %s', ref_name)
    mlogger.debug('Searching for dependency in loaded assemblies: %s', ref_name)

    # Lastly try to find location of assembly if already loaded
    loaded_asm = assmutils.find_loaded_asm(ref_name)
    if loaded_asm:
        return loaded_asm[0].Location

    mlogger.debug('Dependency is not loaded: %s', ref_name)
    mlogger.debug('Searching for dependency in installed frameworks: %s',
                  ref_name)

    # Then try to find the dll in windows installed framework64 files
    if DOTNET64_DIR:
        fw_module_file = _get_framework_module(ref_name, fw64=True)
        if fw_module_file:
            return fw_module_file

    # Then try to find the dll in windows installed framework files
    if DOTNET_DIR:
        fw_module_file = _get_framework_module(ref_name)
        if fw_module_file:
            return fw_module_file

    mlogger.debug('Dependency is not installed: %s', ref_name)
    mlogger.debug('Searching for dependency in installed frameworks sdks: %s',
                  ref_name)

    # Then try to find the dll in windows SDK
    if DOTNET_TARGETPACK_DIRS:
        fw_sdk_module_file = _get_framework_sdk_module(ref_name)
        if fw_sdk_module_file:
            return fw_sdk_module_file

    # if not worked raise critical error
    mlogger.critical('Can not find required reference assembly: %s', ref_name)


def get_references():
    """Get list of all referenced assemblies.

    Returns:
        (list): referenced assemblies
    """
    ref_list = [
        # system stuff
        'System', 'System.Core', 'System.Runtime', 'System.Linq', 'System.Collections',
        'System.Collections.Immutable', 'System.Console',
        'System.Xaml', 'System.Web', 'System.Xml', 'System.Numerics',
        'System.Drawing', 'System.Windows.Forms',
        'System.ComponentModel.Primitives', 'System.ComponentModel.TypeConverter',
        'PresentationCore', 'PresentationFramework',
        'WindowsBase', 'WindowsFormsIntegration',
        # legacy csharp/vb.net compiler
        'Microsoft.CSharp',
        # iron python engine
        '{prefix}Microsoft.Dynamic'.format(prefix=eng.EnginePrefix),
        '{prefix}Microsoft.Scripting'.format(prefix=eng.EnginePrefix),
        '{prefix}IronPython'.format(prefix=eng.EnginePrefix),
        '{prefix}IronPython.Modules'.format(prefix=eng.EnginePrefix),
        # revit api
        'RevitAPI', 'RevitAPIUI', 'AdWindows', 'UIFramework',
        # pyrevit loader assembly
        'pyRevitLoader',
        # pyrevit labs
        'pyRevitLabs.Common', 'pyRevitLabs.CommonWPF',
        'pyRevitLabs.MahAppsMetro',
        'pyRevitLabs.NLog',
        'pyRevitLabs.Json',
        'pyRevitLabs.Emojis',
        'pyRevitLabs.TargetApps.Revit',
        'pyRevitLabs.PyRevit',
        'pyRevitLabs.PyRevit.Runtime.Shared',
    ]

    # netcore depends
    if NETCORE:
        ref_list.extend(['System.Drawing.Common',
                         'System.Diagnostics.Process',
                         'System.Diagnostics.FileVersionInfo',
                         'System.Text.RegularExpressions'])

    # another revit api
    if HOST_APP.is_newer_than(2018):
        ref_list.extend(['Xceed.Wpf.AvalonDock'])

    refs = (_get_reference_file(ref_name) for ref_name in ref_list)
    return [r for r in refs if r]


def _generate_runtime_asm():
    source_list = list(_get_source_files())
    # now try to load compiled runtime assembly
    try:
        return assmutils.load_asm_file(RUNTIME_ASSM_FILE)
    except PyRevitException as compile_err:
        errors = safe_strtype(compile_err).replace('Compile error: ', '')
        mlogger.critical('Can not compile base types code into assembly.\n%s',
                         errors)
        raise compile_err


def _get_runtime_asm():
    if appdata.is_data_file_available(file_id=RUNTIME_ASSM_FILE_ID,
                                      file_ext=framework.ASSEMBLY_FILE_TYPE):
        return assmutils.load_asm_file(RUNTIME_ASSM_FILE)
    else:
        return _generate_runtime_asm()


def create_ipyengine_configs(clean=False, full_frame=False, persistent=False):
    """Return the configuration for ipython engine.

    Args:
        clean (bool, optional): Engine should be clean. Defaults to False.
        full_frame (bool, optional): Engine shoul be full frame. Defaults to False.
        persistent (bool, optional): Engine should persist. Defaults to False.

    Returns:
        (str): Configuration
    """
    return json.dumps({
        exts.MDATA_ENGINE_CLEAN: clean,
        exts.MDATA_ENGINE_FULLFRAME: full_frame,
        exts.MDATA_ENGINE_PERSISTENT: persistent,
    })


def create_ext_command_attrs():
    """Create dotnet attributes for Revit external commands.

    This method is used in creating custom dotnet types for pyRevit commands
    and compiling them into a DLL assembly. Current implementation sets
    ``RegenerationOption.Manual`` and ``TransactionMode.Manual``

    Returns:
        (list[CustomAttributeBuilder]): object for `RegenerationOption` 
            and `TransactionMode` attributes.
    """
    regen_const_info = \
        framework.clr.GetClrType(api.Attributes.RegenerationAttribute) \
        .GetConstructor(
            framework.Array[framework.Type](
                (api.Attributes.RegenerationOption,)
                ))

    regen_attr_builder = \
        framework.CustomAttributeBuilder(
            regen_const_info,
            framework.Array[object](
                (api.Attributes.RegenerationOption.Manual,)
                ))

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


def create_type(modulebuilder, type_class, class_name, custom_attr_list, *args):
    """Create a dotnet type for a pyRevit command.

    See ``baseclasses.cs`` code for the template pyRevit command dotnet type
    and its constructor default arguments that must be provided here.

    Args:
        modulebuilder (:obj:`ModuleBuilder`): dotnet module builder
        type_class (type): source dotnet type for the command
        class_name (str): name for the new type
        custom_attr_list (:obj:`list`): list of dotnet attributes for the type
        *args (Any): list of arguments to be used with type constructor

    Returns:
        (type): returns created dotnet type

    Examples:
        ```python
        asm_builder = AppDomain.CurrentDomain.DefineDynamicAssembly(
        win_asm_name, AssemblyBuilderAccess.RunAndSave, filepath
        )
        module_builder = asm_builder.DefineDynamicModule(
        ext_asm_file_name, ext_asm_full_file_name
        )
        create_type(
            module_builder,
            runtime.ScriptCommand,
            "PyRevitSomeCommandUniqueName",
            runtime.create_ext_command_attrs(),
            [scriptpath, atlscriptpath, searchpath, helpurl, name,
            bundle, extension, uniquename, False, False])
        ```
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
        if isinstance(param, str) \
                or isinstance(param, int):
            type_list.append(type(param))
            param_list.append(param)

    # call base constructor
    constructor = \
        type_class.GetConstructor(framework.Array[framework.Type](type_list))
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
    gen.Emit(framework.OpCodes.Call, constructor)
    # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(framework.OpCodes.Nop)
    gen.Emit(framework.OpCodes.Nop)
    gen.Emit(framework.OpCodes.Nop)
    gen.Emit(framework.OpCodes.Ret)
    return type_builder.CreateType()


# compile or load the base types assembly
# see it the assembly is already loaded
RUNTIME_ASSM = None
assm_list = assmutils.find_loaded_asm(RUNTIME_ASSM_NAME)
if assm_list:
    RUNTIME_ASSM = assm_list[0]
else:
    # else, let's generate the assembly and load it
    RUNTIME_ASSM = _get_runtime_asm()

if RUNTIME_ASSM is None:
    raise Exception("Error dynamically compiling pyRevit runtime")

CMD_EXECUTOR_TYPE = \
    assmutils.find_type_by_name(RUNTIME_ASSM, CMD_EXECUTOR_TYPE_NAME)

CMD_AVAIL_TYPE_EXTENDED = \
        assmutils.find_type_by_name(RUNTIME_ASSM,
                                    CMD_AVAIL_TYPE_NAME_EXTENDED)
CMD_AVAIL_TYPE_SELECTION = \
        assmutils.find_type_by_name(RUNTIME_ASSM,
                                    CMD_AVAIL_TYPE_NAME_SELECTION)
CMD_AVAIL_TYPE_ZERODOC = \
    assmutils.find_type_by_name(RUNTIME_ASSM,
                                CMD_AVAIL_TYPE_NAME_ZERODOC)
