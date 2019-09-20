"""Testing non-modal windows calling actions thru external events.

Shift-Click:
Run window as Modal
"""
# pylint: skip-file
from pyrevit import HOST_APP, framework
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit.runtime import types as runtime_types


__context__ = 'zero-doc'


# with non-modal windows, Revit API call to command execute returns after
# creating the window, and thus, while window is running, Revit is NOT in
# API context and all the api calls needs be handled through external events.
# The event subscription (+=) happens on the API context inside the window
# __init__ method while window is being created, but
# the unsibscribe needs to happen on API context and thus an event handler
# is necessary. The event handler needs to hold a reference to window so
# it can unsibscribe the subscribed events
class EventHandlerRemover(UI.IExternalEventHandler):
    def __init__(self, window):
        self.name = 'EventHandlerRemover'
        self.target_window = window

    def Execute(self, uiapp):
        if self.target_window:
            HOST_APP.app.DocumentChanged -= \
                self.target_window.docchanged_hndlr
            HOST_APP.app.DocumentClosed -= \
                self.target_window.docclosed_hndlr
            HOST_APP.app.DocumentOpened -= \
                self.target_window.docopened_hndlr
            HOST_APP.uiapp.ViewActivated -= \
                self.target_window.viewactivated_hndlr
            self.target_window = None

    def GetName(self):
        return self.name


class NonModalWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, ext_event_handler):
        forms.WPFWindow.__init__(self, xaml_file_name, set_owner=False)

        self.ext_event_handler = ext_event_handler
        self.ext_event = \
            UI.ExternalEvent.Create(self.ext_event_handler)

        self.prev_title = "Title Changed..."

        # activate document updator
        self.docchanged_hndlr = \
            framework.EventHandler[DB.Events.DocumentChangedEventArgs](
                self.uiupdator_eventhandler
            )
        self.docclosed_hndlr = \
            framework.EventHandler[DB.Events.DocumentClosedEventArgs](
                self.uiupdator_eventhandler
            )
        self.docopened_hndlr = \
            framework.EventHandler[DB.Events.DocumentOpenedEventArgs](
                self.uiupdator_eventhandler
            )
        self.viewactivated_hndlr = \
            framework.EventHandler[UI.Events.ViewActivatedEventArgs](
                self.uiupdator_eventhandler
            )

        self.remover = UI.ExternalEvent.Create(
            EventHandlerRemover(self)
            )

        self.update_ui()
        self.start_listening()

    def uiupdator_eventhandler(self, sender, args):
        self.update_ui()

    def start_listening(self):
        HOST_APP.app.DocumentChanged += self.docchanged_hndlr
        HOST_APP.app.DocumentClosed += self.docclosed_hndlr
        HOST_APP.app.DocumentOpened += self.docopened_hndlr
        HOST_APP.uiapp.ViewActivated += self.viewactivated_hndlr

    def stop_listening(self):
        self.remover.Raise()

    def action(self, sender, args):
        if __shiftclick__:
            self.Close()
            forms.alert("Stuff")
        else:
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

    def window_closing(self, sender, args):
        self.stop_listening()


NonModalWindow(
    'NonModalWindow.xaml',
    ext_event_handler=runtime_types.PlaceKeynoteExternalEventHandler(),
    ).show(modal=__shiftclick__)