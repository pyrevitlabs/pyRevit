import clr
import os.path as op
from collections import namedtuple

from pyrevit import PYREVIT_ADDON_NAME, EXEC_PARAMS
import pyrevit.coreutils.appdata as appdata
from pyrevit.coreutils import load_asm_file, find_loaded_asm, get_file_name,\
    make_canonical_name
from pyrevit.coreutils import get_str_hash, get_revit_instance_count
from pyrevit.coreutils.logger import get_logger
from pyrevit.versionmgr import PYREVIT_VERSION

from pyrevit.loader import ASSEMBLY_FILE_TYPE, HASH_CUTOFF_LENGTH
from pyrevit.loader.basetypes import BASE_TYPES_DIR_HASH
from pyrevit.loader.basetypes.typemaker import make_cmd_types, make_shared_types


if not EXEC_PARAMS.doc_mode:
    clr.AddReference('PresentationCore')
    clr.AddReference('RevitAPI')
    clr.AddReference('RevitAPIUI')
    clr.AddReference('System.Xml.Linq')

# noinspection PyUnresolvedReferences
from System import AppDomain, Version
# noinspection PyUnresolvedReferences
from System.Reflection import Assembly, AssemblyName
# noinspection PyUnresolvedReferences
from System.Reflection.Emit import AssemblyBuilderAccess

# Generic named tuple for passing assembly information to other modules
ExtensionAssemblyInfo = namedtuple('ExtensionAssemblyInfo',
                                   ['name', 'location', 'reloading'])


logger = get_logger(__name__)


def _make_extension_hash(extension):
    # creates a hash based on hash of baseclasses module that
    # the extension is based upon
    return get_str_hash(BASE_TYPES_DIR_HASH +
                        extension.ext_hash_value)[:HASH_CUTOFF_LENGTH]


def _make_ext_asm_fileid(extension):
    return '{}_{}'.format(_make_extension_hash(extension), extension.name)


def _is_pyrevit_ext_asm(asm_name, extension):
    # if this is a pyRevit package assembly
    return asm_name.startswith(PYREVIT_ADDON_NAME) \
           and asm_name.endswith(extension.name)


def _is_pyrevit_ext_already_loaded(ext_asm_name):
    logger.debug('Asking Revit for previously loaded package assemblies: {}'
                 .format(ext_asm_name))
    return len(find_loaded_asm(ext_asm_name))


def _is_any_ext_asm_loaded(extension):
    for loaded_asm in AppDomain.CurrentDomain.GetAssemblies():
        logger.debug('Checking for loaded extension asm: {} ? {} : {}'
                     .format(extension.name,
                             loaded_asm.GetName().Name,
                             loaded_asm))
        if _is_pyrevit_ext_asm(loaded_asm.GetName().Name, extension):
            return True
    return False


def _update_component_cmd_types(extension):
    for cmd_component in extension.get_all_commands():
        make_cmd_types(extension, cmd_component, module_builder=None)


def _create_asm_file(extension, ext_asm_file_name, ext_asm_file_path):
    # check to see if any older assemblies have been loaded for this package
    ext_asm_full_file_name = make_canonical_name(ext_asm_file_name,
                                                 ASSEMBLY_FILE_TYPE)

    # this means that we currently have this package loaded and
    # we're reloading a new version
    is_reloading_pkg = _is_any_ext_asm_loaded(extension)

    # create assembly
    logger.debug('Building assembly for package: {}'.format(extension))
    pyrvt_ver_int_tuple = PYREVIT_VERSION.as_int_tuple()
    win_asm_name = AssemblyName(Name=ext_asm_file_name,
                                Version=Version(pyrvt_ver_int_tuple[0],
                                                pyrvt_ver_int_tuple[1],
                                                pyrvt_ver_int_tuple[2]))
    logger.debug('Generated assembly name for this package: {0}'
                 .format(ext_asm_file_name))
    logger.debug('Generated windows assembly name for this package: {0}'
                 .format(win_asm_name))
    logger.debug('Generated assembly file name for this package: {0}'
                 .format(ext_asm_full_file_name))

    # get assembly builder
    asm_builder = AppDomain.CurrentDomain.DefineDynamicAssembly(
        win_asm_name,
        AssemblyBuilderAccess.RunAndSave,
        op.dirname(ext_asm_file_path))

    # get module builder
    module_builder = asm_builder.DefineDynamicModule(ext_asm_file_name,
                                                     ext_asm_full_file_name)

    # create classes that could be called from any button (shared classes)
    # currently only default availability class is implemented.
    # Default availability class is for resetting buttons back to normal
    # context state (when reloading and after their context
    # has changed during a session).
    make_shared_types(module_builder)

    # create command classes
    for cmd_component in extension.get_all_commands():
        # create command executor class for this command
        logger.debug('Creating types for command: {}'.format(cmd_component))
        make_cmd_types(extension, cmd_component, module_builder)

    # save final assembly
    asm_builder.Save(ext_asm_full_file_name)
    load_asm_file(ext_asm_file_path)

    logger.debug('Executer assembly saved.')
    return ExtensionAssemblyInfo(ext_asm_file_name,
                                 ext_asm_file_path,
                                 is_reloading_pkg)


def _produce_asm_file(extension):
    # unique assembly filename for this package
    ext_asm_fileid = _make_ext_asm_fileid(extension)
    ext_asm_file_path = appdata.get_data_file(file_id=ext_asm_fileid,
                                              file_ext=ASSEMBLY_FILE_TYPE)
    # make unique assembly name for this package
    ext_asm_file_name = get_file_name(ext_asm_file_path)

    if _is_pyrevit_ext_already_loaded(ext_asm_file_name):
        logger.debug('Extension assembly is already loaded: {}'
                     .format(ext_asm_file_name))
        _update_component_cmd_types(extension)
        return ExtensionAssemblyInfo(ext_asm_file_name, ext_asm_file_path, True)
    elif appdata.is_data_file_available(file_id=ext_asm_fileid,
                                        file_ext=ASSEMBLY_FILE_TYPE):
        logger.debug('Extension assembly file already exists: {}'
                     .format(ext_asm_file_path))
        try:
            loaded_assm = load_asm_file(ext_asm_file_path)
            for asm_name in loaded_assm.GetReferencedAssemblies():
                logger.debug('Checking referenced assembly: {}'
                             .format(asm_name))
                ref_asm_file_path = \
                    appdata.is_file_available(file_name=asm_name.Name,
                                              file_ext=ASSEMBLY_FILE_TYPE)
                if ref_asm_file_path:
                    logger.debug('Loading referenced assembly: {}'
                                 .format(ref_asm_file_path))
                    try:
                        load_asm_file(ref_asm_file_path)
                    except Exception as load_err:
                        logger.error('Error loading referenced assembly: {} '
                                     '| {}'.format(ref_asm_file_path, load_err))

            _update_component_cmd_types(extension)
            return ExtensionAssemblyInfo(ext_asm_file_name,
                                         ext_asm_file_path,
                                         False)
        except Exception as ext_asm_load_err:
            logger.error('Error loading extension assembly: {} | {}'
                         .format(ext_asm_file_path, ext_asm_load_err))
    else:
        return _create_asm_file(extension,
                                ext_asm_file_name,
                                ext_asm_file_path)


def create_assembly(extension):
    """

    Args:
        extension (pyrevit.extensions.components.Extension):

    Returns:

    """
    logger.debug('Creating assembly for extension: {}'.format(extension.name))
    # create assembly file and return assembly path to be used in UI creation
    # try:
    ext_asm_info = _produce_asm_file(extension)
    logger.debug('Assembly created: {}'.format(ext_asm_info))
    return ext_asm_info
    # except Exception as asm_err:
    #     logger.critical('Can not create assembly for: {}' \
    #                     '| {}'.format(extension, asm_err))


def cleanup_assembly_files():
    if get_revit_instance_count() == 1:
        for asm_file_path in appdata.list_data_files(file_ext='dll'):
            if not find_loaded_asm(asm_file_path, by_location=True):
                appdata.garbage_data_file(asm_file_path)
