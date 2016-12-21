from pyrevit import PyRevitException
from pyrevit.coreutils import create_type, read_source_file, get_str_hash, load_asm_file, create_ext_command_attrs
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.dotnetcompiler import compile_csharp

from pyrevit.loader import ASSEMBLY_FILE_TYPE, HASH_CUTOFF_LENGTH
from pyrevit.loader.basetypes import _get_references

import pyrevit.coreutils.appdata as appdata

# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import IExternalCommand, IExternalCommandAvailability


logger = get_logger(__name__)


def _get_csharp_cmd_asm(cmd_component):
    """

    Args:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    source = read_source_file(cmd_component.get_full_script_address())
    script_hash = get_str_hash(source)[:HASH_CUTOFF_LENGTH]

    command_assm_file_id = '{}_{}'.format(script_hash, cmd_component.unique_name)
    compiled_assm_path = appdata.is_data_file_available(file_id=command_assm_file_id, file_ext=ASSEMBLY_FILE_TYPE)

    if not compiled_assm_path:
        command_assm_file = appdata.get_data_file(file_id=command_assm_file_id, file_ext=ASSEMBLY_FILE_TYPE)
        logger.debug('Compiling script {} to {}'.format(cmd_component, command_assm_file))
        compiled_assm_path = compile_csharp([source], command_assm_file, reference_list=_get_references())

    return load_asm_file(compiled_assm_path)


def create_csharp_types(module_builder, cmd_component):

    compiled_assm = _get_csharp_cmd_asm(cmd_component)

    iext_cmd = iext_cmd_avail = None

    for compiled_type in compiled_assm.GetTypes():
        if IExternalCommand in compiled_type.GetInterfaces():
            iext_cmd = compiled_type
        elif IExternalCommandAvailability in compiled_type.GetInterfaces():
            iext_cmd_avail = compiled_type

    if iext_cmd:
        create_type(module_builder, iext_cmd, cmd_component.unique_name, create_ext_command_attrs())
        cmd_component.class_name = cmd_component.unique_name
    else:
        raise PyRevitException('Can not find IExternalCommand derivatives for: {}'.format(cmd_component))

    if iext_cmd_avail:
        create_type(module_builder, iext_cmd_avail, cmd_component.unique_avail_name, [])
        cmd_component.avail_class_name = cmd_component.unique_avail_name
    else:
        logger.debug('Can not find IExternalCommandAvailability derivatives for: {}'.format(cmd_component))
