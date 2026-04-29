"""Example: Using execute_in_revit_context for modeless dialogs.

This example demonstrates the difference between calling Revit API directly
vs using execute_in_revit_context() from modeless WPF windows.
"""

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit.revit.events import execute_in_revit_context
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()


def update_element_comment(element, comment_text):
    """Update the Comments parameter of an element."""
    with revit.Transaction("Update Comment"):
        param = element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if param and not param.IsReadOnly:
            param.Set(comment_text)
            forms.alert("Successfully updated comment!")
        else:
            forms.alert("Element has no writable Comments parameter.")
            return False


class ExampleUI(forms.WPFWindow):
    """Example modeless window showing execute_in_revit_context usage."""

    def __init__(self):
        xaml_layout = """
        <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Title="Execute in Revit Context Example"
                Width="400" Height="340"
                WindowStartupLocation="CenterScreen"
                ShowInTaskbar="False"
                ResizeMode="CanMinimize">
            <StackPanel Margin="20">
                <TextBlock Text="Pick an element, then click a button:"
                           Margin="0,0,0,10"/>

                <CheckBox Name="chk_context"
                        Content="Run pick in external event content"/>

                <Button Name="pick_button"
                        Content="1. Pick Element"
                        Height="30"
                        Margin="0,5"
                        Click="pick_element_clicked"/>

                <TextBlock Name="element_info"
                           Text="No element selected"
                           Margin="0,10"
                           FontStyle="Italic"/>

                <TextBlock Text="Text for comments field of select element:"
                           Margin="0,0,0,5"/>

                <TextBox Name="comment_input"
                         Height="25"
                         Margin="0,10,0,5"
                         Text="Updated from modeless dialog"/>

                <Button Name="update_wrong_button"
                        Content="2a. Update (WRONG - Will Crash)"
                        Height="30"
                        Margin="0,5"
                        Background="#FFCCCC"
                        Click="update_wrong_clicked"/>

                <Button Name="update_correct_button"
                        Content="2b. Update (CORRECT - With Context)"
                        Height="30"
                        Margin="0,5"
                        Background="#CCFFCC"
                        Click="update_correct_clicked"/>
            </StackPanel>
        </Window>
        """

        forms.WPFWindow.__init__(self, xaml_layout, literal_string=True)
        self.selected_element = None

    def pick_element_clicked(self, sender, args):
        """Button handler: Pick an element (needs Revit context)."""
        # Picking does not require Revit context, so we can use it standalone.
        # It makes no difference if we use execute_in_revit_context.
        if not self.chk_context.IsChecked:
            self._do_pick_element("Without External Event Context")
        else:
            execute_in_revit_context(self._do_pick_element, "With External Event Content")

    def _do_pick_element(self, message):
        """Actually pick the element (runs in Revit context)."""
        try:
            # This needs to run in Revit context
            element = revit.pick_element(message=message)
            if element:
                self.selected_element = element
                self._update_element_info(element)
        except Exception as ex:
            print(ex)
            self.dispatch(forms.alert, "Error picking element: {}".format(ex))

    def _update_element_info(self, element):
        """Update the UI with element info."""
        element_type = element.GetType().Name
        element_id = get_elementid_value(element.Id)
        info_text = "Selected: {} (ID: {})".format(element_type, element_id)
        self.element_info.Text = info_text

    def update_wrong_clicked(self, sender, args):
        """WRONG: Direct API call from modeless window - will crash!"""
        if not self.selected_element:
            forms.alert("Please pick an element first.")
            return

        # WARNING: This will throw InvalidOperationException!
        # You cannot modify Revit database from a modeless window thread
        try:
            comment = self.comment_input.Text
            update_element_comment(self.selected_element, comment)
        except Exception as ex:
            forms.alert(
                "ERROR (Expected):\n\n{}\n\n"
                "This is why you need execute_in_revit_context!".format(ex)
            )

    def update_correct_clicked(self, sender, args):
        """CORRECT: Use execute_in_revit_context for API calls."""
        if not self.selected_element:
            forms.alert("Please pick an element first.")
            return

        # This is the correct way - wrap the API call
        comment = self.comment_input.Text
        execute_in_revit_context(update_element_comment, self.selected_element, comment)

        # Alternatively wrap the call in a lambda so it executes later,
        # inside Revit's API context.
        # execute_in_revit_context(
        #     lambda: update_element_comment(self.selected_element, comment)
        # )


if __name__ == "__main__":
    ui = ExampleUI()
    ui.show(modal=False)  # Non-modal is key - makes it a modeless dialog
