"""Utilities to load and manage assemblies."""
import os.path as op

from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.compat import safe_strtype
from pyrevit.coreutils import logger


mlogger = logger.get_logger(__name__)


def load_asm(asm_name):
    """Load assembly by name into current domain.

    Args:
        asm_name (str): assembly name

    Returns:
        (Any): the loaded assembly, None if not loaded.
    """
    return framework.AppDomain.CurrentDomain.Load(asm_name)


def load_asm_file(asm_file):
    """Load assembly by file into current domain.

    Args:
        asm_file (str): assembly file path

    Returns:
        (Any): loaded assembly, None if not loaded.
    """
    try:
        return framework.Assembly.LoadFrom(asm_file)
    except Exception as load_ex:
        mlogger.error("Error loading assembly @ %s | %s", asm_file, load_ex)
        return None


def load_asm_files(asm_files):
    """Load assemblies by file into current domain.

    Args:
        asm_files (list[str]): list of assembly file paths
    """
    for asm_file in asm_files:
        load_asm_file(asm_file)


def find_loaded_asm(asm_info, by_partial_name=False, by_location=False):
    """Find loaded assembly based on name, partial name, or location.

    Args:
        asm_info (str): name or location of the assembly
        by_partial_name (bool): returns all assemblies that has the asm_info
        by_location (bool): returns all assemblies matching location

    Returns:
        (list): List of all loaded assemblies matching the provided info
            If only one assembly has been found, it returns the assembly.
            None will be returned if assembly is not loaded.
    """
    loaded_asm_list = []
    cleaned_asm_info = \
        asm_info.lower().replace('.' + framework.ASSEMBLY_FILE_TYPE, '')
    for loaded_assembly in framework.AppDomain.CurrentDomain.GetAssemblies():
        if by_partial_name:
            if cleaned_asm_info in \
                    safe_strtype(loaded_assembly.GetName().Name).lower():
                loaded_asm_list.append(loaded_assembly)
        elif by_location:
            try:
                if op.normpath(loaded_assembly.Location) == \
                        op.normpath(asm_info):
                    loaded_asm_list.append(loaded_assembly)
            except Exception:
                continue
        elif cleaned_asm_info == \
                safe_strtype(loaded_assembly.GetName().Name).lower():
            loaded_asm_list.append(loaded_assembly)

    return loaded_asm_list


def find_type_by_name(assembly, type_name):
    """Find type by name in assembly.

    Args:
        assembly (Assembly): assembly to find the type in
        type_name (str): type name

    Returns:
        (type): type if found.

    Raises:
        PyRevitException: if type not found.
    """
    base_class = assembly.GetType(type_name)
    if base_class is not None:
        return base_class
    else:
        raise PyRevitException('Can not find base class type: {}'
                               .format(type_name))
