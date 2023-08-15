"""Testing non-modal windows calling actions thru external events.

Shift-Click:
Run window as Modal
"""
# pylint: skip-file
from pyrevit import HOST_APP, framework, EXEC_PARAMS
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit.runtime import types as runtime_types
from pyrevit import script


__context__ = 'zero-doc'
__title__ = "Test Persistent Engine (NonModal)"
__author__ = "{{author}}"
__persistentengine__ = True

logger = script.get_logger()


# Note on Events in Non-Modal Windows:
# with non-modal windows, Revit API call to command execute returns after
# creating the window, and thus, while window is running, Revit is NOT in
# API context and all the api calls needs be handled through external events.
# The event subscription (+=) happens on the API context inside the window
# __init__ method while window is being created, but
# the unsibscribe needs to happen on API context and thus an event handler
# is necessary. The event handler needs to hold a reference to window so
# it can unsibscribe the subscribed events


class NonModalWindow(forms.WPFWindow):
    def __init__(self, ext_event_handler):
        self.ext_event_handler = ext_event_handler
        self.ext_event = \
            UI.ExternalEvent.Create(self.ext_event_handler)
        self.prev_title = "Title Changed..."

    def setup(self):
        self.update_ui()

    @revit.events.handle('doc-changed', 'doc-closed', 'doc-opened', 'view-activated')
    def uiupdator_eventhandler(sender, args):
        # the decorator captures the function from the class and not from the
        # instance. so the capture function is not bound thus no 'self'
        # ui however is inside the context and still accessible
        ui.update_ui()

    def action(self, sender, args):
        if __shiftclick__:
            self.Close()

        self.ext_event_handler.KeynoteKey = "12"
        self.ext_event_handler.KeynoteType = UI.PostableCommand.UserKeynote
        self.ext_event.Raise()

    def other_action(self, sender, args):
        self.Title, self.prev_title = self.prev_title, self.Title

    def update_ui(self):
        if revit.doc:
            self.doc_tb.Text = 'Document: {}'.format(revit.doc.Title)
            elements = revit.query.get_all_elements(doc=revit.doc)
            self.elements_tb.Text = 'Element Count: {}'.format(len(elements))
        else:
            self.doc_tb.Text = 'No Documents'
            self.elements_tb.Text = 'N/A'
        logger.dev_log("update_ui", message="{} / {}".format(
            self.doc_tb.Text,
            self.elements_tb.Text
        ))

    def window_closing(self, sender, args): #pylint: disable=unused-argument
        revit.events.stop_events()


ui = script.load_ui(
    NonModalWindow(
        ext_event_handler=runtime_types.PlaceKeynoteExternalEventHandler()
        ),
    ui_file='NonModalWindow.xaml'
    )

ui.show(modal=__shiftclick__)