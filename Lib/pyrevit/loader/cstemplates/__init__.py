from pyrevit.coreutils import make_full_classname


# base classes for pyRevit commands ------------------------------------------------------------------------------------
LOADER_BASE_NAMESPACE = 'PyRevitBaseClasses'

# template python command class
LOADER_CMD_CLASS = '{}.{}'.format(LOADER_BASE_NAMESPACE, 'PyRevitCommand')

# template python command availability class
LOADER_CMD_AVAIL_CLS = make_full_classname(LOADER_BASE_NAMESPACE, 'PyRevitCommandDefaultAvail')
LOADER_CMD_AVAIL_CLS_CATEGORY = make_full_classname(LOADER_BASE_NAMESPACE, 'PyRevitCommandCategoryAvail')
LOADER_CMD_AVAIL_CLS_SELECTION = make_full_classname(LOADER_BASE_NAMESPACE, 'PyRevitCommandSelectionAvail')


def _make_baseclasses_asm_name():
    return SESSION_STAMPED_ID + '_' + LOADER_BASE_CLASSES_ASM


def _is_pyrevit_already_loaded():
    logger.debug('Asking Revit for previously loaded pyrevit assemblies...')
    try:
        return find_loaded_asm(_make_baseclasses_asm_name())
    except Exception as err:
        logger.debug('PyRevit is not loaded.')
        return False


def _find_pyrevit_base_class(base_class_name):
    baseclass_asm = _find_base_classes_asm()
    base_class = baseclass_asm.GetType(base_class_name)
    if base_class is not None:
        return base_class
    else:
        raise PyRevitException('Can not find base class type: {}'.format(base_class_name))


def _generate_base_classes_asm():
    with open(op.join(LOADER_DIR, 'lib', 'pyrevit', 'loader', 'cstemplates','baseclasses.cs'), 'r') as code_file:
        source = code_file.read()
    try:
        baseclass_asm = compile_to_asm(source, _make_baseclasses_asm_name(), USER_TEMP_DIR,
                                       references=[_find_loaded_asm('PresentationCore').Location,
                                                   _find_loaded_asm('WindowsBase').Location,
                                                   'RevitAPI.dll', 'RevitAPIUI.dll',
                                                   op.join(LOADER_ASM_DIR, LOADER_ADDIN + ASSEMBLY_FILE_TYPE)])
    except PyRevitException as compile_err:
        logger.critical('Can not compile cstemplates code into assembly. | {}'.format(compile_err))
        raise compile_err

    return Assembly.LoadFrom(baseclass_asm)


def get_cmd_class(cmd_comp):
    # return (avail_class, class_name)
    base_classes_asm = _find_loaded_asm(_make_baseclasses_asm_name())
    if base_classes_asm is not None:
        return base_classes_asm
    else:
        # if base classes is not already loaded, compile_to_asm and load the assembly
        return _generate_base_classes_asm()


def get_cmd_avail_class(cmd_context):
    # return (avail_class, class_name)
    return tuple([None, None])


def get_shared_classes():
    # return list of tuples (default_avail_class, class_name)
    return [(None, None)]
