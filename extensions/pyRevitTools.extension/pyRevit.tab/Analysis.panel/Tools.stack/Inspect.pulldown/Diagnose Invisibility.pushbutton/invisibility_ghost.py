# -*- coding: utf-8 -*-
"""Ghost preview of diagnosed elements inside Revit's own views.

Draws translucent copies of chosen elements through a DirectContext3D server
(``pyrevit.revit.dc3dserver``). The ghost ignores visibility settings, so a
hidden element shows up where it would be in the diagnosed view: above the
cut plane, outside the crop, behind a filter, and so on.

Warning:
    The server is registered with Revit's DirectContext3D service and stays
    registered until ``GhostPreview.close`` runs. The report closes it when
    its output window closes; anything else creating a preview must do the
    same, in Revit API context.
"""

from pyrevit import DB, HOST_APP
from pyrevit.revit import dc3dserver

from invisibility_checks import id_value

GHOST_COLOR = DB.ColorWithTransparency(245, 165, 36, 110)
_ZOOM_PADDING = 0.3
_MIN_ZOOM_HALF_SIZE_FT = 3.0


def _solids(geometry):
    pending = [geometry]
    while pending:
        for item in pending.pop():
            if isinstance(item, DB.Solid) and item.Faces.Size > 0:
                yield item
            elif isinstance(item, DB.GeometryInstance):
                pending.append(item.GetInstanceGeometry())
            elif isinstance(item, DB.GeometryElement):
                pending.append(item)


def _element_meshes(element):
    """Translucent meshes of an element's solids, or of its bounding box."""
    options = DB.Options()
    options.DetailLevel = DB.ViewDetailLevel.Fine
    meshes = []
    try:
        geometry = element.get_Geometry(options)
        if geometry is not None:
            for solid in _solids(geometry):
                mesh = dc3dserver.Mesh.from_solid(element.Document, solid, GHOST_COLOR)
                if mesh is not None:
                    meshes.append(mesh)
    except Exception:
        meshes = []
    if not meshes:
        bbox = element.get_BoundingBox(None)
        if bbox is not None:
            mesh = dc3dserver.Mesh.from_boundingbox(bbox, GHOST_COLOR)
            if mesh is not None:
                meshes.append(mesh)
    return meshes


def _zoom_to(uidoc, view, element):
    """Zoom the open UI view of ``view`` around the element's extents."""
    bbox = element.get_BoundingBox(None)
    if bbox is None:
        return
    center = (bbox.Min + bbox.Max) * 0.5
    half = (bbox.Max - bbox.Min) * (0.5 + _ZOOM_PADDING)
    half = DB.XYZ(
        max(half.X, _MIN_ZOOM_HALF_SIZE_FT),
        max(half.Y, _MIN_ZOOM_HALF_SIZE_FT),
        max(half.Z, _MIN_ZOOM_HALF_SIZE_FT),
    )
    for ui_view in uidoc.GetOpenUIViews():
        if ui_view.ViewId == view.Id:
            ui_view.ZoomAndCenterRectangle(center - half, center + half)
            return


class GhostPreview(object):
    """Per-report set of ghosted elements and the server that draws them.

    The DirectContext3D server is created on the first ``toggle`` and draws
    in every supported view of the report's document (plans, sections,
    elevations, 3D), not only the diagnosed one.

    Important:
        ``toggle`` and ``close`` touch Revit's external service registry and
        the UI, so they must run in Revit API context.
    """

    def __init__(self, doc):
        self.doc = doc
        self._server = None
        self._meshes = {}
        self._pending_zoom = []

    def toggle(self, uidoc, view, element):
        """Show or remove the ghost of ``element``.

        Showing also brings ``view`` into sight around the element: it zooms
        right away when ``view`` is active, otherwise it asks Revit to open
        it and zooms once Revit has activated it.

        Returns:
            (bool): True when the element is now ghosted.
        """
        key = id_value(element.Id)
        if key in self._meshes:
            del self._meshes[key]
            self._refresh(uidoc)
            return False
        self._meshes[key] = _element_meshes(element)
        self._refresh(uidoc)
        if uidoc.ActiveView.Id == view.Id:
            _zoom_to(uidoc, view, element)
        else:
            self._zoom_after_activation(view, element)
            uidoc.RequestViewChange(view)
        return True

    def close(self):
        """Remove all ghosts and unregister the server."""
        self._meshes = {}
        self._cancel_pending_zoom()
        if self._server is not None:
            try:
                self._server.meshes = []
                self._server.remove_server()
            except Exception:
                pass
            self._server = None
        try:
            uidoc = HOST_APP.uiapp.ActiveUIDocument
            if uidoc is not None:
                uidoc.RefreshActiveView()
        except Exception:
            pass

    def _refresh(self, uidoc):
        if self._server is None:
            self._server = dc3dserver.Server(
                uidoc=uidoc,
                name="pyRevit Diagnose Invisibility",
                description="Ghost preview of hidden elements",
            )
        meshes = []
        for element_meshes in self._meshes.values():
            meshes.extend(element_meshes)
        self._server.meshes = meshes
        uidoc.RefreshActiveView()

    def _zoom_after_activation(self, view, element):
        """Zoom once ``view`` is active and settled; a later request replaces this one.

        Revit restores a view's saved zoom after ``ViewActivated`` fires, so
        the zoom waits for the first ``Idling`` event after activation.
        """
        self._cancel_pending_zoom()
        uiapp = HOST_APP.uiapp
        view_id = view.Id
        element_id = element.Id

        def on_idling(sender, args):
            self._cancel_pending_zoom()
            uidoc = uiapp.ActiveUIDocument
            target = self.doc.GetElement(element_id)
            if uidoc is None or target is None or uidoc.ActiveView.Id != view_id:
                return
            _zoom_to(uidoc, uidoc.ActiveView, target)

        def on_view_activated(sender, args):
            if args.CurrentActiveView is None or args.CurrentActiveView.Id != view_id:
                return
            self._cancel_pending_zoom()
            uiapp.Idling += on_idling
            self._pending_zoom.append(("Idling", on_idling))

        uiapp.ViewActivated += on_view_activated
        self._pending_zoom.append(("ViewActivated", on_view_activated))

    def _cancel_pending_zoom(self):
        uiapp = HOST_APP.uiapp
        pending, self._pending_zoom = self._pending_zoom, []
        for event_name, handler in pending:
            try:
                if event_name == "Idling":
                    uiapp.Idling -= handler
                else:
                    uiapp.ViewActivated -= handler
            except Exception:
                pass
