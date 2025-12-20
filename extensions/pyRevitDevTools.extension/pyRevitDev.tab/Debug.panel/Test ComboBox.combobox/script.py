"""Test ComboBox - Pattern Demo

This script demonstrates the new simplified ComboBox event handler pattern.
Instead of defining __selfinit__, you can define global event handlers:
    - __cmb_on_change__(sender, args, ctx)
    - __cmb_dropdown_close__(sender, args, ctx)
    - __cmb_dropdown_open__(sender, args, ctx)

The `ctx` parameter is a ComboBoxContext object that provides:
    - ctx.current_value: The text of the currently selected item
    - ctx.current_name: The name/id of the currently selected item
    - ctx.current_item: The ComboBoxMemberData object
    - ctx.items: List of all items
    - ctx.item_texts: List of all item texts
    - ctx.item_names: List of all item names
    - ctx.item_count: Number of items
    - ctx.combobox: The raw Revit ComboBox API object
    - ctx.component: The parsed component metadata
    - ctx.uiapp: The Revit UIApplication
    - ctx.user_data: A dict for storing custom data between events
    - ctx.set_current(name_or_text): Set current selection
    - ctx.get_item_by_name(name): Find item by name
    - ctx.get_item_by_text(text): Find item by text
"""
#pylint: disable=C0103,E0401
from Autodesk.Revit.UI import TaskDialog

__context__ = 'zero-doc'


def __cmb_on_change__(sender, args, ctx):
    """Handle ComboBox selection change.
    
    Args:
        sender: The Revit ComboBox control
        args: Event arguments from Revit API
        ctx: ComboBoxContext with current state and helper methods
    """
    TaskDialog.Show(
        "Test ComboBox", 
        "Selection changed!\n\nSelected: {}\nTotal items: {}".format(
            ctx.current_value, 
            ctx.item_count
        )
    )


def __cmb_dropdown_close__(sender, args, ctx):
    """Handle ComboBox dropdown closed event.
    
    Args:
        sender: The Revit ComboBox control
        args: Event arguments from Revit API  
        ctx: ComboBoxContext with current state and helper methods
    """
    TaskDialog.Show(
        "Test ComboBox", 
        "Dropdown closed\n\nFinal selection: {}".format(ctx.current_value)
    )
