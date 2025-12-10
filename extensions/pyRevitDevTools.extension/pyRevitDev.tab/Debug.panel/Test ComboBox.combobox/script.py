"""Test ComboBox"""
#pylint: disable=C0103,E0401
from Autodesk.Revit.UI import TaskDialog

__context__ = 'zero-doc'


def __selfinit__(component, ui_item, uiapp):
    """Deferred initializer - called AFTER the UI and metadata are ready."""
    try:
        cmb = ui_item.get_rvtapi_object()
        if not cmb:
            return False

        def on_changed(sender, args):
            """Handle ComboBox selection change."""
            try:
                current = sender.Current
                if current:
                    selected_text = current.ItemText
                    TaskDialog.Show("Test ComboBox", "Selection changed!\n\nSelected: {}".format(selected_text))
            except Exception as e:
                TaskDialog.Show("Test ComboBox Error", "Error: {}".format(str(e)))

        def on_dropdown_closed(sender, args):
            """Handle ComboBox dropdown closed event."""
            TaskDialog.Show("Test ComboBox", "Dropdown closed")

        # Hook events
        cmb.CurrentChanged += on_changed
        
        if hasattr(cmb, 'DropDownClosed'):
            cmb.DropDownClosed += on_dropdown_closed

        # Keep references alive to prevent garbage collection
        ui_item._current_changed_handler = on_changed
        ui_item._dropdown_closed_handler = on_dropdown_closed

        return True

    except Exception as e:
        TaskDialog.Show("Test ComboBox Error", "Init failed: {}".format(str(e)))
        return False
