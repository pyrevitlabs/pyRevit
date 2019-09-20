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


logger = script.get_logger()


# with non-modal windows, Revit API call to command execute returns after
# creating the window, and thus, while window is running, Revit is NOT in
# API context and all the api calls needs be handled through external events.
# The event subscription (+=) happens on the API context inside the window
# __init__ method while window is being created, but
# the unsibscribe needs to happen on API context and thus an event handler
# is necessary. The event handler needs to hold a reference to window so
# it can unsibscribe the subscribed events
class FuncAsEventHandler(UI.IExternalEventHandler):
    def __init__(self, func):
        self.name = 'FuncAsEventHandler'
        self.func = func

    def Execute(self, uiapp):
        if self.func:
            logger.dev_log("exec_func_as_event")
            self.func()
            self.func = None

    def GetName(self):
        return self.name


class NonModalWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, ext_event_handler):
        forms.WPFWindow.__init__(self, xaml_file_name, set_owner=True)

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
            FuncAsEventHandler(self.stop_listening)
            )

        self.update_ui()
        self.start_listening()

    def uiupdator_eventhandler(self, sender, args):
        self.update_ui()

    def start_listening(self):
        logger.dev_log("start_listening")
        HOST_APP.app.DocumentChanged += self.docchanged_hndlr
        HOST_APP.app.DocumentClosed += self.docclosed_hndlr
        HOST_APP.app.DocumentOpened += self.docopened_hndlr
        HOST_APP.uiapp.ViewActivated += self.viewactivated_hndlr

    def stop_listening(self):
        logger.dev_log("stop_listening")
        HOST_APP.app.DocumentChanged -= self.docchanged_hndlr
        HOST_APP.app.DocumentClosed -= self.docclosed_hndlr
        HOST_APP.app.DocumentOpened -= self.docopened_hndlr
        HOST_APP.uiapp.ViewActivated -= self.viewactivated_hndlr

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
        logger.dev_log("update_ui")
        if revit.doc:
            self.doc_tb.Text = 'Document: {}'.format(revit.doc.Title)
            elements = revit.query.get_all_elements(doc=revit.doc)
            self.elements_tb.Text = 'Element Count: {}'.format(len(elements))
        else:
            self.doc_tb.Text = 'No Documents'
            self.elements_tb.Text = 'N/A'

    def window_closing(self, sender, args):
        self.remover.Raise()


NonModalWindow(
    'NonModalWindow.xaml',
    ext_event_handler=runtime_types.PlaceKeynoteExternalEventHandler(),
    ).show(modal=__shiftclick__)