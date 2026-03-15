"""Test ComboBox - Demonstrates pyRevit ComboBox wrapper features.

This script serves as a reference for:
- All three ComboBox events (CurrentChanged, DropDownOpened, DropDownClosed)
- Dynamic member addition (add_item, add_items, add_separator)
- Querying items (get_items, current property)
- UI manipulation (enabled, visible, activate, deactivate)
- Tooltip and contextual help APIs

Note: This ComboBox is driven only by event handler functions.
"""
#pylint: disable=C0103,E0401
from Autodesk.Revit.UI import TaskDialog

__context__ = 'zero-doc'


def _ensure_dynamic_items(ctx):
    if ctx.user_data.ContainsKey('dynamic_items_added') and ctx.user_data['dynamic_items_added']:
        return

    ui_item = ctx.ui_item
    if not ui_item:
        return

    ui_item.add_separator()

    ui_item.AddItem("dynamic_single", "Dynamic Single", "Dynamic Items")

    batch_members = [
        ("dynamic_batch_1", "Dynamic Batch 1"),
        ("dynamic_batch_2", "Dynamic Batch 2"),
    ]
    ui_item.add_items(batch_members, "Dynamic Items")

    all_items = ui_item.get_items()
    if all_items and not ctx.current_item:
        ui_item.current = all_items[0]

    ctx.user_data['dynamic_items_added'] = True


def _show_ui_info_once(ctx):
    if ctx.user_data.ContainsKey('ui_info_shown') and ctx.user_data['ui_info_shown']:
        return

    ui_item = ctx.ui_item
    if not ui_item:
        return

    ctx_help = ui_item.get_contexthelp()
    ctx_help_type = ctx_help.HelpType if ctx_help else "None"

    TaskDialog.Show(
        "Test ComboBox",
        "Enabled: {}\nVisible: {}\nContextual help: {}".format(
            ui_item.enabled,
            ui_item.visible,
            ctx_help_type
        )
    )

    ctx.user_data['ui_info_shown'] = True


def __cmb_on_change__(sender, args, ctx):
    """Fired when user selects a different item."""
    _show_ui_info_once(ctx)

    print("ComboBox Selection Changed - Current selection: {}".format(sender.Current.ItemText if sender.Current else "None"))
    current = sender.Current
    if current:
        TaskDialog.Show(
            "ComboBox Selection Changed",
            "Selected: {}\nID: {}".format(current.ItemText, current.Name)
        )


def __cmb_dropdown_open__(sender, args, ctx):
    """Fired when dropdown is opened (before items shown).

    Note: Avoid TaskDialog here - it blocks dropdown expansion.
    """
    print("ComboBox Dropdown Opened - Adding dynamic items...")
    _ensure_dynamic_items(ctx)



def __cmb_dropdown_close__(sender, args, ctx):
    """Fired when dropdown is closed."""
    current = sender.Current
    print("ComboBox Dropdown Closed - Current selection: {}".format(current.ItemText if current else "None"))
    TaskDialog.Show(
        "ComboBox Dropdown Closed",
        "Current selection: {}".format(
            current.ItemText if current else "None"
        )
    )
