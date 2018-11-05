"""Prepare and compile C# script types."""
from pyrevit import PyRevitException
from pyrevit.coreutils import find_loaded_asm, read_source_file, get_str_hash
from pyrevit.coreutils import create_type, load_asm_file,\
    create_ext_command_attrs
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.dotnetcompiler import compile_csharp
from pyrevit.loader import ASSEMBLY_FILE_TYPE, HASH_CUTOFF_LENGTH
from pyrevit.loader.basetypes import _get_references
from pyrevit.coreutils import appdata
from pyrevit import extensions as exts
from pyrevit import UI


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def _update_pyrevit_fields(cmd_component, iext_cmd):
    # grab title from C# type
    title_field = iext_cmd.GetDeclaredField(exts.UI_TITLE_PARAM)
    if title_field:
        cmd_component.ui_title = title_field.GetValue(iext_cmd)

    # grab docstring from C# type
    docstring_field = iext_cmd.GetDeclaredField(exts.DOCSTRING_PARAM)
    if docstring_field:
        cmd_component.doc_string = docstring_field.GetValue(iext_cmd)

    # grab author from C# type
    author_field = iext_cmd.GetDeclaredField(exts.AUTHOR_PARAM)
    if author_field:
        cmd_component.author = author_field.GetValue(iext_cmd)

    # grab help url from C# type
    helpurl_field = iext_cmd.GetDeclaredField(exts.COMMAND_HELP_URL)
    if helpurl_field:
        cmd_component.cmd_help_url = helpurl_field.GetValue(iext_cmd)

    # grab min supported revit version from C# type
    minrevit_field = iext_cmd.GetDeclaredField(exts.MIN_REVIT_VERSION_PARAM)
    if minrevit_field:
        cmd_component.min_revit_ver = minrevit_field.GetValue(iext_cmd)

    # grab max supported revit version from C# type
    maxrevit_field = iext_cmd.GetDeclaredField(exts.MAX_REVIT_VERSION_PARAM)
    if maxrevit_field:
        cmd_component.max_revit_ver = maxrevit_field.GetValue(iext_cmd)

    # grab beta from C# type
    isbeta_field = iext_cmd.GetDeclaredField(exts.BETA_SCRIPT_PARAM)
    if isbeta_field:
        cmd_component.beta_cmd = isbeta_field.GetValue(iext_cmd)


def _get_csharp_cmd_asm(cmd_component):
    """

    Args:
        cmd_component (pyrevit.extensions.genericcomps.GenericUICommand):

    Returns:

    """
    script_path = cmd_component.get_full_script_address()
    source = read_source_file(script_path)
    script_hash = get_str_hash(source)[:HASH_CUTOFF_LENGTH]

    command_assm_file_id = '{}_{}'\
        .format(script_hash, cmd_component.unique_name)

    # check to see if compiled c# command assembly is already loaded
    compiled_assm_list = find_loaded_asm(command_assm_file_id,
                                         by_partial_name=True)
    if compiled_assm_list:
        return compiled_assm_list[0]

    # if not already loaded, check to see if the assembly file exits
    compiled_assm_path = \
        appdata.is_data_file_available(file_id=command_assm_file_id,
                                       file_ext=ASSEMBLY_FILE_TYPE)
    if compiled_assm_path:
        return load_asm_file(compiled_assm_path)

    # else, let's compile the script and make the types
    command_assm_file = \
        appdata.get_data_file(file_id=command_assm_file_id,
                              file_ext=ASSEMBLY_FILE_TYPE)
    mlogger.debug('Compiling script %s to %s', cmd_component, command_assm_file)
    compiled_assm_path = compile_csharp([script_path],
                                        command_assm_file,
                                        reference_list=_get_references())
    return load_asm_file(compiled_assm_path)


def _verify_command_interfaces(compiled_assm):
    iextcmd = iextcmd_avail = None

    for compiled_type in compiled_assm.GetTypes():
        if UI.IExternalCommand in compiled_type.GetInterfaces():
            iextcmd = compiled_type
        elif UI.IExternalCommandAvailability in compiled_type.GetInterfaces():
            iextcmd_avail = compiled_type

    return iextcmd, iextcmd_avail


def _make_csharp_types(module_builder, cmd_component):

    compiled_assm = _get_csharp_cmd_asm(cmd_component)

    iext_cmd, iext_cmd_avail = _verify_command_interfaces(compiled_assm)

    if iext_cmd:
        create_type(module_builder,
                    iext_cmd,
                    cmd_component.unique_name,
                    create_ext_command_attrs())
        
        _update_pyrevit_fields(cmd_component, iext_cmd)
        cmd_component.class_name = cmd_component.unique_name
    else:
        raise PyRevitException('Can not find UI.IExternalCommand derivatives '
                               'for: {}'.format(cmd_component))

    if iext_cmd_avail:
        create_type(module_builder,
                    iext_cmd_avail,
                    cmd_component.unique_avail_name,
                    [])
        cmd_component.avail_class_name = cmd_component.unique_avail_name
    else:
        mlogger.debug('Can not find UI.IExternalCommandAvailability '
                      'derivatives for: %s', cmd_component)


def create_csharp_types(extension, cmd_component, module_builder=None): #pylint: disable=W0613
    if module_builder:
        _make_csharp_types(module_builder, cmd_component)
    else:
        compiled_assm = _get_csharp_cmd_asm(cmd_component)
        iext_cmd, iext_cmd_avail = _verify_command_interfaces(compiled_assm)

        if iext_cmd:
            _update_pyrevit_fields(cmd_component, iext_cmd)
            cmd_component.class_name = cmd_component.unique_name

        if iext_cmd_avail:
            cmd_component.avail_class_name = cmd_component.unique_avail_name
