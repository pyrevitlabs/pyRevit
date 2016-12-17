import imp

from pyrevit import HOST_APP, EXEC_PARAMS, PyRevitException
from pyrevit.coreutils import find_loaded_asm
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.ribbon import get_current_ui
from pyrevit.extensions import TAB_POSTFIX, PANEL_POSTFIX, STACKTWO_BUTTON_POSTFIX, STACKTHREE_BUTTON_POSTFIX, \
                               PULLDOWN_BUTTON_POSTFIX, SPLIT_BUTTON_POSTFIX, SPLITPUSH_BUTTON_POSTFIX, \
                               PUSH_BUTTON_POSTFIX, TOGGLE_BUTTON_POSTFIX, SMART_BUTTON_POSTFIX, LINK_BUTTON_POSTFIX, \
                               SEPARATOR_IDENTIFIER, SLIDEOUT_IDENTIFIER, SCRIPT_FILE_FORMAT


logger = get_logger(__name__)


CONFIG_SCRIPT_TITLE_POSTFIX = u'\u25CF'


class UIMakerParams:
    def __init__(self, parent_ui, component, asm_info):
        self.parent_ui = parent_ui
        self.component = component
        self.asm_info = asm_info


def _make_button_tooltip(button):
    tooltip = button.doc_string
    if tooltip:
        tooltip += '\n\nBundle Name:\n{0}'.format(button.name)
        tooltip += '\n\nAuthor:\n{0}'.format(button.author)
    return tooltip


def _make_button_tooltip_ext(button, asm_name):
    return 'Class Name:\n{}\n\nAssembly Name:\n{}'.format(button.unique_name, asm_name)


def _make_ui_title(button):
    if button.has_config_script():
        return button.ui_title + ' {}'.format(CONFIG_SCRIPT_TITLE_POSTFIX)
    else:
        return button.ui_title


def _make_full_class_name(asm_name, class_name):
    if asm_name is None or class_name is None:
        return None
    else:
        return '{}.{}'.format(asm_name, class_name)


def _produce_ui_separator(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui_item = ui_maker_params.parent_ui
    ext_asm_info = ui_maker_params.asm_info

    if not ext_asm_info.reloading:
        logger.debug('Adding separator to: {}'.format(parent_ui_item))
        try:
            parent_ui_item.add_separator()
        except PyRevitException as err:
            logger.error('UI error: {}'.format(err.message))

    return None


def _produce_ui_slideout(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui_item = ui_maker_params.parent_ui
    ext_asm_info = ui_maker_params.asm_info

    if not ext_asm_info.reloading:
        logger.debug('Adding slide out to: {}'.format(parent_ui_item))
        try:
            parent_ui_item.add_slideout()
        except PyRevitException as err:
            logger.error('UI error: {}'.format(err.message))

    return None


def _produce_ui_smartbutton(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui_item = ui_maker_params.parent_ui
    smartbutton = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    logger.debug('Producing smart button: {}'.format(smartbutton))
    try:
        parent_ui_item.create_push_button(smartbutton.name,
                                          ext_asm_info.location,
                                          smartbutton.unique_name,
                                          smartbutton.icon_file,
                                          _make_button_tooltip(smartbutton),
                                          _make_button_tooltip_ext(smartbutton, ext_asm_info.name),
                                          smartbutton.unique_avail_name,
                                          update_if_exists=True,
                                          ui_title=_make_ui_title(smartbutton))
    except PyRevitException as err:
        logger.error('UI error: {}'.format(err.message))
        return None

    logger.debug('Importing smart button as module: {}'.format(smartbutton))
    # replacing EXEC_PARAMS.command_name value with button name so the init script can log under its own name
    orig_cmd_name = EXEC_PARAMS.command_name
    EXEC_PARAMS.command_name = smartbutton.name
    try:
        # importing smart button script as a module
        importedscript = imp.load_source(smartbutton.unique_name, smartbutton.script_file)
        # resetting EXEC_PARAMS.command_name to original
        EXEC_PARAMS.command_name = orig_cmd_name
        logger.debug('Import successful: {}'.format(importedscript))
        logger.debug('Running self initializer: {}'.format(smartbutton))
        try:
            # running the smart button initializer function
            importedscript.__selfinit__(smartbutton,
                                        parent_ui_item.button(smartbutton.name),
                                        HOST_APP.uiapp)
        except Exception as button_err:
            logger.error('Error initializing smart button: {} | {}'.format(smartbutton, button_err))
        return parent_ui_item.button(smartbutton.name)
    except Exception as err:
        logger.error('Smart button initialization error on: {} | {}'.format(smartbutton, err.message))
        return None


def _produce_ui_linkbutton(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui_item = ui_maker_params.parent_ui
    linkbutton = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    if not linkbutton.command_class:
        return None

    logger.debug('Producing button: {}'.format(linkbutton))
    try:
        linked_asm_list = find_loaded_asm(linkbutton.assembly)
        if not linked_asm_list:
            return None

        linked_asm = linked_asm_list[0]

        parent_ui_item.create_push_button(linkbutton.name,
                                          linked_asm.Location,
                                          _make_full_class_name(linked_asm.GetName().Name, linkbutton.command_class),
                                          linkbutton.icon_file,
                                          _make_button_tooltip(linkbutton),
                                          _make_button_tooltip_ext(linkbutton, ext_asm_info.name),
                                          linkbutton.unique_avail_name,
                                          update_if_exists=True,
                                          ui_title=_make_ui_title(linkbutton))
        return parent_ui_item.button(linkbutton.name)
    except PyRevitException as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_pushbutton(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui_item = ui_maker_params.parent_ui
    pushbutton = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    logger.debug('Producing button: {}'.format(pushbutton))
    try:
        parent_ui_item.create_push_button(pushbutton.name,
                                          ext_asm_info.location,
                                          pushbutton.unique_name,
                                          pushbutton.icon_file,
                                          _make_button_tooltip(pushbutton),
                                          _make_button_tooltip_ext(pushbutton, ext_asm_info.name),
                                          pushbutton.unique_avail_name,
                                          update_if_exists=True,
                                          ui_title=_make_ui_title(pushbutton))
        return parent_ui_item.button(pushbutton.name)
    except PyRevitException as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_pulldown(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    pulldown = ui_maker_params.component

    logger.debug('Producing pulldown button: {}'.format(pulldown))
    try:
        parent_ribbon_panel.create_pulldown_button(pulldown.name, pulldown.icon_file, update_if_exists=True)
        return parent_ribbon_panel.ribbon_item(pulldown.name)
    except PyRevitException as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_split(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    split = ui_maker_params.component

    logger.debug('Producing split button: {}'.format(split))
    try:
        parent_ribbon_panel.create_split_button(split.name, split.icon_file, update_if_exists=True)
        return parent_ribbon_panel.ribbon_item(split.name)
    except PyRevitException as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_splitpush(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    splitpush = ui_maker_params.component

    logger.debug('Producing splitpush button: {}'.format(splitpush))
    try:
        parent_ribbon_panel.create_splitpush_button(splitpush.name, splitpush.icon_file, update_if_exists=True)
        return parent_ribbon_panel.ribbon_item(splitpush.name)
    except PyRevitException as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_stacks(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui_panel = ui_maker_params.parent_ui
    stack_cmp = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    # if sub_cmp is a stack, ask parent_ui_item to open a stack (parent_ui_item.open_stack).
    # All subsequent items will be placed under this stack.
    # Close the stack (parent_ui_item.close_stack) to finish adding items to the stack.
    try:
        parent_ui_panel.open_stack()
        logger.debug('Opened stack: {}'.format(stack_cmp.name))

        if HOST_APP.is_older_than('2017'):
            _component_creation_dict[SPLIT_BUTTON_POSTFIX] = _produce_ui_pulldown
            _component_creation_dict[SPLITPUSH_BUTTON_POSTFIX] = _produce_ui_pulldown

        # capturing and logging any errors on stack item
        # (e.g when parent_ui_panel's stack is full and can not add any more items it will raise an error)
        _recursively_produce_ui_items(parent_ui_panel, stack_cmp, ext_asm_info)

        if HOST_APP.is_older_than('2017'):
            _component_creation_dict[SPLIT_BUTTON_POSTFIX] = _produce_ui_split
            _component_creation_dict[SPLITPUSH_BUTTON_POSTFIX] = _produce_ui_splitpush

        try:
            parent_ui_panel.close_stack()
            logger.debug('Closed stack: {}'.format(stack_cmp.name))
        except PyRevitException as err:
            logger.error('Error creating stack | {}'.format(err))

    except Exception as err:
        logger.error('Can not create stack under this parent: {} | {}'.format(parent_ui_panel, err))


def _produce_ui_panels(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui_tab = ui_maker_params.parent_ui
    panel = ui_maker_params.component

    logger.debug('Producing ribbon panel: {}'.format(panel))
    try:
        parent_ui_tab.create_ribbon_panel(panel.name, update_if_exists=True)
        return parent_ui_tab.ribbon_panel(panel.name)
    except PyRevitException as err:
        logger.error('UI error: {}'.format(err.message))
        return None


def _produce_ui_tab(ui_maker_params):
    """

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item
    """
    parent_ui = ui_maker_params.parent_ui
    tab = ui_maker_params.component

    logger.debug('Verifying tab: {}'.format(tab))
    if tab.has_commands():
        logger.debug('Tabs has command: {}'.format(tab))
        logger.debug('Producing ribbon tab: {}'.format(tab))
        try:
            parent_ui.create_ribbon_tab(tab.name, update_if_exists=True)
            return parent_ui.ribbon_tab(tab.name)
        except PyRevitException as err:
            logger.error('UI error: {}'.format(err.message))
            return None
    else:
        logger.debug('Tab does not have any commands. Skipping: {}'.format(tab.name))
        return None


_component_creation_dict = {TAB_POSTFIX: _produce_ui_tab,
                            PANEL_POSTFIX: _produce_ui_panels,
                            STACKTWO_BUTTON_POSTFIX: _produce_ui_stacks,
                            STACKTHREE_BUTTON_POSTFIX: _produce_ui_stacks,
                            PULLDOWN_BUTTON_POSTFIX: _produce_ui_pulldown,
                            SPLIT_BUTTON_POSTFIX: _produce_ui_split,
                            SPLITPUSH_BUTTON_POSTFIX: _produce_ui_splitpush,
                            PUSH_BUTTON_POSTFIX: _produce_ui_pushbutton,
                            TOGGLE_BUTTON_POSTFIX: _produce_ui_smartbutton,
                            SMART_BUTTON_POSTFIX: _produce_ui_smartbutton,
                            LINK_BUTTON_POSTFIX: _produce_ui_linkbutton,
                            SEPARATOR_IDENTIFIER: _produce_ui_separator,
                            SLIDEOUT_IDENTIFIER: _produce_ui_slideout,
                            }


def _recursively_produce_ui_items(parent_ui_item, component, ext_asm_info):
    for sub_cmp in component:
        try:
            logger.debug('Calling create func {} for: {}'.format(_component_creation_dict[sub_cmp.type_id], sub_cmp))
            ui_item = _component_creation_dict[sub_cmp.type_id](UIMakerParams(parent_ui_item, sub_cmp, ext_asm_info))
        except KeyError:
            logger.debug('Can not find create function for: {}'.format(sub_cmp))

        logger.debug('UI item created by create func is: {}'.format(ui_item))

        if ui_item and sub_cmp.is_container:
                _recursively_produce_ui_items(ui_item, sub_cmp, ext_asm_info)


current_ui = get_current_ui()


def update_pyrevit_ui(parsed_ext, ext_asm_info):
    """Updates/Creates pyRevit ui for the given extension and provided assembly dll address.
    """
    logger.debug('Creating/Updating ui for extension: {}'.format(parsed_ext))
    _recursively_produce_ui_items(current_ui, parsed_ext, ext_asm_info)


def cleanup_pyrevit_ui():
    untouched_items = current_ui.get_unchanged_items()
    for item in untouched_items:
        if not item.is_native():
            try:
                logger.debug('Deactivating: {}'.format(item))
                item.deactivate()
            except Exception as deact_err:
                logger.debug(deact_err)
