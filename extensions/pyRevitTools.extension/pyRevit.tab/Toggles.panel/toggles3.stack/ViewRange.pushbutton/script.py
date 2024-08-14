# -*- coding: UTF-8 -*-

from __future__ import print_function
from pyrevit import script, forms, revit, HOST_APP
from pyrevit.revit import dc3dserver as d3d
import traceback

from Autodesk.Revit import DB, UI
from Autodesk.Revit.Exceptions import InvalidOperationException
from Autodesk.Revit.UI.Events import ViewActivatedEventArgs, SelectionChangedEventArgs
from Autodesk.Revit.DB.Events import DocumentChangedEventArgs

from System import EventHandler, Convert
from System.Windows.Media import Color, SolidColorBrush

from System.Collections.Generic import List

doc = revit.doc
uidoc = revit.uidoc

logger = script.get_logger()
output = script.get_output()

PLANES = {
    DB.PlanViewPlane.TopClipPlane: [0, 255, 0],
    DB.PlanViewPlane.CutPlane: [255, 0, 0],
    DB.PlanViewPlane.BottomClipPlane: [0, 0, 255],
    DB.PlanViewPlane.ViewDepthPlane: [255, 127, 0]
}

class SimpleEventHandler(UI.IExternalEventHandler):
    """
    Simple IExternalEventHandler sample
    """

    def __init__(self, do_this):
        self.do_this = do_this

    def Execute(self, uiapp):
        try:
            self.do_this(uiapp)
        except InvalidOperationException:
            print('InvalidOperationException catched')

    def GetName(self):
        return "SimpleEventHandler"


class Context(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Context, cls).__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self, view_model):
        self._active_view = None
        self._source_plan_view = None
        self.length_unit = (doc.GetUnits()
                             .GetFormatOptions(DB.SpecTypeId.Length)
                             .GetUnitTypeId())

        self.height_data = {}
        self.view_model = view_model
        view_model.unit_label = DB.LabelUtils.GetLabelForUnit(self.length_unit)

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
        if not self.is_valid():
            server.meshes = None
            refresh_event.Raise()

            self.view_model.topplane_elevation = "-"
            self.view_model.cutplane_elevation = "-"
            self.view_model.bottomplane_elevation = "-"
            self.view_model.viewdepth_elevation = "-"
            return
        try:
            def corners_from_bb(bbox):
                transform = bbox.Transform

                corners = [
                    bbox.Min,
                    bbox.Min + DB.XYZ.BasisX * (bbox.Max - bbox.Min).X,
                    bbox.Max,
                    bbox.Min + DB.XYZ.BasisY * (bbox.Max - bbox.Min).Y
                ]
                return [transform.OfPoint(c) for c in corners]

            if self.active_view.get_Parameter(
                    DB.BuiltInParameter.VIEWER_MODEL_CLIP_BOX_ACTIVE
            ).AsInteger() == 1:
                bbox = self.active_view.GetSectionBox()

                bb_corners = corners_from_bb(bbox)
            else:
                bb_corners = None

            view_range = self.source_plan_view.GetViewRange()

            edges = []
            triangles = []
            for plane in PLANES:

                plane_level = self.source_plan_view.Document.GetElement(
                    view_range.GetLevelId(plane)
                )

                if bb_corners:
                    corners = bb_corners
                else:
                    level_bbox = plane_level.get_BoundingBox(self.active_view)
                    corners = corners_from_bb(level_bbox)

                plane_elevation = (
                    plane_level.Elevation
                    + view_range.GetOffset(plane)
                )

                self.height_data[plane] = round(
                    DB.UnitUtils.ConvertFromInternalUnits(
                        plane_elevation,
                        self.length_unit
                    ),
                    2
                )

                cut_plane_vertices = [
                    DB.XYZ(c.X, c.Y, plane_elevation) for c in corners
                ]

                color = DB.ColorWithTransparency(
                    PLANES[plane][0],
                    PLANES[plane][1],
                    PLANES[plane][2],
                    180
                )

                edges.extend([
                    revit.dc3dserver.Edge(
                        cut_plane_vertices[i-1],
                        cut_plane_vertices[i],
                        color
                    ) for i in range(len(cut_plane_vertices))
                ])
                triangles.extend([
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
                ])

            mesh = revit.dc3dserver.Mesh(
                edges,
                triangles
            )

            server.meshes = [mesh]
            refresh_event.Raise()

            self.view_model.topplane_elevation = str(self.height_data[
                DB.PlanViewPlane.TopClipPlane])
            self.view_model.cutplane_elevation = str(self.height_data[
                DB.PlanViewPlane.CutPlane])
            self.view_model.bottomplane_elevation = str(self.height_data[
                DB.PlanViewPlane.BottomClipPlane])
            self.view_model.viewdepth_elevation = str(self.height_data[
                DB.PlanViewPlane.ViewDepthPlane])
        except:
            print(traceback.format_exc())



    def is_valid(self):
        if not isinstance(context.source_plan_view, DB.ViewPlan):
            self.view_model.message = \
                "Please select a Plan View in the Project Browser!"
            return False
        elif not isinstance(context.active_view, DB.View3D):
            self.view_model.message = "Please activate a 3D View!"
            return False
        else:
            self.view_model.message = "Showing View Range of\n[{}]".format(
                    self.source_plan_view.Name)
            return True


class MainViewModel(forms.Reactive):

    def __init__(self):
        self._message = None
        self.topplane_brush = SolidColorBrush(Color.FromRgb(
            *[Convert.ToByte(i) for i in PLANES[DB.PlanViewPlane.TopClipPlane]]
        ))
        self.cutplane_brush = SolidColorBrush(Color.FromRgb(
            *[Convert.ToByte(i) for i in PLANES[DB.PlanViewPlane.CutPlane]]
        ))
        self.bottomplane_brush = SolidColorBrush(Color.FromRgb(
            *[Convert.ToByte(i) for i in PLANES[DB.PlanViewPlane.BottomClipPlane]]
        ))
        self.viewdepth_brush = SolidColorBrush(Color.FromRgb(
            *[Convert.ToByte(i) for i in PLANES[DB.PlanViewPlane.ViewDepthPlane]]
        ))
        self._topplane_elevation = "-"
        self._cutplane_elevation = "-"
        self._bottomplane_elevation = "-"
        self._viewdepth_elevation = "-"

        self.unit_label = ""

    @forms.reactive
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    @forms.reactive
    def topplane_elevation(self):
        return self._topplane_elevation

    @topplane_elevation.setter
    def topplane_elevation(self, value):
        self._topplane_elevation = value

    @forms.reactive
    def cutplane_elevation(self):
        return self._cutplane_elevation

    @cutplane_elevation.setter
    def cutplane_elevation(self, value):
        self._cutplane_elevation = value

    @forms.reactive
    def bottomplane_elevation(self):
        return self._bottomplane_elevation

    @bottomplane_elevation.setter
    def bottomplane_elevation(self, value):
        self._bottomplane_elevation = value

    @forms.reactive
    def viewdepth_elevation(self):
        return self._viewdepth_elevation

    @viewdepth_elevation.setter
    def viewdepth_elevation(self, value):
        self._viewdepth_elevation = value


class MainWindow(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self, "MainWindow.xaml")
        self.Closed += self.window_closed
        subscribe()
        server.add_server()


    def window_closed(self, sender, args):
        server.remove_server()
        refresh_event.Raise()
        unsubscribe_event.Raise()

def subscribe():
    try:
        ui_app = UI.UIApplication(HOST_APP.app)
        ui_app.ViewActivated += EventHandler[ViewActivatedEventArgs](view_activated)
        ui_app.SelectionChanged += EventHandler[SelectionChangedEventArgs](selection_changed)
        ui_app.Application.DocumentChanged += EventHandler[DocumentChangedEventArgs](doc_changed)
    except:
        print(traceback.format_exc())


def unsubscribe(uiapp):
    try:
        uiapp.ViewActivated -= EventHandler[ViewActivatedEventArgs](view_activated)
        uiapp.SelectionChanged -= EventHandler[SelectionChangedEventArgs](selection_changed)
        uiapp.Application.DocumentChanged -= EventHandler[DocumentChangedEventArgs](doc_changed)
    except:
        print(traceback.format_exc())


def refresh_active_view(uiapp):
    uidoc = uiapp.ActiveUIDocument
    uidoc.ActiveView = context.active_view
    uidoc.RefreshActiveView()
    if context.source_plan_view:
        uidoc.Selection.SetElementIds(List[DB.ElementId]([context.source_plan_view.Id]))


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

def doc_changed(sender, args):
    try:
        context.context_changed()
    except:
        print(traceback.format_exc())



server = revit.dc3dserver.Server(register=False)

unsubscribe_event = UI.ExternalEvent.Create(SimpleEventHandler(unsubscribe))
refresh_event = UI.ExternalEvent.Create(SimpleEventHandler(refresh_active_view))

vm = MainViewModel()
context = Context(vm)
context.active_view = uidoc.ActiveGraphicalView

main_window = MainWindow()
main_window.DataContext = vm
main_window.show()
