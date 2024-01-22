# -*- coding: UTF-8 -*-

from __future__ import print_function
from pyrevit import script, forms, revit
from pyrevit.revit import dc3dserver as d3d
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
        self.context_changed()

    @property
    def source_plan_view(self):
        return self._source_plan_view
    @source_plan_view.setter
    def source_plan_view(self, value):
        self._source_plan_view = value
        self.context_changed()

    def context_changed(self):
        server.uidoc = UI.UIDocument(self.active_view.Document)
        if self.view_model:
             self.view_model.update(self)
        if not self.is_valid():
            server.meshes = None
            server.uidoc.RefreshActiveView()
            return
        try:
            shape_loops = list(
                self.source_plan_view.GetCropRegionShapeManager().GetCropShape())
            shape_outline = DB.Outline(DB.XYZ.Zero, DB.XYZ.Zero)
            for loop in shape_loops:
                for curve in loop:
                    shape_outline.AddPoint(curve.GetEndPoint(0))


            bbox = self.active_view.GetSectionBox()
            transform = bbox.Transform

            corners = [
                bbox.Min,
                bbox.Min + DB.XYZ.BasisX * (bbox.Max - bbox.Min).X,
                bbox.Max,
                bbox.Min + DB.XYZ.BasisY * (bbox.Max - bbox.Min).Y
            ]

            corners = [transform.OfPoint(c) for c in corners]

            view_level = self.source_plan_view.GenLevel
            view_range = self.source_plan_view.GetViewRange()
            cut_plane_level = self.source_plan_view.Document.GetElement(
                view_range.GetLevelId(DB.PlanViewPlane.CutPlane)
            )
            cut_plane_elevation = (
                cut_plane_level.Elevation
                + view_range.GetOffset(DB.PlanViewPlane.CutPlane)
            )

            cut_plane_vertices = [
                DB.XYZ(c.X, c.Y, cut_plane_elevation) for c in corners
            ]

            color = DB.ColorWithTransparency(255, 0, 0, 180)

            edges = [
                revit.dc3dserver.Edge(
                    cut_plane_vertices[i-1],
                    cut_plane_vertices[i],
                    color
                ) for i in range(len(cut_plane_vertices))
            ]
            triangles = [
                revit.dc3dserver.Triangle(
                    cut_plane_vertices[0],
                    cut_plane_vertices[1],
                    cut_plane_vertices[2],
                    revit.dc3dserver.Mesh.calculate_triangle_normal(
                        cut_plane_vertices[0],
                        cut_plane_vertices[1],
                        cut_plane_vertices[2],
                    ),
                    color
                ),
                revit.dc3dserver.Triangle(
                    cut_plane_vertices[2],
                    cut_plane_vertices[3],
                    cut_plane_vertices[0],
                    revit.dc3dserver.Mesh.calculate_triangle_normal(
                        cut_plane_vertices[2],
                        cut_plane_vertices[3],
                        cut_plane_vertices[0],
                    ),
                    color
                )
            ]

            mesh = revit.dc3dserver.Mesh(
                edges,
                triangles
            )

            server.meshes = [mesh]
            server.uidoc.RefreshActiveView()
        except:
            print(traceback.format_exc())



    def is_valid(self):
        return (
            isinstance(context.source_plan_view, DB.ViewPlan) and
            isinstance(context.active_view, DB.View3D) and
            context.active_view.IsSectionBoxActive
        )

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
            if context.is_valid():
                message = "Showing View Range of [{}]".format(context.source_plan_view.Name)
            elif not isinstance(context.active_view, DB.View3D):
                message = "Please activate a 3D View!"
            elif not context.active_view.IsSectionBoxActive:
                message = "3D View has no Section Box!"
            elif not isinstance(context.source_plan_view, DB.ViewPlan):
                message = "Please select a Plan View in the Project Browser!"
            self.message = message
        except:
            print(traceback.format_exc())

class MainWindow(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self, "MainWindow.xaml")
        self.Closed += self.window_closed
        subscribe()
        server.add_server()


    def window_closed(self, sender, args):
        external_event.Raise()
        server.remove_server()
        uidoc.RefreshActiveView()

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


server = revit.dc3dserver.Server(register=False)

vm = MainViewModel()
context = Context()
context.view_model = vm
context.active_view = uidoc.ActiveGraphicalView


event_handler = SimpleEventHandler(unsubscribe)

external_event = UI.ExternalEvent.Create(event_handler)

main_window = MainWindow()
main_window.DataContext = vm
main_window.show()