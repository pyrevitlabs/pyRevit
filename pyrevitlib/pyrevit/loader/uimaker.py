"""UI maker."""
import sys
import imp

from pyrevit import HOST_APP, EXEC_PARAMS, PyRevitException
from pyrevit.coreutils import assmutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import applocales
from pyrevit.api import UI

from pyrevit.coreutils import ribbon

# For event handlers in IronPython
from System import EventHandler
from Autodesk.Revit.UI.Events import ComboBoxCurrentChangedEventArgs

#pylint: disable=W0703,C0302,C0103,C0413
import pyrevit.extensions as exts
from pyrevit.extensions import components
from pyrevit.userconfig import user_config


mlogger = get_logger(__name__)

# Enable verbose logging to see WARNING messages (can be removed later)
# Uncomment the line below to see all log messages:
# mlogger.set_verbose_mode()


CONFIG_SCRIPT_TITLE_POSTFIX = u'\u25CF'


class UIMakerParams:
    """UI maker parameters.

    Args:
        par_ui (_PyRevitUI): Parent UI item
        par_cmp (GenericUIComponent): Parent UI component
        cmp_item (GenericUIComponent): UI component item
        asm_info (AssemblyInfo): Assembly info
        create_beta (bool, optional): Create beta button. Defaults to False
    """
    def __init__(self, par_ui, par_cmp, cmp_item, asm_info, create_beta=False):
        self.parent_ui = par_ui
        self.parent_cmp = par_cmp
        self.component = cmp_item
        self.asm_info = asm_info
        self.create_beta_cmds = create_beta


def _make_button_tooltip(button):
    tooltip = button.tooltip + '\n\n' if button.tooltip else ''
    tooltip += 'Bundle Name:\n{} ({})'\
        .format(button.name, button.type_id.replace('.', ''))
    if button.author:
        tooltip += '\n\nAuthor(s):\n{}'.format(button.author)
    return tooltip


def _make_button_tooltip_ext(button, asm_name):

    tooltip_ext = ''

    if button.min_revit_ver and not button.max_revit_ver:
        tooltip_ext += 'Compatible with {} {} and above\n\n'\
            .format(HOST_APP.proc_name,
                    button.min_revit_ver)

    if button.max_revit_ver and not button.min_revit_ver:
        tooltip_ext += 'Compatible with {} {} and earlier\n\n'\
            .format(HOST_APP.proc_name,
                    button.max_revit_ver)

    if button.min_revit_ver and button.max_revit_ver:
        if int(button.min_revit_ver) != int(button.max_revit_ver):
            tooltip_ext += 'Compatible with {} {} to {}\n\n'\
                .format(HOST_APP.proc_name,
                        button.min_revit_ver, button.max_revit_ver)
        else:
            tooltip_ext += 'Compatible with {} {} only\n\n'\
                .format(HOST_APP.proc_name,
                        button.min_revit_ver)

    if isinstance(button, (components.LinkButton, components.InvokeButton)):
        tooltip_ext += 'Class Name:\n{}\n\nAssembly Name:\n{}\n\n'.format(
            button.command_class or 'Runs first matching DB.IExternalCommand',
            button.assembly)
    else:
        tooltip_ext += 'Class Name:\n{}\n\nAssembly Name:\n{}\n\n'\
            .format(button.unique_name, asm_name)

    if button.control_id:
        tooltip_ext += 'Control Id:\n{}'\
            .format(button.control_id)

    return tooltip_ext


def _make_tooltip_ext_if_requested(button, asm_name):
    if user_config.tooltip_debug_info:
        return _make_button_tooltip_ext(button, asm_name)


def _make_ui_title(button):
    if button.has_config_script():
        return button.ui_title + ' {}'.format(CONFIG_SCRIPT_TITLE_POSTFIX)
    else:
        return button.ui_title


def _make_full_class_name(asm_name, class_name):
    if asm_name and class_name:
        return '{}.{}'.format(asm_name, class_name)
    return None


def _set_highlights(button, ui_item):
    ui_item.reset_highlights()
    if button.highlight_type == exts.MDATA_HIGHLIGHT_TYPE_UPDATED:
        ui_item.highlight_as_updated()
    elif button.highlight_type == exts.MDATA_HIGHLIGHT_TYPE_NEW:
        ui_item.highlight_as_new()


def _get_effective_classname(button):
    """Verifies if button has class_name set.

    This means that typemaker has created a executor type for this command.
    If class_name is not set, this function returns button.unique_name.
    This allows for the UI button to be created and linked to the previously 
    created assembly.
    If the type does not exist in the assembly, the UI button will not work,
    however this allows updating the command with the correct executor type,
    once command script has been fixed and pyrevit is reloaded.

    Args:
        button (pyrevit.extensions.genericcomps.GenericUICommand): button

    Returns:
        (str): class_name (or unique_name if class_name is None)
    """
    return button.class_name if button.class_name else button.unique_name


def _produce_ui_separator(ui_maker_params):
    """Create a separator.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui_item = ui_maker_params.parent_ui
    ext_asm_info = ui_maker_params.asm_info

    if not ext_asm_info.reloading:
        mlogger.debug('Adding separator to: %s', parent_ui_item)
        try:
            if hasattr(parent_ui_item, 'add_separator'):    # re issue #361
                parent_ui_item.add_separator()
        except PyRevitException as err:
            mlogger.error('UI error: %s', err.msg)

    return None


def _produce_ui_slideout(ui_maker_params):
    """Create a slide out.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui_item = ui_maker_params.parent_ui
    ext_asm_info = ui_maker_params.asm_info

    if not ext_asm_info.reloading:
        # Log panel items before adding slideout (for debugging order issues)
        try:
            if hasattr(parent_ui_item, 'get_rvtapi_object'):
                existing_items = parent_ui_item.get_rvtapi_object().GetItems()
                mlogger.warning('SLIDEOUT: Panel has %d items before adding slideout', len(existing_items))
                for idx, item in enumerate(existing_items):
                    mlogger.warning('SLIDEOUT: Existing item %d: %s (type: %s)', 
                                   idx, getattr(item, 'Name', 'unknown'), type(item).__name__)
        except Exception as log_err:
            mlogger.debug('SLIDEOUT: Could not log existing items: %s', log_err)
        
        mlogger.warning('SLIDEOUT: Adding slide out to: %s', parent_ui_item)
        try:
            parent_ui_item.add_slideout()
            mlogger.warning('SLIDEOUT: Slideout added successfully')
        except PyRevitException as err:
            mlogger.error('UI error: %s', err.msg)

    return None


def _produce_ui_smartbutton(ui_maker_params):
    """Create a smart button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui_item = ui_maker_params.parent_ui
    parent = ui_maker_params.parent_cmp
    smartbutton = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    if not smartbutton.is_supported:
        return None

    if smartbutton.is_beta and not ui_maker_params.create_beta_cmds:
        return None

    mlogger.debug('Producing smart button: %s', smartbutton)
    try:
        parent_ui_item.create_push_button(
            button_name=smartbutton.name,
            asm_location=ext_asm_info.location,
            class_name=_get_effective_classname(smartbutton),
            icon_path=smartbutton.icon_file or parent.icon_file,
            tooltip=_make_button_tooltip(smartbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(smartbutton,
                                                       ext_asm_info.name),
            tooltip_media=smartbutton.media_file,
            ctxhelpurl=smartbutton.help_url,
            avail_class_name=smartbutton.avail_class_name,
            update_if_exists=True,
            ui_title=_make_ui_title(smartbutton))
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None

    smartbutton_ui = parent_ui_item.button(smartbutton.name)

    mlogger.debug('Importing smart button as module: %s', smartbutton)
    try:
        # replacing EXEC_PARAMS.command_name value with button name so the
        # init script can log under its own name
        prev_commandname = \
            __builtins__['__commandname__'] \
            if '__commandname__' in __builtins__ else None
        prev_commandpath = \
            __builtins__['__commandpath__'] \
            if '__commandpath__' in __builtins__ else None
        prev_shiftclick = \
            __builtins__['__shiftclick__'] \
            if '__shiftclick__' in __builtins__ else False
        prev_debugmode = \
            __builtins__['__forceddebugmode__'] \
            if '__forceddebugmode__' in __builtins__ else False

        __builtins__['__commandname__'] = smartbutton.name
        __builtins__['__commandpath__'] = smartbutton.script_file
        __builtins__['__shiftclick__'] = False
        __builtins__['__forceddebugmode__'] = False
    except Exception as err:
        mlogger.error('Smart button setup error: %s | %s', smartbutton, err)
        return smartbutton_ui

    try:
        # setup sys.paths for the smart command
        current_paths = list(sys.path)
        for search_path in smartbutton.module_paths:
            if search_path not in current_paths:
                sys.path.append(search_path)

        # importing smart button script as a module
        importedscript = imp.load_source(smartbutton.unique_name,
                                         smartbutton.script_file)
        # resetting EXEC_PARAMS.command_name to original
        __builtins__['__commandname__'] = prev_commandname
        __builtins__['__commandpath__'] = prev_commandpath
        __builtins__['__shiftclick__'] = prev_shiftclick
        __builtins__['__forceddebugmode__'] = prev_debugmode
        mlogger.debug('Import successful: %s', importedscript)
        mlogger.debug('Running self initializer: %s', smartbutton)

        # reset sys.paths back to normal
        sys.path = current_paths

        res = False
        try:
            # running the smart button initializer function
            res = importedscript.__selfinit__(smartbutton,
                                              smartbutton_ui, HOST_APP.uiapp)
        except Exception as button_err:
            mlogger.error('Error initializing smart button: %s | %s',
                          smartbutton, button_err)

        # if the __selfinit__ function returns False
        # remove the button
        if res is False:
            mlogger.debug('SelfInit returned False on Smartbutton: %s',
                          smartbutton_ui)
            smartbutton_ui.deactivate()

        mlogger.debug('SelfInit successful on Smartbutton: %s', smartbutton_ui)
    except Exception as err:
        mlogger.error('Smart button script import error: %s | %s',
                      smartbutton, err)
        return smartbutton_ui

    _set_highlights(smartbutton, smartbutton_ui)

    return smartbutton_ui


def _produce_ui_linkbutton(ui_maker_params):
    """Create a link button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui_item = ui_maker_params.parent_ui
    parent = ui_maker_params.parent_cmp
    linkbutton = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    if not linkbutton.is_supported:
        return None

    if linkbutton.is_beta and not ui_maker_params.create_beta_cmds:
        return None

    mlogger.debug('Producing button: %s', linkbutton)
    try:
        linked_asm = None
        # attemp to find the assembly file
        linked_asm_file = linkbutton.get_target_assembly()
        # if not found, search the loaded assemblies
        # this is usually a slower process
        if linked_asm_file:
            linked_asm = assmutils.load_asm_file(linked_asm_file)
        else:
            linked_asm_list = assmutils.find_loaded_asm(linkbutton.assembly)
            # cancel button creation if not found
            if not linked_asm_list:
                mlogger.error("Can not find target assembly for %s", linkbutton)
                return None
            linked_asm = linked_asm_list[0]

        linked_asm_name = linked_asm.GetName().Name
        parent_ui_item.create_push_button(
            button_name=linkbutton.name,
            asm_location=linked_asm.Location,
            class_name=_make_full_class_name(
                linked_asm_name,
                linkbutton.command_class
                ),
            icon_path=linkbutton.icon_file or parent.icon_file,
            tooltip=_make_button_tooltip(linkbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(linkbutton,
                                                       ext_asm_info.name),
            tooltip_media=linkbutton.media_file,
            ctxhelpurl=linkbutton.help_url,
            avail_class_name=_make_full_class_name(
                linked_asm_name,
                linkbutton.avail_command_class
                ),
            update_if_exists=True,
            ui_title=_make_ui_title(linkbutton))
        linkbutton_ui = parent_ui_item.button(linkbutton.name)

        _set_highlights(linkbutton, linkbutton_ui)

        return linkbutton_ui
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None


def _produce_ui_pushbutton(ui_maker_params):
    """Create a push button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui_item = ui_maker_params.parent_ui
    parent = ui_maker_params.parent_cmp
    pushbutton = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    if not pushbutton.is_supported:
        return None

    if pushbutton.is_beta and not ui_maker_params.create_beta_cmds:
        return None

    mlogger.debug('Producing button: %s', pushbutton)
    try:
        parent_ui_item.create_push_button(
            button_name=pushbutton.name,
            asm_location=ext_asm_info.location,
            class_name=_get_effective_classname(pushbutton),
            icon_path=pushbutton.icon_file or parent.icon_file,
            tooltip=_make_button_tooltip(pushbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(pushbutton,
                                                       ext_asm_info.name),
            tooltip_media=pushbutton.media_file,
            ctxhelpurl=pushbutton.help_url,
            avail_class_name=pushbutton.avail_class_name,
            update_if_exists=True,
            ui_title=_make_ui_title(pushbutton))
        pushbutton_ui = parent_ui_item.button(pushbutton.name)

        _set_highlights(pushbutton, pushbutton_ui)

        return pushbutton_ui
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None


def _produce_ui_pulldown(ui_maker_params):
    """Create a pulldown button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    pulldown = ui_maker_params.component

    mlogger.debug('Producing pulldown button: %s', pulldown)
    try:
        parent_ribbon_panel.create_pulldown_button(pulldown.ui_title,
                                                   pulldown.icon_file,
                                                   update_if_exists=True)
        pulldown_ui = parent_ribbon_panel.ribbon_item(pulldown.ui_title)

        _set_highlights(pulldown, pulldown_ui)

        return pulldown_ui
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None


def _produce_ui_combobox(ui_maker_params):
    """Create a ComboBox - bare minimum implementation.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    combobox = ui_maker_params.component

    mlogger.warning('COMBOBOX: Creating ComboBox: %s', combobox.name)
    print("=== COMBOBOX: Creating ComboBox: {} ===".format(combobox.name))
    
    # Validate parent panel
    if not parent_ribbon_panel:
        mlogger.error('COMBOBOX: Parent ribbon panel is None for: %s', combobox.name)
        print("COMBOBOX ERROR: Parent ribbon panel is None")
        return None
        
    # Log panel info for debugging
    try:
        panel_name = getattr(parent_ribbon_panel, 'name', 'unknown')
        panel_type = str(type(parent_ribbon_panel))
        mlogger.warning('COMBOBOX: Parent panel: %s (type: %s)', panel_name, panel_type)
        # Warn if panel name suggests it might be native (common native panel names)
        native_panel_names = ['Utility', 'Modify', 'Annotate', 'Architecture', 'Structure', 'Systems']
        if panel_name in native_panel_names:
            mlogger.error('COMBOBOX: WARNING - Panel "%s" appears to be a native Revit panel! '
                         'Native panels do not support ComboBoxes. This will fail.', panel_name)
    except Exception:
        pass
    
    try:
        # Log current panel items before adding ComboBox (for debugging order issues)
        # NOTE: Revit's AddItem() always appends to the end, so if the panel already
        # has items, the ComboBox will appear at the end regardless of layout order.
        # This is a limitation of Revit's ribbon API - there's no way to insert at
        # a specific position.
        try:
            existing_items = parent_ribbon_panel.get_rvtapi_object().GetItems()
            item_count = len(existing_items)
            mlogger.warning('COMBOBOX: Panel has %d items before adding ComboBox', item_count)
            if item_count > 0:
                mlogger.warning('COMBOBOX: WARNING - Panel already has items. ComboBox will be added at the end (position %d), '
                               'not at the position specified in layout. This is a Revit API limitation.', item_count)
            for idx, item in enumerate(existing_items):
                mlogger.warning('COMBOBOX: Existing item %d: %s (type: %s)', 
                               idx, getattr(item, 'Name', 'unknown'), type(item).__name__)
        except Exception as log_err:
            mlogger.debug('COMBOBOX: Could not log existing items: %s', log_err)
        
        # Create or get existing ComboBox using panel's create_combobox method
        # Note: create_combobox doesn't return the wrapper, so we get it separately
        mlogger.warning('COMBOBOX: About to create ComboBox: %s', combobox.name)
        parent_ribbon_panel.create_combobox(combobox.name, update_if_exists=True)
        combobox_ui = parent_ribbon_panel.ribbon_item(combobox.name)
        
        # Log panel items after adding ComboBox
        try:
            items_after = parent_ribbon_panel.get_rvtapi_object().GetItems()
            mlogger.warning('COMBOBOX: Panel has %d items after adding ComboBox', len(items_after))
            for idx, item in enumerate(items_after):
                mlogger.warning('COMBOBOX: Item %d: %s (type: %s)', 
                               idx, getattr(item, 'Name', 'unknown'), type(item).__name__)
        except Exception as log_err:
            mlogger.debug('COMBOBOX: Could not log items after creation: %s', log_err)
        
        if not combobox_ui:
            mlogger.error('COMBOBOX: Failed to get ComboBox UI item: %s', combobox.name)
            print("COMBOBOX ERROR: Failed to get ComboBox UI item: {}".format(combobox.name))
            return None
        
        # Get the Revit API ComboBox object
        # This may fail if the panel is native (e.g., "Utility") which doesn't support ComboBoxes
        try:
            combobox_obj = combobox_ui.get_rvtapi_object()
        except Exception as rvtapi_err:
            mlogger.error('COMBOBOX: get_rvtapi_object() failed for %s (panel may be native): %s', 
                         combobox.name, rvtapi_err)
            print("COMBOBOX ERROR: get_rvtapi_object() failed: {}".format(rvtapi_err))
            return None
        
        if not combobox_obj:
            mlogger.error('COMBOBOX: get_rvtapi_object() returned None for: %s', combobox.name)
            print("COMBOBOX ERROR: get_rvtapi_object() returned None")
            return None
        
        # Log type for debugging (try GetType() first, fallback to Python type)
        try:
            obj_type = combobox_obj.GetType()
            mlogger.warning('COMBOBOX: rvtapi object type: %s', obj_type)
            print("COMBOBOX: rvtapi object type: {}".format(obj_type))
        except Exception:
            mlogger.warning('COMBOBOX: rvtapi object type (python): %s', type(combobox_obj))
            print("COMBOBOX: rvtapi object type (python): {}".format(type(combobox_obj)))
        
        # Guard: If we're still in data mode (stack), we cannot attach events yet
        if isinstance(combobox_obj, UI.ComboBoxData):
            mlogger.warning('COMBOBOX: %s is still UI.ComboBoxData (itemdata_mode). '
                            'Skipping event wiring for now.', combobox.name)
            print("COMBOBOX WARNING: ComboBox is still ComboBoxData (itemdata_mode) - skipping event wiring")
            return combobox_ui
        
        # Set ItemText (required for ComboBox to display)
        combobox_obj.ItemText = combobox.ui_title or combobox.name
        
        # Clear existing members and add fresh ones (cache fix ensures fresh data)
        # Note: Revit API doesn't support removing individual members, so we add all
        # The cache fix ensures we get fresh members from metadata
        existing_items = combobox_obj.GetItems()
        if existing_items and len(existing_items) > 0:
            mlogger.warning('COMBOBOX: %s already has %d members (will add new ones)', 
                          combobox.name, len(existing_items))
        
        # Add members from metadata
        if combobox.members:
            for member in combobox.members:
                # Handle different member formats
                if isinstance(member, (list, tuple)) and len(member) >= 2:
                    member_id, member_text = member[0], member[1]
                elif isinstance(member, dict) or (hasattr(member, 'get') and hasattr(member, 'keys')):
                    # OrderedDict or dict format (defensive - should be handled in components.py)
                    member_id = member.get('id', member.get('name', ''))
                    member_text = member.get('text', member.get('title', member_id))
                elif isinstance(member, str):
                    member_id = member_text = member
                else:
                    mlogger.warning('COMBOBOX: Skipping invalid member format: %s (type: %s)', member, type(member))
                    continue
                
                # Create ComboBoxMemberData and add to ComboBox
                member_data = UI.ComboBoxMemberData(member_id, member_text)
                combobox_obj.AddItem(member_data)
                mlogger.warning('COMBOBOX: Added member: %s (%s)', member_text, member_id)
        
        # Set Current to first item if members exist
        items = combobox_obj.GetItems()
        if items and len(items) > 0:
            combobox_obj.Current = items[0]
            combobox_obj.ItemText = items[0].ItemText
            mlogger.warning('COMBOBOX: Set current item: %s', items[0].ItemText)
        
        # Subscribe to CurrentChanged event to handle selection changes
        # Remove existing handler if updating to avoid duplicate subscriptions
        prev_handler = getattr(combobox_ui, '_current_changed_handler', None)
        if prev_handler:
            try:
                combobox_obj.CurrentChanged -= prev_handler
                mlogger.warning('COMBOBOX: Removed previous CurrentChanged handler: %s', combobox.name)
            except Exception as ex:
                mlogger.debug('COMBOBOX: Could not remove previous handler: %s', ex)
        
        # Create event handler function (use sender, not captured combobox_obj)
        # Store handler reference on combobox_ui to prevent garbage collection
        def on_combobox_changed(sender, args):
            """Handle ComboBox selection change."""
            try:
                # Use sender instead of captured combobox_obj
                current_item = sender.Current
                if current_item:
                    selected_text = current_item.ItemText
                    selected_id = current_item.Name
                    mlogger.warning('COMBOBOX: Selection changed: %s (id: %s)', selected_text, selected_id)
                    # TODO: Execute the corresponding script function based on selected_id
                    # This would require loading and executing the script module
                else:
                    mlogger.warning('COMBOBOX: Selection changed, but Current is None')
            except Exception as event_err:
                mlogger.error('COMBOBOX: Error in event handler: %s', event_err)
        
        # Try simple direct assignment first (like WPF events in ribbon.py)
        # Store handler reference to prevent garbage collection
        combobox_ui._current_changed_handler = on_combobox_changed
        try:
            combobox_obj.CurrentChanged += combobox_ui._current_changed_handler
            mlogger.warning('COMBOBOX: Attached CurrentChanged handler (direct): %s', combobox.name)
        except (TypeError, AttributeError) as direct_err:
            # If direct assignment fails, try with explicit EventHandler wrapper
            mlogger.warning('COMBOBOX: Direct assignment failed, trying EventHandler wrapper: %s', direct_err)
            try:
                handler = EventHandler[ComboBoxCurrentChangedEventArgs](on_combobox_changed)
                combobox_ui._current_changed_handler = handler
                combobox_obj.CurrentChanged += handler
                mlogger.warning('COMBOBOX: Attached CurrentChanged handler (wrapped): %s', combobox.name)
            except Exception as wrapped_err:
                mlogger.error('COMBOBOX: Both direct and wrapped event handler failed: %s', wrapped_err)
        
        # Set highlights (may fail if AdWindows object not available, but that's OK)
        try:
            _set_highlights(combobox, combobox_ui)
        except Exception as highlight_err:
            mlogger.debug('COMBOBOX: Could not set highlights: %s', highlight_err)
        
        # Ensure ComboBox is visible and enabled
        try:
            if hasattr(combobox_obj, 'Visible'):
                combobox_obj.Visible = True
            if hasattr(combobox_obj, 'Enabled'):
                combobox_obj.Enabled = True
            mlogger.warning('COMBOBOX: Set Visible=True, Enabled=True')
        except Exception as vis_err:
            mlogger.debug('COMBOBOX: Could not set visibility: %s', vis_err)
        
        # Activate the ComboBox UI item
        try:
            combobox_ui.activate()
            mlogger.warning('COMBOBOX: Activated ComboBox UI item')
        except Exception as activate_err:
            mlogger.warning('COMBOBOX: Could not activate: %s', activate_err)
        
        # Final verification - check if ComboBox is in the panel
        try:
            panel_items = parent_ribbon_panel.ribbon_item(combobox.name)
            if panel_items:
                mlogger.warning('COMBOBOX: Verified ComboBox exists in panel')
            else:
                mlogger.error('COMBOBOX: ComboBox not found in panel after creation!')
        except Exception as verify_err:
            mlogger.debug('COMBOBOX: Could not verify panel item: %s', verify_err)
        
        mlogger.warning('COMBOBOX: Created successfully: %s', combobox.name)
        print("=== COMBOBOX: Created successfully: {} ===".format(combobox.name))
        return combobox_ui
    except PyRevitException as err:
        mlogger.error('COMBOBOX: UI error creating: %s', err.msg)
        return None
    except Exception as err:
        mlogger.error('COMBOBOX: Error creating: %s', err)
        import traceback
        mlogger.error('COMBOBOX: %s', traceback.format_exc())
        return None


def _produce_ui_split(ui_maker_params):
    """Produce a split button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    split = ui_maker_params.component

    mlogger.debug('Producing split button: %s}', split)
    try:
        parent_ribbon_panel.create_split_button(split.ui_title,
                                                split.icon_file,
                                                update_if_exists=True)
        split_ui = parent_ribbon_panel.ribbon_item(split.ui_title)

        _set_highlights(split, split_ui)

        return split_ui
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None


def _produce_ui_splitpush(ui_maker_params):
    """Create split push button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    splitpush = ui_maker_params.component

    mlogger.debug('Producing splitpush button: %s', splitpush)
    try:
        parent_ribbon_panel.create_splitpush_button(splitpush.ui_title,
                                                    splitpush.icon_file,
                                                    update_if_exists=True)
        splitpush_ui = parent_ribbon_panel.ribbon_item(splitpush.ui_title)

        _set_highlights(splitpush, splitpush_ui)

        return splitpush_ui
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None


def _produce_ui_stacks(ui_maker_params):
    """Create a stack of ui items.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui_panel = ui_maker_params.parent_ui
    stack_parent = ui_maker_params.parent_cmp
    stack_cmp = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    # if sub_cmp is a stack, ask parent_ui_item to open a stack
    # (parent_ui_item.open_stack).
    # All subsequent items will be placed under this stack. Close the stack
    # (parent_ui_item.close_stack) to finish adding items to the stack.
    try:
        parent_ui_panel.open_stack()
        mlogger.debug('Opened stack: %s', stack_cmp.name)

        if HOST_APP.is_older_than('2017'):
            _component_creation_dict[exts.SPLIT_BUTTON_POSTFIX] = \
                _produce_ui_pulldown
            _component_creation_dict[exts.SPLITPUSH_BUTTON_POSTFIX] = \
                _produce_ui_pulldown

        # capturing and logging any errors on stack item
        # (e.g when parent_ui_panel's stack is full and can not add any
        # more items it will raise an error)
        _recursively_produce_ui_items(
            UIMakerParams(parent_ui_panel,
                          stack_parent,
                          stack_cmp,
                          ext_asm_info,
                          ui_maker_params.create_beta_cmds))

        if HOST_APP.is_older_than('2017'):
            _component_creation_dict[exts.SPLIT_BUTTON_POSTFIX] = \
                _produce_ui_split
            _component_creation_dict[exts.SPLITPUSH_BUTTON_POSTFIX] = \
                _produce_ui_splitpush

        try:
            parent_ui_panel.close_stack()
            mlogger.debug('Closed stack: %s', stack_cmp.name)
            return stack_cmp
        except PyRevitException as err:
            mlogger.error('Error creating stack | %s', err)

    except Exception as err:
        mlogger.error('Can not create stack under this parent: %s | %s',
                      parent_ui_panel, err)


def _produce_ui_panelpushbutton(ui_maker_params):
    """Create a push button with the given parameters.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui_item = ui_maker_params.parent_ui
    # parent = ui_maker_params.parent_cmp
    panelpushbutton = ui_maker_params.component
    ext_asm_info = ui_maker_params.asm_info

    if panelpushbutton.is_beta and not ui_maker_params.create_beta_cmds:
        return None

    mlogger.debug('Producing panel button: %s', panelpushbutton)
    try:
        parent_ui_item.create_panel_push_button(
            button_name=panelpushbutton.name,
            asm_location=ext_asm_info.location,
            class_name=_get_effective_classname(panelpushbutton),
            tooltip=_make_button_tooltip(panelpushbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(panelpushbutton,
                                                       ext_asm_info.name),
            tooltip_media=panelpushbutton.media_file,
            ctxhelpurl=panelpushbutton.help_url,
            avail_class_name=panelpushbutton.avail_class_name,
            update_if_exists=True,
            ui_title=_make_ui_title(panelpushbutton))

        panelpushbutton_ui = parent_ui_item.button(panelpushbutton.name)

        _set_highlights(panelpushbutton, panelpushbutton_ui)

        return panelpushbutton_ui
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None


def _produce_ui_panels(ui_maker_params):
    """Create a panel with the given parameters.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.

    Returns:
        (RevitNativeRibbonPanel): The created panel
    """
    parent_ui_tab = ui_maker_params.parent_ui
    panel = ui_maker_params.component

    if panel.is_beta and not ui_maker_params.create_beta_cmds:
        return None

    mlogger.debug('Producing ribbon panel: %s', panel)
    try:
        parent_ui_tab.create_ribbon_panel(panel.ui_title, update_if_exists=True)
        panel_ui = parent_ui_tab.ribbon_panel(panel.ui_title)

        # set backgrounds
        panel_ui.reset_backgrounds()
        if panel.panel_background:
            panel_ui.set_background(panel.panel_background)
        # override the title background if exists
        if panel.title_background:
            panel_ui.set_title_background(panel.title_background)
        # override the slideout background if exists
        if panel.slideout_background:
            panel_ui.set_slideout_background(panel.slideout_background)

        _set_highlights(panel, panel_ui)

        panel_ui.set_collapse(panel.collapsed)

        return panel_ui
    except PyRevitException as err:
        mlogger.error('UI error: %s', err.msg)
        return None


def _produce_ui_tab(ui_maker_params):
    """Create a tab with the given parameters.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui = ui_maker_params.parent_ui
    tab = ui_maker_params.component

    mlogger.debug('Verifying tab: %s', tab)
    if tab.has_commands():
        mlogger.debug('Tabs has command: %s', tab)
        mlogger.debug('Producing ribbon tab: %s', tab)
        try:
            parent_ui.create_ribbon_tab(tab.name, update_if_exists=True)
            tab_ui = parent_ui.ribbon_tab(tab.name)

            _set_highlights(tab, tab_ui)

            return tab_ui
        except PyRevitException as err:
            # If tab is native, log as warning instead of error
            if 'native item' in err.msg.lower():
                mlogger.warning('UI warning (tab may be native): %s', err.msg)
            else:
                mlogger.error('UI error: %s', err.msg)
                return None
    else:
        mlogger.debug('Tab does not have any commands. Skipping: %s', tab.name)
        return None


_component_creation_dict = {
    exts.TAB_POSTFIX: _produce_ui_tab,
    exts.PANEL_POSTFIX: _produce_ui_panels,
    exts.STACK_BUTTON_POSTFIX: _produce_ui_stacks,
    exts.PULLDOWN_BUTTON_POSTFIX: _produce_ui_pulldown,
    exts.COMBOBOX_POSTFIX: _produce_ui_combobox,
    exts.SPLIT_BUTTON_POSTFIX: _produce_ui_split,
    exts.SPLITPUSH_BUTTON_POSTFIX: _produce_ui_splitpush,
    exts.PUSH_BUTTON_POSTFIX: _produce_ui_pushbutton,
    exts.SMART_BUTTON_POSTFIX: _produce_ui_smartbutton,
    exts.CONTENT_BUTTON_POSTFIX: _produce_ui_pushbutton,
    exts.URL_BUTTON_POSTFIX: _produce_ui_pushbutton,
    exts.LINK_BUTTON_POSTFIX: _produce_ui_linkbutton,
    exts.INVOKE_BUTTON_POSTFIX: _produce_ui_pushbutton,
    exts.SEPARATOR_IDENTIFIER: _produce_ui_separator,
    exts.SLIDEOUT_IDENTIFIER: _produce_ui_slideout,
    exts.PANEL_PUSH_BUTTON_POSTFIX: _produce_ui_panelpushbutton,
    }


def _recursively_produce_ui_items(ui_maker_params):
    cmp_count = 0
    for sub_cmp in ui_maker_params.component:
        ui_item = None
        try:
            # Diagnostic logging to track panel placement issues
            parent_name = getattr(ui_maker_params.parent_ui, 'name', None)
            if not parent_name:
                try:
                    parent_name = str(type(ui_maker_params.parent_ui))
                except:
                    parent_name = 'unknown'
            mlogger.warning('BUILDING COMPONENT: %s parent: %s', sub_cmp.name, parent_name)
            
            mlogger.debug('Calling create func %s for: %s',
                          _component_creation_dict[sub_cmp.type_id],
                          sub_cmp)
            ui_item = _component_creation_dict[sub_cmp.type_id](
                UIMakerParams(ui_maker_params.parent_ui,
                              ui_maker_params.component,
                              sub_cmp,
                              ui_maker_params.asm_info,
                              ui_maker_params.create_beta_cmds))
            if ui_item:
                cmp_count += 1
        except KeyError:
            mlogger.warning('Can not find create function for type_id: %s (component: %s)', 
                          sub_cmp.type_id, sub_cmp)
        except Exception as create_err:
            mlogger.critical(
                'Error creating item: %s | %s', sub_cmp, create_err
            )

        mlogger.debug('UI item created by create func is: %s', ui_item)
        # if component does not have any sub components hide it
        # Exclude GenericStack and ComboBoxGroup from deactivation check
        # (GenericStack is a special container, ComboBoxGroup has members not child components)
        if ui_item \
                and not isinstance(ui_item, components.GenericStack) \
                and not isinstance(sub_cmp, components.ComboBoxGroup) \
                and sub_cmp.is_container:
            subcmp_count = _recursively_produce_ui_items(
                UIMakerParams(ui_item,
                              ui_maker_params.component,
                              sub_cmp,
                              ui_maker_params.asm_info,
                              ui_maker_params.create_beta_cmds))

            # if component does not have any sub components hide it
            if subcmp_count == 0:
                ui_item.deactivate()

    return cmp_count


current_ui = ribbon.get_current_ui()


def update_pyrevit_ui(ui_ext, ext_asm_info, create_beta=False):
    """Updates/Creates pyRevit ui for the extension and assembly dll address.

    Args:
        ui_ext (GenericUIContainer): UI container.
        ext_asm_info (AssemblyInfo): Assembly info.
        create_beta (bool, optional): Create beta ui. Defaults to False.
    """
    mlogger.debug('Creating/Updating ui for extension: %s', ui_ext)
    cmp_count = _recursively_produce_ui_items(
        UIMakerParams(current_ui, None, ui_ext, ext_asm_info, create_beta))
    mlogger.debug('%s components were created for: %s', cmp_count, ui_ext)


def sort_pyrevit_ui(ui_ext):
    """Sorts pyRevit UI.

    Args:
        ui_ext (GenericUIContainer): UI container.
    """
    # only works on panels so far
    # re-ordering of ui components deeper than panels have not been implemented
    for tab in current_ui.get_pyrevit_tabs():
        for litem in ui_ext.find_layout_items():
            if litem.directive:
                if litem.directive.directive_type == 'before':
                    tab.reorder_before(litem.name, litem.directive.target)
                elif litem.directive.directive_type == 'after':
                    tab.reorder_after(litem.name, litem.directive.target)
                elif litem.directive.directive_type == 'afterall':
                    tab.reorder_afterall(litem.name)
                elif litem.directive.directive_type == 'beforeall':
                    tab.reorder_beforeall(litem.name)


def cleanup_pyrevit_ui():
    """Cleanup the pyrevit UI.

    Hide all items that were not touched after a reload
    meaning they have been removed in extension folder structure
    and thus are not updated.
    """
    untouched_items = current_ui.get_unchanged_items()
    for item in untouched_items:
        if not item.is_native():
            try:
                mlogger.debug('Deactivating: %s', item)
                item.deactivate()
            except Exception as deact_err:
                # Log as debug to avoid cluttering output with expected errors
                mlogger.debug('Could not deactivate item (may be native): %s | %s', item, deact_err)


def reflow_pyrevit_ui(direction=applocales.DEFAULT_LANG_DIR):
    """Set the flow direction of the tabs."""
    if direction == "LTR":
        current_ui.set_LTR_flow()
    elif direction == "RTL":
        current_ui.set_RTL_flow()
