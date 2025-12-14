# -*- coding: utf-8 -*-
"""UI maker."""
import sys
import imp
import os.path as op

from pyrevit import HOST_APP, PyRevitException
from pyrevit.coreutils import assmutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import applocales
from pyrevit.api import UI

from pyrevit.coreutils import ribbon
from pyrevit.coreutils.ribbon import ICON_MEDIUM

# pylint: disable=W0703,C0302,C0103,C0413
import pyrevit.extensions as exts
from pyrevit.extensions import components
from pyrevit.userconfig import user_config


mlogger = get_logger(__name__)


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
    tooltip = button.tooltip + "\n\n" if button.tooltip else ""
    tooltip += "Bundle Name:\n{} ({})".format(
        button.name, button.type_id.replace(".", "")
    )
    if button.author:
        tooltip += "\n\nAuthor(s):\n{}".format(button.author)
    return tooltip


def _make_button_tooltip_ext(button, asm_name):

    tooltip_ext = ""

    if button.min_revit_ver and not button.max_revit_ver:
        tooltip_ext += "Compatible with {} {} and above\n\n".format(
            HOST_APP.proc_name, button.min_revit_ver
        )

    if button.max_revit_ver and not button.min_revit_ver:
        tooltip_ext += "Compatible with {} {} and earlier\n\n".format(
            HOST_APP.proc_name, button.max_revit_ver
        )

    if button.min_revit_ver and button.max_revit_ver:
        if int(button.min_revit_ver) != int(button.max_revit_ver):
            tooltip_ext += "Compatible with {} {} to {}\n\n".format(
                HOST_APP.proc_name, button.min_revit_ver, button.max_revit_ver
            )
        else:
            tooltip_ext += "Compatible with {} {} only\n\n".format(
                HOST_APP.proc_name, button.min_revit_ver
            )

    if isinstance(button, (components.LinkButton, components.InvokeButton)):
        tooltip_ext += "Class Name:\n{}\n\nAssembly Name:\n{}\n\n".format(
            button.command_class or "Runs first matching DB.IExternalCommand",
            button.assembly,
        )
    else:
        tooltip_ext += "Class Name:\n{}\n\nAssembly Name:\n{}\n\n".format(
            button.unique_name, asm_name
        )

    if button.control_id:
        tooltip_ext += "Control Id:\n{}".format(button.control_id)

    return tooltip_ext


def _make_tooltip_ext_if_requested(button, asm_name):
    if user_config.tooltip_debug_info:
        return _make_button_tooltip_ext(button, asm_name)


def _make_ui_title(button):
    if button.has_config_script():
        return button.ui_title + " {}".format(CONFIG_SCRIPT_TITLE_POSTFIX)
    else:
        return button.ui_title


def _make_full_class_name(asm_name, class_name):
    if asm_name and class_name:
        return "{}.{}".format(asm_name, class_name)
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
        mlogger.debug("Adding separator to: %s", parent_ui_item)
        try:
            if hasattr(parent_ui_item, "add_separator"):  # re issue #361
                parent_ui_item.add_separator()
        except PyRevitException as err:
            mlogger.error("UI error: %s", err.msg)

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
            if hasattr(parent_ui_item, "get_rvtapi_object"):
                existing_items = parent_ui_item.get_rvtapi_object().GetItems()
                mlogger.debug(
                    "SLIDEOUT: Panel has %d items before adding slideout",
                    len(existing_items),
                )
                for idx, item in enumerate(existing_items):
                    mlogger.debug(
                        "SLIDEOUT: Existing item %d: %s (type: %s)",
                        idx,
                        getattr(item, "Name", "unknown"),
                        type(item).__name__,
                    )
        except Exception as log_err:
            mlogger.debug("SLIDEOUT: Could not log existing items: %s", log_err)

        mlogger.debug("SLIDEOUT: Adding slide out to: %s", parent_ui_item)
        try:
            parent_ui_item.add_slideout()
            mlogger.debug("SLIDEOUT: Slideout added successfully")
        except PyRevitException as err:
            mlogger.error("UI error: %s", err.msg)

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

    mlogger.debug("Producing smart button: %s", smartbutton)
    try:
        parent_ui_item.create_push_button(
            button_name=smartbutton.name,
            asm_location=ext_asm_info.location,
            class_name=_get_effective_classname(smartbutton),
            icon_path=smartbutton.icon_file or parent.icon_file,
            tooltip=_make_button_tooltip(smartbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(smartbutton, ext_asm_info.name),
            tooltip_media=smartbutton.media_file,
            ctxhelpurl=smartbutton.help_url,
            avail_class_name=smartbutton.avail_class_name,
            update_if_exists=True,
            ui_title=_make_ui_title(smartbutton),
        )
    except PyRevitException as err:
        mlogger.error("UI error: %s", err.msg)
        return None

    smartbutton_ui = parent_ui_item.button(smartbutton.name)

    mlogger.debug("Importing smart button as module: %s", smartbutton)
    try:
        # replacing EXEC_PARAMS.command_name value with button name so the
        # init script can log under its own name
        prev_commandname = (
            __builtins__["__commandname__"]
            if "__commandname__" in __builtins__
            else None
        )
        prev_commandpath = (
            __builtins__["__commandpath__"]
            if "__commandpath__" in __builtins__
            else None
        )
        prev_shiftclick = (
            __builtins__["__shiftclick__"]
            if "__shiftclick__" in __builtins__
            else False
        )
        prev_debugmode = (
            __builtins__["__forceddebugmode__"]
            if "__forceddebugmode__" in __builtins__
            else False
        )

        __builtins__["__commandname__"] = smartbutton.name
        __builtins__["__commandpath__"] = smartbutton.script_file
        __builtins__["__shiftclick__"] = False
        __builtins__["__forceddebugmode__"] = False
    except Exception as err:
        mlogger.error("Smart button setup error: %s | %s", smartbutton, err)
        return smartbutton_ui

    try:
        # setup sys.paths for the smart command
        current_paths = list(sys.path)
        for search_path in smartbutton.module_paths:
            if search_path not in current_paths:
                sys.path.append(search_path)

        # importing smart button script as a module
        importedscript = imp.load_source(
            smartbutton.unique_name, smartbutton.script_file
        )
        # resetting EXEC_PARAMS.command_name to original
        __builtins__["__commandname__"] = prev_commandname
        __builtins__["__commandpath__"] = prev_commandpath
        __builtins__["__shiftclick__"] = prev_shiftclick
        __builtins__["__forceddebugmode__"] = prev_debugmode
        mlogger.debug("Import successful: %s", importedscript)
        mlogger.debug("Running self initializer: %s", smartbutton)

        # reset sys.paths back to normal
        sys.path = current_paths

        res = False
        try:
            # running the smart button initializer function
            res = importedscript.__selfinit__(
                smartbutton, smartbutton_ui, HOST_APP.uiapp
            )
        except Exception as button_err:
            mlogger.error(
                "Error initializing smart button: %s | %s", smartbutton, button_err
            )

        # if the __selfinit__ function returns False
        # remove the button
        if res is False:
            mlogger.debug("SelfInit returned False on Smartbutton: %s", smartbutton_ui)
            smartbutton_ui.deactivate()

        mlogger.debug("SelfInit successful on Smartbutton: %s", smartbutton_ui)
    except Exception as err:
        mlogger.error("Smart button script import error: %s | %s", smartbutton, err)
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

    mlogger.debug("Producing button: %s", linkbutton)
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
            class_name=_make_full_class_name(linked_asm_name, linkbutton.command_class),
            icon_path=linkbutton.icon_file or parent.icon_file,
            tooltip=_make_button_tooltip(linkbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(linkbutton, ext_asm_info.name),
            tooltip_media=linkbutton.media_file,
            ctxhelpurl=linkbutton.help_url,
            avail_class_name=_make_full_class_name(
                linked_asm_name, linkbutton.avail_command_class
            ),
            update_if_exists=True,
            ui_title=_make_ui_title(linkbutton),
        )
        linkbutton_ui = parent_ui_item.button(linkbutton.name)

        _set_highlights(linkbutton, linkbutton_ui)

        return linkbutton_ui
    except PyRevitException as err:
        mlogger.error("UI error: %s", err.msg)
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

    mlogger.debug("Producing button: %s", pushbutton)
    try:
        parent_ui_item.create_push_button(
            button_name=pushbutton.name,
            asm_location=ext_asm_info.location,
            class_name=_get_effective_classname(pushbutton),
            icon_path=pushbutton.icon_file or parent.icon_file,
            tooltip=_make_button_tooltip(pushbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(pushbutton, ext_asm_info.name),
            tooltip_media=pushbutton.media_file,
            ctxhelpurl=pushbutton.help_url,
            avail_class_name=pushbutton.avail_class_name,
            update_if_exists=True,
            ui_title=_make_ui_title(pushbutton),
        )
        pushbutton_ui = parent_ui_item.button(pushbutton.name)

        _set_highlights(pushbutton, pushbutton_ui)

        return pushbutton_ui
    except PyRevitException as err:
        mlogger.error("UI error: %s", err.msg)
        return None


def _produce_ui_pulldown(ui_maker_params):
    """Create a pulldown button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    pulldown = ui_maker_params.component

    mlogger.debug("Producing pulldown button: %s", pulldown)
    try:
        parent_ribbon_panel.create_pulldown_button(
            pulldown.ui_title, pulldown.icon_file, update_if_exists=True
        )
        pulldown_ui = parent_ribbon_panel.ribbon_item(pulldown.ui_title)

        _set_highlights(pulldown, pulldown_ui)

        return pulldown_ui
    except PyRevitException as err:
        mlogger.error("UI error: %s", err.msg)
        return None


def _setup_combobox_objects(ui_maker_params):
    """Setup and validate combobox objects.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.

    Returns:
        tuple: (combobox_ui, combobox_obj) if successful, None otherwise.
        If ComboBox is in data mode, returns (combobox_ui, None).
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    combobox = ui_maker_params.component
    combobox_name = getattr(combobox, "name", "unknown")

    # Validate inputs first
    if not combobox:
        mlogger.error("Component is None")
        return None
    if not parent_ribbon_panel:
        mlogger.error("Parent UI is None for: %s", combobox_name)
        return None

    # Get panel API object
    try:
        panel_rvtapi = parent_ribbon_panel.get_rvtapi_object()
        if not panel_rvtapi:
            mlogger.error("Panel Revit API object is None for: %s", combobox_name)
            return None
    except Exception as panel_err:
        mlogger.error("Could not get panel Revit API object: %s", panel_err)
        return None

    # Create combobox
    try:
        parent_ribbon_panel.create_combobox(combobox_name, update_if_exists=True)
    except Exception as create_err:
        mlogger.exception("Error calling create_combobox: %s", create_err)
        return None

    combobox_ui = parent_ribbon_panel.ribbon_item(combobox_name)
    if not combobox_ui:
        mlogger.error("Failed to get ComboBox UI item: %s", combobox_name)
        return None

    # Get the Revit API ComboBox object
    try:
        combobox_obj = combobox_ui.get_rvtapi_object()
    except Exception as rvtapi_err:
        mlogger.error(
            "get_rvtapi_object() failed for %s: %s", combobox_name, rvtapi_err
        )
        return None

    if not combobox_obj:
        mlogger.error("get_rvtapi_object() returned None for: %s", combobox_name)
        return None

    # Return early if ComboBox is still in data mode (not yet added to panel)
    if isinstance(combobox_obj, UI.ComboBoxData):
        return (combobox_ui, None)

    return (combobox_ui, combobox_obj)


def _add_combobox_members(combobox_ui, combobox):
    """Add members to a ComboBox from metadata.

    Args:
        combobox_ui: The ComboBox UI object to add members to
        combobox: The combobox component with members metadata
    """
    if not hasattr(combobox, "members") or not combobox.members:
        return

    for member in combobox.members:
        member_id = None
        member_text = None
        member_icon = None
        member_group = None
        member_tooltip = None
        member_tooltip_ext = None
        member_tooltip_image = None

        if isinstance(member, (list, tuple)) and len(member) >= 2:
            member_id, member_text = member[0], member[1]
        elif isinstance(member, dict) or (
            hasattr(member, "get") and hasattr(member, "keys")
        ):
            member_id = member.get("id", member.get("name", ""))
            member_text = member.get("text", member.get("title", member_id))
            member_icon = member.get("icon", None)
            member_group = member.get("group", member.get("groupName", None))
            member_tooltip = member.get("tooltip", None)
            member_tooltip_ext = member.get(
                "tooltip_ext", member.get("longDescription", None)
            )
            member_tooltip_image = member.get(
                "tooltip_image", member.get("tooltipImage", None)
            )
        elif isinstance(member, str):
            member_id = member_text = member
        else:
            mlogger.warning(
                "Skipping invalid member format: %s (type: %s)",
                member,
                type(member),
            )
            continue

        if not member_id or not member_text:
            mlogger.warning("Skipping member with missing id or text")
            continue

        # Create member data (minimal - just id and text)
        member_data = UI.ComboBoxMemberData(member_id, member_text)

        # Add member to ComboBox first (returns ComboBoxMember object)
        try:
            member_obj = combobox_ui.add_item(member_data)
            if not member_obj:
                mlogger.warning("AddItem returned None for: %s", member_text)
                continue

            # Now set properties on the actual ComboBoxMember object (not the data)

            # Set member icon if available
            if member_icon:
                try:
                    # Resolve icon path (relative to bundle directory or absolute)
                    if combobox.directory and not op.isabs(member_icon):
                        icon_path = op.join(combobox.directory, member_icon)
                    else:
                        icon_path = member_icon

                    if op.exists(icon_path):
                        button_icon = ribbon.ButtonIcons(icon_path)
                        member_obj.Image = button_icon.small_bitmap
                    else:
                        mlogger.warning("Icon file not found: %s", icon_path)
                except Exception as member_icon_err:
                    mlogger.debug(
                        "Error setting member icon: %s", member_icon_err
                    )

            # Set member group if available
            if member_group and hasattr(member_obj, "GroupName"):
                try:
                    member_obj.GroupName = member_group
                except Exception as group_err:
                    mlogger.debug("Error setting member group: %s", group_err)

            # Set member tooltip if available
            if member_tooltip and hasattr(member_obj, "ToolTip"):
                try:
                    member_obj.ToolTip = member_tooltip
                except Exception as tooltip_err:
                    mlogger.debug(
                        "Error setting member tooltip: %s", tooltip_err
                    )

            # Set member extended tooltip if available
            if member_tooltip_ext and hasattr(member_obj, "LongDescription"):
                try:
                    member_obj.LongDescription = member_tooltip_ext
                except Exception as tooltip_ext_err:
                    mlogger.debug(
                        "Error setting member extended tooltip: %s",
                        tooltip_ext_err,
                    )

            # Set member tooltip image if available
            if member_tooltip_image and hasattr(member_obj, "ToolTipImage"):
                try:
                    # Resolve tooltip image path (relative to bundle directory or absolute)
                    if combobox.directory and not op.isabs(
                        member_tooltip_image
                    ):
                        tooltip_image_path = op.join(
                            combobox.directory, member_tooltip_image
                        )
                    else:
                        tooltip_image_path = member_tooltip_image

                    if op.exists(tooltip_image_path):
                        from pyrevit.coreutils.ribbon import load_bitmapimage

                        tooltip_bitmap = load_bitmapimage(tooltip_image_path)
                        member_obj.ToolTipImage = tooltip_bitmap
                except Exception as tooltip_image_err:
                    mlogger.debug(
                        "Error setting member tooltip image: %s",
                        tooltip_image_err,
                    )

        except Exception as add_err:
            mlogger.warning("Error adding member: %s", add_err)


def _produce_ui_combobox(ui_maker_params):
    """Create a ComboBox with full property support.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    # Setup and get combobox objects
    setup_result = _setup_combobox_objects(ui_maker_params)
    if setup_result is None:
        return None

    combobox_ui, combobox_obj = setup_result

    # If in data mode, return early
    if combobox_obj is None:
        return combobox_ui

    combobox = ui_maker_params.component
    combobox_name = getattr(combobox, "name", "unknown")

    # From here on we have a real Autodesk.Revit.UI.ComboBox

    # Set ItemText/Title
    # Note: In Revit, ComboBox.ItemText displays the current selected item's text in the dropdown
    # There is no separate visible "title" label for ComboBoxes like buttons have
    # The title from bundle.yaml is used for tooltip and identification
    # We'll set ItemText to the title initially, but it will be overwritten when current item is set
    combobox_title = getattr(combobox, "ui_title", None) or combobox_name
    if not combobox_ui.current and combobox_title:
        try:
            # Set initial ItemText to title (will be overwritten when current item is set)
            combobox_obj.ItemText = combobox_title
        except Exception as title_err:
            mlogger.debug("Could not set ItemText: %s", title_err)

    # Set icon if available
    parent = ui_maker_params.parent_cmp
    icon_file = getattr(combobox, "icon_file", None) or getattr(
        parent, "icon_file", None
    )
    if icon_file:
        try:
            combobox_ui.set_icon(icon_file, icon_size=ICON_MEDIUM)
        except Exception as icon_err:
            mlogger.debug("Error setting icon: %s", icon_err)

    # Set tooltip if available
    tooltip = getattr(combobox, "tooltip", None)
    if tooltip:
        try:
            combobox_ui.set_tooltip(tooltip)
        except Exception as tooltip_err:
            mlogger.debug("Error setting tooltip: %s", tooltip_err)

    # Set extended tooltip if available
    tooltip_ext = getattr(combobox, "tooltip_ext", None)
    if tooltip_ext:
        try:
            combobox_ui.set_tooltip_ext(tooltip_ext)
        except Exception as tooltip_ext_err:
            mlogger.debug("Error setting extended tooltip: %s", tooltip_ext_err)

    # Set tooltip media (image/video) if available
    tooltip_media = getattr(combobox, "media_file", None)
    if tooltip_media:
        try:
            combobox_ui.set_tooltip_media(tooltip_media)
        except Exception as tooltip_media_err:
            mlogger.debug("Error setting tooltip media: %s", tooltip_media_err)

    # Set contextual help if available
    help_url = getattr(combobox, "help_url", None)
    if help_url:
        try:
            combobox_ui.set_contexthelp(help_url)
        except Exception as help_err:
            mlogger.debug("Error setting contextual help: %s", help_err)

    # Add members from metadata
    _add_combobox_members(combobox_ui, combobox)

    # Set Current to first item
    # Note: Setting current will overwrite ItemText with the selected item's text
    # This is expected behavior - ComboBox.ItemText shows the current selection
    items = combobox_ui.get_items()
    if items and len(items) > 0:
        try:
            combobox_ui.current = items[0]
        except Exception as current_err:
            mlogger.debug("Error setting current item: %s", current_err)

    # Call __selfinit__ on script (SmartButton pattern)
    try:
        combobox_script_file = getattr(combobox, "script_file", None)
        combobox_unique_name = getattr(combobox, "unique_name", None)

        if (
            not combobox_script_file
            and hasattr(combobox, "directory")
            and combobox.directory
        ):
            script_path = op.join(combobox.directory, "script.py")
            if op.exists(script_path):
                combobox_script_file = script_path

        if combobox_script_file and combobox_unique_name:
            current_paths = list(sys.path)
            combobox_module_paths = getattr(combobox, "module_paths", [])
            for search_path in combobox_module_paths:
                if search_path not in current_paths:
                    sys.path.append(search_path)

            imported_script = imp.load_source(
                combobox_unique_name, combobox_script_file
            )
            sys.path = current_paths

            if hasattr(imported_script, "__selfinit__"):
                mlogger.warning(
                    "[ComboBox Script Load] '%s': Calling __selfinit__ function",
                    combobox_name,
                )
                res = imported_script.__selfinit__(
                    combobox, combobox_ui, HOST_APP.uiapp
                )
                if res is False:
                    combobox_ui.deactivate()
            else:
                mlogger.warning(
                    "[ComboBox Script Load] '%s': Script loaded but __selfinit__ function not found",
                    combobox_name,
                )
        else:
            mlogger.warning(
                "[ComboBox Script Load] '%s': Skipping script load - script_file=%s, unique_name=%s",
                combobox_name,
                combobox_script_file,
                combobox_unique_name,
            )
    except Exception as init_err:
        mlogger.exception("Error in __selfinit__: %s", init_err)

    # Ensure visible & enabled
    try:
        if hasattr(combobox_obj, "Visible"):
            combobox_obj.Visible = True
        if hasattr(combobox_obj, "Enabled"):
            combobox_obj.Enabled = True
    except Exception as vis_err:
        mlogger.debug("Could not set visibility: %s", vis_err)

    # Activate UI item
    try:
        combobox_ui.activate()
    except Exception as activate_err:
        mlogger.debug("Could not activate: %s", activate_err)

    return combobox_ui


def _produce_ui_split(ui_maker_params):
    """Produce a split button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    split = ui_maker_params.component

    mlogger.debug("Producing split button: %s}", split)
    try:
        parent_ribbon_panel.create_split_button(
            split.ui_title, split.icon_file, update_if_exists=True
        )
        split_ui = parent_ribbon_panel.ribbon_item(split.ui_title)

        _set_highlights(split, split_ui)

        return split_ui
    except PyRevitException as err:
        mlogger.error("UI error: %s", err.msg)
        return None


def _produce_ui_splitpush(ui_maker_params):
    """Create split push button.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ribbon_panel = ui_maker_params.parent_ui
    splitpush = ui_maker_params.component

    mlogger.debug("Producing splitpush button: %s", splitpush)
    try:
        parent_ribbon_panel.create_splitpush_button(
            splitpush.ui_title, splitpush.icon_file, update_if_exists=True
        )
        splitpush_ui = parent_ribbon_panel.ribbon_item(splitpush.ui_title)

        _set_highlights(splitpush, splitpush_ui)

        return splitpush_ui
    except PyRevitException as err:
        mlogger.error("UI error: %s", err.msg)
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
        mlogger.debug("Opened stack: %s", stack_cmp.name)

        if HOST_APP.is_older_than("2017"):
            _component_creation_dict[exts.SPLIT_BUTTON_POSTFIX] = _produce_ui_pulldown
            _component_creation_dict[exts.SPLITPUSH_BUTTON_POSTFIX] = (
                _produce_ui_pulldown
            )

        # capturing and logging any errors on stack item
        # (e.g when parent_ui_panel's stack is full and can not add any
        # more items it will raise an error)
        _recursively_produce_ui_items(
            UIMakerParams(
                parent_ui_panel,
                stack_parent,
                stack_cmp,
                ext_asm_info,
                ui_maker_params.create_beta_cmds,
            )
        )

        if HOST_APP.is_older_than("2017"):
            _component_creation_dict[exts.SPLIT_BUTTON_POSTFIX] = _produce_ui_split
            _component_creation_dict[exts.SPLITPUSH_BUTTON_POSTFIX] = (
                _produce_ui_splitpush
            )

        try:
            parent_ui_panel.close_stack()
            mlogger.debug("Closed stack: %s", stack_cmp.name)
            for component in stack_cmp:
                if hasattr(component, 'highlight_type') and component.highlight_type:
                    # Get the UI item for this component
                    ui_item = parent_ui_panel.button(component.name)
                    if ui_item:
                        _set_highlights(component, ui_item)
            mlogger.debug("Set highlights on stack: %s", stack_cmp.name)
            return stack_cmp
        except PyRevitException as err:
            mlogger.error("Error creating stack | %s", err)

    except Exception as err:
        mlogger.error(
            "Can not create stack under this parent: %s | %s", parent_ui_panel, err
        )


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

    mlogger.debug("Producing panel button: %s", panelpushbutton)
    try:
        parent_ui_item.create_panel_push_button(
            button_name=panelpushbutton.name,
            asm_location=ext_asm_info.location,
            class_name=_get_effective_classname(panelpushbutton),
            tooltip=_make_button_tooltip(panelpushbutton),
            tooltip_ext=_make_tooltip_ext_if_requested(
                panelpushbutton, ext_asm_info.name
            ),
            tooltip_media=panelpushbutton.media_file,
            ctxhelpurl=panelpushbutton.help_url,
            avail_class_name=panelpushbutton.avail_class_name,
            update_if_exists=True,
            ui_title=_make_ui_title(panelpushbutton),
        )

        panelpushbutton_ui = parent_ui_item.button(panelpushbutton.name)

        _set_highlights(panelpushbutton, panelpushbutton_ui)

        return panelpushbutton_ui
    except PyRevitException as err:
        mlogger.error("UI error: %s", err.msg)
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

    mlogger.debug("Producing ribbon panel: %s", panel)
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
        mlogger.error("UI error: %s", err.msg)
        return None


def _produce_ui_tab(ui_maker_params):
    """Create a tab with the given parameters.

    Args:
        ui_maker_params (UIMakerParams): Standard parameters for making ui item.
    """
    parent_ui = ui_maker_params.parent_ui
    tab = ui_maker_params.component

    mlogger.debug("Verifying tab: %s", tab)
    if tab.has_commands():
        mlogger.debug("Tabs has command: %s", tab)
        mlogger.debug("Producing ribbon tab: %s", tab)
        try:
            parent_ui.create_ribbon_tab(tab.name, update_if_exists=True)
            tab_ui = parent_ui.ribbon_tab(tab.name)

            _set_highlights(tab, tab_ui)

            return tab_ui
        except PyRevitException as err:
            # If tab is native, log as warning instead of error
            if "native item" in err.msg.lower():
                mlogger.warning("UI warning (tab may be native): %s", err.msg)
            else:
                mlogger.error("UI error: %s", err.msg)
                return None
    else:
        mlogger.debug("Tab does not have any commands. Skipping: %s", tab.name)
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
            parent_name = getattr(ui_maker_params.parent_ui, "name", None)
            if not parent_name:
                try:
                    parent_name = str(type(ui_maker_params.parent_ui))
                except Exception:
                    parent_name = "unknown"
            mlogger.debug(
                "BUILDING COMPONENT: %s parent: %s", sub_cmp.name, parent_name
            )

            mlogger.debug(
                "Calling create func %s for: %s",
                _component_creation_dict[sub_cmp.type_id],
                sub_cmp,
            )
            ui_item = _component_creation_dict[sub_cmp.type_id](
                UIMakerParams(
                    ui_maker_params.parent_ui,
                    ui_maker_params.component,
                    sub_cmp,
                    ui_maker_params.asm_info,
                    ui_maker_params.create_beta_cmds,
                )
            )
            if ui_item:
                cmp_count += 1
        except KeyError:
            mlogger.warning(
                "Can not find create function for type_id: %s (component: %s)",
                sub_cmp.type_id,
                sub_cmp,
            )
        except Exception as create_err:
            mlogger.critical("Error creating item: %s | %s", sub_cmp, create_err)

        mlogger.debug("UI item created by create func is: %s", ui_item)
        # if component does not have any sub components hide it
        # Exclude GenericStack and ComboBoxGroup from deactivation check
        # (GenericStack is a special container, ComboBoxGroup has members not child components)
        if (
            ui_item
            and not isinstance(ui_item, components.GenericStack)
            and not isinstance(sub_cmp, components.ComboBoxGroup)
            and sub_cmp.is_container
        ):
            subcmp_count = _recursively_produce_ui_items(
                UIMakerParams(
                    ui_item,
                    ui_maker_params.component,
                    sub_cmp,
                    ui_maker_params.asm_info,
                    ui_maker_params.create_beta_cmds,
                )
            )

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
    mlogger.debug("Creating/Updating ui for extension: %s", ui_ext)
    cmp_count = _recursively_produce_ui_items(
        UIMakerParams(current_ui, None, ui_ext, ext_asm_info, create_beta)
    )
    mlogger.debug("%s components were created for: %s", cmp_count, ui_ext)


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
                if litem.directive.directive_type == "before":
                    tab.reorder_before(litem.name, litem.directive.target)
                elif litem.directive.directive_type == "after":
                    tab.reorder_after(litem.name, litem.directive.target)
                elif litem.directive.directive_type == "afterall":
                    tab.reorder_afterall(litem.name)
                elif litem.directive.directive_type == "beforeall":
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
                mlogger.debug("Deactivating: %s", item)
                item.deactivate()
            except Exception as deact_err:
                # Log as debug to avoid cluttering output with expected errors
                mlogger.debug(
                    "Could not deactivate item (may be native): %s | %s",
                    item,
                    deact_err,
                )


def reflow_pyrevit_ui(direction=applocales.DEFAULT_LANG_DIR):
    """Set the flow direction of the tabs."""
    if direction == "LTR":
        current_ui.set_LTR_flow()
    elif direction == "RTL":
        current_ui.set_RTL_flow()
