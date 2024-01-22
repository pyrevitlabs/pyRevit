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


class Context(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Context, cls).__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self):
        self._active_view = None
        self._source_plan_view = None
        self.view_model = None

    @property
    def active_view(self):
        return self._active_view
    @active_view.setter
    def active_view(self, value):
        self._active_view = value
        self.view_model.update(self)

    @property
    def source_plan_view(self):
        return self._source_plan_view
    @source_plan_view.setter
    def source_plan_view(self, value):
        self._source_plan_view = value
        self.view_model.update(self)

class MainViewModel(forms.Reactive):

    def __init__(self):
        self._message = None

    @forms.reactive
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    def update(self, context):
        try:
            if not isinstance(context.active_view, DB.View3D):
                message = "Please activate a 3D View!"
            elif isinstance(context.source_plan_view, DB.ViewPlan):
                message = "Showing View Range of [{}]".format(context.source_plan_view.Name)
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
        external_event.Raise()

    def window_closed(self, sender, args):
        external_event.Raise()

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
        print(traceback.format_exc())

def view_activated(sender, args):
    try:
        context.active_view = args.CurrentActiveView
    except:
        print(traceback.format_exc())


def selection_changed(sender, args):
    try:
        doc = args.GetDocument()
        sel_ids = list(args.GetSelectedElements())
        if len(sel_ids) == 1:
            sel = doc.GetElement(sel_ids[0])
            if isinstance(sel, DB.ViewPlan):
                context.source_plan_view = sel
                return
        context.source_plan_view = None
    except:
        print(traceback.format_exc())



vm = MainViewModel()
context = Context()
context.view_model = vm
context.active_view = uidoc.ActiveGraphicalView

event_handler = SimpleEventHandler(unsubscribe)

external_event = UI.ExternalEvent.Create(event_handler)

main_window = MainWindow()
main_window.DataContext = vm
main_window.show()