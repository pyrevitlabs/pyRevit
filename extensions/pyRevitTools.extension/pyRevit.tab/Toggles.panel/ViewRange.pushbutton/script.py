# -*- coding: UTF-8 -*-

from __future__ import print_function
from pyrevit import script, forms, revit
import traceback

from Autodesk.Revit import DB, UI
from Autodesk.Revit.Exceptions import InvalidOperationException
from Autodesk.Revit.UI.Events import ViewActivatedEventArgs, SelectionChangedEventArgs

from System import EventHandler

doc = revit.doc
uidoc = revit.uidoc

logger = script.get_logger()
output = script.get_output()

class SimpleEventHandler(UI.IExternalEventHandler):
    """
    Simple IExternalEventHandler sample
    """

    def __init__(self, do_this):
        self.do_this = do_this

    def Execute(self, uiapp):
        try:
            self.do_this()
        except InvalidOperationException:
            print('InvalidOperationException catched')

    def GetName(self):
        return "SimpleEventHandler"

def subscribe():
    try:
        print("subscribe")
        ui_app = UI.UIApplication(doc.Application)
        ui_app.ViewActivated += EventHandler[ViewActivatedEventArgs](view_activated)
        ui_app.SelectionChanged += EventHandler[SelectionChangedEventArgs](selection_changed)
    except:
        print(traceback.format_exc())

def unsubscribe():
    try:
        print("unsubscribe")
        ui_app = UI.UIApplication(doc.Application)
        ui_app.ViewActivated -= EventHandler[ViewActivatedEventArgs](view_activated)
        ui_app.SelectionChanged -= EventHandler[SelectionChangedEventArgs](selection_changed)
    except:
        pass
        # print(traceback.format_exc())

def view_activated(sender, args):
    try:
        context["active_view"] = args.CurrentActiveView
        doc = args.Document
        vm.update()
    except:
        print(traceback.format_exc())


def selection_changed(sender, args):
    try:
        doc = args.GetDocument()
        sel_ids = list(args.GetSelectedElements())
        if len(sel_ids) == 1:
            sel = doc.GetElement(sel_ids[0])
            if isinstance(sel, DB.View):
                context["source_view"] = sel
        else:
            context["source_view"] = None
        vm.update()
    except:
        print(traceback.format_exc())



class MainViewModel(forms.Reactive):

    def __init__(self):
        self._message = None
        self.update()

    @forms.reactive
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    def update(self):
        try:
            if not isinstance(context["active_view"], DB.View3D):
                message = "Please activate a 3D View!"
            elif isinstance(context["source_view"], DB.ViewPlan):
                message = "Showing View Range of [{}]".format(context["source_view"].Name)
            else:
                message = "Please select a Plan View in the Project Browser!"
            self.message = message
        except:
            print(traceback.format_exc())

class MainWindow(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self, "MainWindow.xaml")
        self.Closed += self.window_closed
        subscribe()

    def btn_click(self, sender, args):
        print("hey from button")
        # print(doc.Title)
        external_event.Raise()

    def window_closed(self, sender, args):
        external_event.Raise()


active_view = doc.ActiveView
source_view = None

context = {
    "active_view": uidoc.ActiveGraphicalView,
    "source_view": None
}

event_handler = SimpleEventHandler(unsubscribe)

external_event = UI.ExternalEvent.Create(event_handler)

vm = MainViewModel()
main_window = MainWindow()
main_window.DataContext = vm
main_window.show()