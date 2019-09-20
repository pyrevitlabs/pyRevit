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


class NonModalWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, ext_event_handler):
        forms.WPFWindow.__init__(self, xaml_file_name, set_owner=False)

        self.ext_event_handler = ext_event_handler
        self.ext_event = \
            UI.ExternalEvent.Create(self.ext_event_handler)

        self.prev_title = "Title Changed..."

        # activate document updator
        self.update_ui()
        self.start_listening()

    def uiupdator_eventhandler(self, sender, args):
        self.update_ui()

    def start_listening(self):
        HOST_APP.app.DocumentClosed += self.uiupdator_eventhandler
        HOST_APP.app.DocumentOpened += self.uiupdator_eventhandler
        HOST_APP.app.DocumentChanged += self.uiupdator_eventhandler
        HOST_APP.uiapp.ViewActivated += self.uiupdator_eventhandler

    def stop_listening(self):
        # FIXME: this crashes Revit
        # HOST_APP.app.DocumentChanged -= self.docchanged_handler
        # HOST_APP.uiapp.ViewActivated -= self.viewactivated_handler
        pass

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
