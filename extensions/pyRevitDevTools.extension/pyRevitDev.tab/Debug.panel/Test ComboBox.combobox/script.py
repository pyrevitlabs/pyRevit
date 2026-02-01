"""Test ComboBox - Demonstrates ALL pyRevit ComboBox wrapper features.

This script serves as a comprehensive reference for:
- All three ComboBox events (CurrentChanged, DropDownOpened, DropDownClosed)
- Dynamic member addition (add_item, add_items, add_separator)
- Querying items (get_items, current property)
- UI manipulation (enabled, visible, activate, deactivate)
- Tooltip and contextual help APIs
"""
#pylint: disable=C0103,E0401
from Autodesk.Revit.UI import ComboBoxMemberData, TaskDialog

__context__ = 'zero-doc'


def __selfinit__(component, ui_item, uiapp):
    """Initialize the ComboBox after UI creation.

    Args:
        component: The ComboBoxGroup component object (bundle metadata)
        ui_item: The _PyRevitRibbonComboBox wrapper instance
        uiapp: The Revit UIApplication object

    Returns:
        bool: True to keep active, False to deactivate
    """
    try:
        # Get the underlying Revit API ComboBox object
        cmb = ui_item.get_rvtapi_object()
        if not cmb:
            return False

        # =====================================================================
        # DYNAMIC MEMBER ADDITION
        # =====================================================================

        # Add a separator before dynamic items
        ui_item.add_separator()

        # Add single item using add_item()
        dynamic_member = ComboBoxMemberData("dynamic_single", "Dynamic Single")
        dynamic_member.GroupName = "Dynamic Items"
        ui_item.add_item(dynamic_member)

        # Add multiple items at once using add_items()
        batch_members = [
            ComboBoxMemberData("dynamic_batch_1", "Dynamic Batch 1"),
            ComboBoxMemberData("dynamic_batch_2", "Dynamic Batch 2"),
        ]
        for m in batch_members:
            m.GroupName = "Dynamic Items"
        ui_item.add_items(batch_members)

        # =====================================================================
        # QUERY ITEMS
        # =====================================================================

        # Get all items currently in the ComboBox
        all_items = ui_item.get_items()

        # =====================================================================
        # CURRENT SELECTION
        # =====================================================================

        # Get current selection
        current = ui_item.current
        if current:
            pass

        # Set current selection to first item (if exists)
        if all_items:
            ui_item.current = all_items[0]
            pass

        # =====================================================================
        # UI PROPERTIES (via wrapper)
        # =====================================================================

        # Title manipulation
        original_title = ui_item.get_title()
        # ui_item.set_title("Modified Title")  # Uncomment to test

        # Enabled/Visible properties (inherited from GenericPyRevitUIContainer)
        TaskDialog.Show(
            "Enabled: {}\nVisible: {}".format(ui_item.enabled, ui_item.visible)
        )

        # These can be set:
        # ui_item.enabled = False  # Disable the ComboBox
        # ui_item.visible = False  # Hide the ComboBox
        # ui_item.activate()       # Enable and show
        # ui_item.deactivate()     # Disable and hide

        # =====================================================================
        # CONTEXTUAL HELP
        # =====================================================================

        # Check current contextual help
        ctx_help = ui_item.get_contexthelp()
        if ctx_help:
            TaskDialog.Show(
                "Test ComboBox",
                "Contextual help type: {}".format(ctx_help.HelpType)
            )

        # Can also set programmatically:
        # ui_item.set_contexthelp("https://example.com/help")

        # =====================================================================
        # EVENT HANDLERS
        # =====================================================================

        def on_current_changed(sender, args):
            """Fired when user selects a different item."""
            current = sender.Current
            if current:
                TaskDialog.Show(
                    "ComboBox Selection Changed",
                    "Selected: {}\nID: {}".format(current.ItemText, current.Name)
                )

        def on_dropdown_opened(sender, args):
            """Fired when dropdown is opened (before items shown).

            Note: Avoid TaskDialog here - it blocks dropdown expansion.
            This event is useful for refreshing items or updating state,
            but not for showing UI feedback.
            """
            # Example: could refresh dynamic items here
            # items = sender.GetItems()
            pass

        def on_dropdown_closed(sender, args):
            """Fired when dropdown is closed."""
            current = sender.Current
            TaskDialog.Show(
                "ComboBox Dropdown Closed",
                "Current selection: {}".format(
                    current.ItemText if current else "None"
                )
            )

        # Subscribe to all three events
        cmb.CurrentChanged += on_current_changed
        cmb.DropDownOpened += on_dropdown_opened
        cmb.DropDownClosed += on_dropdown_closed

        # IMPORTANT: Keep references to prevent garbage collection
        ui_item._on_current_changed = on_current_changed
        ui_item._on_dropdown_opened = on_dropdown_opened
        ui_item._on_dropdown_closed = on_dropdown_closed

        return True

    except Exception as e:
        return False
