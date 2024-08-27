"""Assembly maker module."""
import os.path as op
from collections import namedtuple

from pyrevit import PYREVIT_ADDON_NAME, EXEC_PARAMS
from pyrevit.compat import NETCORE
from pyrevit import framework
from pyrevit.framework import AppDomain, Version
from pyrevit.framework import AssemblyName, AssemblyBuilderAccess
from pyrevit import coreutils
from pyrevit.coreutils import assmutils
from pyrevit.coreutils import appdata
from pyrevit.coreutils import logger
from pyrevit.versionmgr import get_pyrevit_version

from pyrevit.loader import HASH_CUTOFF_LENGTH
from pyrevit.runtime import BASE_TYPES_DIR_HASH
from pyrevit.runtime import typemaker
from pyrevit.userconfig import user_config

from System.Reflection.Emit import AssemblyBuilder

# Generic named tuple for passing assembly information to other modules
ExtensionAssemblyInfo = namedtuple('ExtensionAssemblyInfo',
                                   ['name', 'location', 'reloading'])


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


def _make_extension_hash(extension):
    # creates a hash based on hash of baseclasses module that
    # the extension is based upon and also the user configuration version
    return coreutils.get_str_hash(
        BASE_TYPES_DIR_HASH
        + EXEC_PARAMS.engine_ver
        + extension.get_hash())[:HASH_CUTOFF_LENGTH]


def _make_ext_asm_fileid(extension):
    return '{}_{}'.format(_make_extension_hash(extension), extension.name)


def _is_pyrevit_ext_asm(asm_name, extension):
    # if this is a pyRevit package assembly
    return asm_name.startswith(PYREVIT_ADDON_NAME) \
           and asm_name.endswith(extension.name)


def _is_pyrevit_ext_already_loaded(ext_asm_name):
    mlogger.debug('Asking Revit for previously loaded package assemblies: %s',
                  ext_asm_name)
    return len(assmutils.find_loaded_asm(ext_asm_name))


def _is_any_ext_asm_loaded(extension):
    for loaded_asm in AppDomain.CurrentDomain.GetAssemblies():
        mlogger.debug('Checking for loaded extension asm: %s ? %s : %s',
                      extension.name, loaded_asm.GetName().Name, loaded_asm)
        if _is_pyrevit_ext_asm(loaded_asm.GetName().Name, extension):
            return True
    return False


def _update_component_cmd_types(extension):
    for cmd_component in extension.get_all_commands():
        typemaker.make_bundle_types(
            extension,
            cmd_component,
            module_builder=None
            )


def _create_asm_file(extension, ext_asm_file_name, ext_asm_file_path):
    # check to see if any older assemblies have been loaded for this package
    ext_asm_full_file_name = \
        coreutils.make_canonical_name(ext_asm_file_name,
                                      framework.ASSEMBLY_FILE_TYPE)

    # this means that we currently have this package loaded and
    # we're reloading a new version
    is_reloading_pkg = _is_any_ext_asm_loaded(extension)

    # create assembly
    mlogger.debug('Building assembly for package: %s', extension)
    pyrvt_ver_int_tuple = get_pyrevit_version().as_int_tuple()
    win_asm_name = AssemblyName(Name=ext_asm_file_name,
                                Version=Version(pyrvt_ver_int_tuple[0],
                                                pyrvt_ver_int_tuple[1],
                                                pyrvt_ver_int_tuple[2]))
    mlogger.debug('Generated assembly name for this package: %s',
                  ext_asm_file_name)
    mlogger.debug('Generated windows assembly name for this package: %s',
                  win_asm_name)
    mlogger.debug('Generated assembly file name for this package: %s',
                  ext_asm_full_file_name)

    if NETCORE:
        asm_builder = AssemblyBuilder.DefineDynamicAssembly(
            win_asm_name,
            AssemblyBuilderAccess.Run)

        # get module builder
        module_builder = asm_builder.DefineDynamicModule(ext_asm_file_name)
    else:
        # get assembly builder
        asm_builder = AppDomain.CurrentDomain.DefineDynamicAssembly(
            win_asm_name,
            AssemblyBuilderAccess.RunAndSave,
            op.dirname(ext_asm_file_path))

        # get module builder
        module_builder = asm_builder.DefineDynamicModule(ext_asm_file_name,
                                                         ext_asm_full_file_name)

    # create command classes
    for cmd_component in extension.get_all_commands():
        # create command executor class for this command
        mlogger.debug('Creating types for command: %s', cmd_component)
        typemaker.make_bundle_types(extension, cmd_component, module_builder)

    if NETCORE:
        from Lokad.ILPack import AssemblyGenerator
        generator = AssemblyGenerator()
        generator.GenerateAssembly(asm_builder, ext_asm_file_path)
    else:
        # save final assembly
        asm_builder.Save(ext_asm_full_file_name)

    assmutils.load_asm_file(ext_asm_file_path)

    mlogger.debug('Executer assembly saved.')
    return ExtensionAssemblyInfo(ext_asm_file_name,
                                 ext_asm_file_path,
                                 is_reloading_pkg)


def _produce_asm_file(extension):
    # unique assembly filename for this package
    ext_asm_fileid = _make_ext_asm_fileid(extension)
    ext_asm_file_path = \
        appdata.get_data_file(file_id=ext_asm_fileid,
                              file_ext=framework.ASSEMBLY_FILE_TYPE)
    # make unique assembly name for this package
    ext_asm_file_name = coreutils.get_file_name(ext_asm_file_path)

    if _is_pyrevit_ext_already_loaded(ext_asm_file_name):
        mlogger.debug('Extension assembly is already loaded: %s',
                      ext_asm_file_name)
        _update_component_cmd_types(extension)
        return ExtensionAssemblyInfo(ext_asm_file_name, ext_asm_file_path, True)
    elif appdata.is_data_file_available(
            file_id=ext_asm_fileid,
            file_ext=framework.ASSEMBLY_FILE_TYPE):
        mlogger.debug('Extension assembly file already exists: %s',
                      ext_asm_file_path)
        try:
            loaded_assm = assmutils.load_asm_file(ext_asm_file_path)
            for asm_name in loaded_assm.GetReferencedAssemblies():
                mlogger.debug('Checking referenced assembly: %s', asm_name)
                ref_asm_file_path = \
                    appdata.is_file_available(
                        file_name=asm_name.Name,
                        file_ext=framework.ASSEMBLY_FILE_TYPE
                        )
                if ref_asm_file_path:
                    mlogger.debug('Loading referenced assembly: %s',
                                  ref_asm_file_path)
                    try:
                        assmutils.load_asm_file(ref_asm_file_path)
                    except Exception as load_err:
                        mlogger.error('Error loading referenced assembly: %s '
                                      '| %s', ref_asm_file_path, load_err)

            _update_component_cmd_types(extension)
            return ExtensionAssemblyInfo(ext_asm_file_name,
                                         ext_asm_file_path,
                                         False)
        except Exception as ext_asm_load_err:
            mlogger.error('Error loading extension assembly: %s | %s',
                          ext_asm_file_path, ext_asm_load_err)
    else:
        return _create_asm_file(extension,
                                ext_asm_file_name,
                                ext_asm_file_path)


def create_assembly(extension):
    """Create an extension assembly.

    Args:
        extension (pyrevit.extensions.components.Extension): pyRevit extension.

    Returns:
        (ExtensionAssemblyInfo): assembly info
    """
    mlogger.debug('Creating assembly for extension: %s', extension.name)
    # create assembly file and return assembly path to be used in UI creation
    # try:
    ext_asm_info = _produce_asm_file(extension)
    mlogger.debug('Assembly created: %s', ext_asm_info)
    return ext_asm_info
    # except Exception as asm_err:
    #     mlogger.critical('Can not create assembly for: {}' \
    #                     '| {}'.format(extension, asm_err))


def cleanup_assembly_files():
    if coreutils.get_revit_instance_count() == 1:
        for asm_file_path in appdata.list_data_files(file_ext='dll'):
            if not assmutils.find_loaded_asm(asm_file_path, by_location=True):
                appdata.garbage_data_file(asm_file_path)
                asm_log_file = asm_file_path.replace('.dll', '.log')
                if op.exists(asm_log_file):
                    appdata.garbage_data_file(asm_log_file)
