# -*- coding: utf-8 -*-
"""Interactive 3D preview of the section or crop box in a docked output window.

The page (``preview.js``, ``preview.css``) draws the model, levels, grids and
scope boxes and lets the user drag the box faces and, on plan views, the view
range planes with snapping; this module streams the model to it, applies what
it posts and keeps bookmarks.

Page -> Python actions: ``ready``, ``apply_box``, ``apply_view_range``
(new heights of view range planes), ``use_scope_box``,
``bookmark_save``, ``bookmark_apply``, ``bookmark_rename``,
``bookmark_delete``, ``fit_visible``, ``load_group`` (stream the elements of
one category that are not loaded: left out by the point limit, or only lines at
the view's detail level), ``save_settings`` (the page's display and box
toggles, kept in the navigator's config).
Python -> page events: ``scene`` (a model chunk), ``view`` (box, kind and
bookmarks of the active view), ``box`` (the box changed in Revit), ``guides``
(levels, grids and scope boxes), ``sources`` (link geometry added or removed,
the whole model dropped to be streamed again, or streaming finished with the
elements left out per category), ``result``, ``error``.

Important:
    Handlers outlive the command, so the bundle must run on a persistent
    engine. They run in Revit API context.
"""

import io
import json
import os
import uuid

from pyrevit import DB, HOST_APP, forms, script
from pyrevit.compat import get_elementid_from_value_func
from pyrevit.framework import Controls, System
from pyrevit.output.bridge import PageBridge
from pyrevit.revit import events
from scene3d import read_asset as read_lib_asset
from scene3d.meshing import box_corners, scene_to_json

from sectionbox_geometry import get_box_info, get_crop_edit_blocker
from sectionbox_scene import (
    ModelStream,
    box_from_payload,
    box_payload,
    grids_payload,
    levels_payload,
    north_angle,
    scene_origin,
    scope_boxes_payload,
    units_payload,
    view_focus_bounds,
    view_payload,
)
from sectionbox_scene_filter import SceneFilter
from sectionbox_settings import dump_settings, parse_settings
from sectionbox_sources import (
    get_visible_model_elements,
    scope_box_to_bounding_box,
)
from sectionbox_viewrange import (
    ViewRangeError,
    build_view_range,
    controlling_template_name,
    has_view_range,
)
from sectionbox_viewrange_rules import BOTTOM, CUT, DEPTH, TOP

logger = script.get_logger()
get_elementid_from_value = get_elementid_from_value_func()
_BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

CHUNK_SECONDS = 1.0
PAGE_WIDTH = 820
PIN_TOOLTIP = "Keep On Top"
BOOKMARK_SLOT = "SectionBoxPreviewBookmarks"
SETTINGS_OPTION = "preview_settings"
MIN_EXTENT_FT = 1e-6
RANGE_PLANE_STRINGS = {
    TOP: "PreviewRangeTop",
    CUT: "PreviewRangeCut",
    BOTTOM: "PreviewRangeBottom",
    DEPTH: "PreviewRangeDepth",
}
PAGE_STRINGS = (
    "PreviewTitle",
    "PreviewLevels",
    "PreviewGrids",
    "PreviewAllGrids",
    "PreviewNames",
    "PreviewScopeBoxes",
    "PreviewModel",
    "PreviewCut",
    "PreviewCutOff",
    "PreviewCutGhost",
    "PreviewCutHide",
    "PreviewGhostStrength",
    "PreviewLive",
    "PreviewSnap",
    "PreviewFitBox",
    "PreviewFitModel",
    "PreviewTop",
    "PreviewFront",
    "PreviewSide",
    "PreviewAllLevels",
    "PreviewGroupShow",
    "PreviewGroupView",
    "PreviewGroupBox",
    "PreviewHintElement",
    "PreviewHintGrid",
    "PreviewIso",
    "PreviewView",
    "PreviewAlignGrid",
    "PreviewFitVisible",
    "PreviewPickElement",
    "PreviewBookmarks",
    "PreviewBookmarkSave",
    "PreviewBookmarkApply",
    "PreviewBookmarkRename",
    "PreviewBookmarkDelete",
    "PreviewBookmarkName",
    "PreviewUseScopeBox",
    "PreviewLoading",
    "PreviewLoaded",
    "PreviewTruncated",
    "PreviewNoBox",
    "PreviewSnappedTo",
    "PreviewHelp",
    "PreviewBlockedScopeBox",
    "PreviewBlockedCropShape",
    "PreviewApplied",
    "PreviewFailed",
    "PreviewSize",
    "PreviewCategories",
    "PreviewAll",
    "PreviewNone",
    "PreviewCubeBack",
    "PreviewCubeBottom",
    "PreviewCubeLeft",
    "PreviewCubeRight",
    "PreviewCompass",
    "PreviewBoxOnly",
    "PreviewBoxes",
    "PreviewNotLoaded",
    "PreviewLoadGroup",
    "PreviewSearch",
    "PreviewViewRange",
    "PreviewRangeTop",
    "PreviewRangeCut",
    "PreviewRangeBottom",
    "PreviewRangeDepth",
    "PreviewRangeTemplate",
    "PreviewRangeRelative",
    "PreviewRangeOffsetPrompt",
    "PreviewRangeNotANumber",
    "PreviewRangeFailed",
    "PreviewRangeHelp",
)


def _read_bundle_asset(name):
    with io.open(os.path.join(_BUNDLE_DIR, name), encoding="utf-8") as asset:
        return asset.read()


class PreviewSession(object):
    """One open preview window for the navigator.

    Args:
        output (pyrevit.output.PyRevitOutputWindow): the command's output window.
        navigator (System.Windows.Window): the navigator window to dock beside.
        get_string (callable): locale key -> localized string.
        datafilename (str): script data slot of the stored (inactive) boxes.
        include_links (callable): returns whether link geometry, levels and
            grids are included.
        collect_guides (callable): returns ``(levels, grids)`` as
            ``get_all_levels``/``get_all_grids`` do for the current setting.
        on_box_changed (callable): called after the preview changed the box.
        on_closed (callable): called when the preview window closes.
        config (pyrevit.coreutils.configparser.ConfigSection | None):
            the navigator's config, where the page's display and box settings
            are kept between sessions; without it they are not remembered.

    Lifecycle:
        ``open`` creates the page and docks it; ``close`` or the user closing
        the window ends it. Element ids and the origin are kept, never API
        objects, because the user can switch views and documents while it is
        open.

    Invariant:
        Every request from the page echoes the ``generation`` of the view
        payload it was made from, which changes whenever the session follows
        another view or document. A request of an older generation is
        rejected, so an edit queued for one view is never written to another.
        An ``apply_box`` request also carries an edit ``revision``. Every
        view payload sent afterwards, including the ones that follow document
        changes, repeats the latest applied revision, so the page can ignore
        a box that predates its latest edit.
    """

    def __init__(
        self,
        output,
        navigator,
        get_string,
        datafilename,
        include_links,
        collect_guides,
        on_box_changed,
        on_closed,
        config=None,
    ):
        self.output = output
        self.navigator = navigator
        self.get_string = get_string
        self.datafilename = datafilename
        self.include_links = include_links
        self.collect_guides = collect_guides
        self.on_box_changed = on_box_changed
        self.on_closed = on_closed
        self.config = config
        self.bridge = PageBridge(output, "sectionbox-preview")
        self.root_id = "sbp-app-{}".format(uuid.uuid4().hex[:8])
        self.is_open = False
        self._mounted = False
        self._shutting_down = False
        self._loaded_doc = None
        self.doc = None
        self.view_id = None
        self._view_generation = 0
        self._applied_revision = None
        self.origin = DB.XYZ.Zero
        self._streams = []
        self._ready = False
        self._generation = 0
        self._linked = False
        self._model_filter = SceneFilter()
        for action, handler in (
            ("ready", self._on_ready),
            ("apply_box", self._on_apply_box),
            ("apply_view_range", self._on_apply_view_range),
            ("use_scope_box", self._on_use_scope_box),
            ("bookmark_save", self._on_bookmark_save),
            ("bookmark_apply", self._on_bookmark_apply),
            ("bookmark_rename", self._on_bookmark_rename),
            ("bookmark_delete", self._on_bookmark_delete),
            ("fit_visible", self._on_fit_visible),
            ("load_group", self._on_load_group),
            ("save_settings", self._on_save_settings),
        ):
            self.bridge.handlers[action] = handler

    @property
    def shutting_down(self):
        """True once the navigator closed and the preview can no longer open."""
        return self._shutting_down

    @property
    def supported(self):
        """True when the output window can exchange messages with the page."""
        return self.output.supports_messages

    def open(self, view):
        """Show the preview for ``view``, mounting the page on first use.

        Must run in the command or another API context. Returns False when
        the output window cannot receive messages.
        """
        if self.is_open:
            self.output.window.Activate()
            return True
        if not self._mounted and not self.bridge.start():
            return False
        changed_view = view.Id != self.view_id
        self._follow(view)
        info = get_box_info(view, self.datafilename)
        if self._mounted:
            self._reopen(view, info, changed_view)
        else:
            self._mount(view, info)
        self.is_open = True
        self._resume_streams()
        self.dock()
        return True

    def _follow(self, view):
        try:
            same_document = view.Document.Equals(self.doc)
        except Exception:
            same_document = False
        if not same_document or view.Id != self.view_id:
            self._view_generation += 1
            self._applied_revision = None
        self.doc = view.Document
        self.view_id = view.Id

    def _mount(self, view, info):
        self.origin = scene_origin(self.doc, info["box"] if info else None)
        window = self.output.window
        window.Closing += self._on_window_closing
        window.Width = PAGE_WIDTH
        self._keep_on_top()
        self.navigator.LocationChanged += self._on_navigator_moved
        self.navigator.SizeChanged += self._on_navigator_moved
        self.output.set_title(self.get_string("PreviewTitle"))
        self.output.add_style(_read_bundle_asset("preview.css"))
        self.output.inject_script(read_lib_asset("gl.js"))
        self.output.inject_script(read_lib_asset("viewcube.js"))
        self.output.inject_script(_read_bundle_asset("preview.js"))
        self.output.inject_to_body("div", "", {"id": self.root_id})
        self.output.inject_script(
            "window.pyRevitSectionBoxPreview.mount({}, {});".format(
                json.dumps(self.root_id),
                json.dumps(self._mount_payload(view), ensure_ascii=False),
            ),
            body=True,
        )
        self._mounted = True
        self._loaded_doc = self.doc

    def _keep_on_top(self):
        """Press the output window's own pin button so it stays above Revit.

        The button toggles the window's ``Topmost`` and swaps its icon, which
        setting ``Topmost`` directly would leave stale. It is found by its
        tooltip because other title bar buttons are inserted around it.
        """
        window = self.output.window
        if window.Topmost:
            return
        pin = next(
            (
                item
                for item in window.RightWindowCommands.Items
                if str(item.ToolTip) == PIN_TOOLTIP
            ),
            None,
        )
        if pin is None:
            logger.debug("The output window has no pin button")
            window.Topmost = True
            return
        pin.RaiseEvent(System.Windows.RoutedEventArgs(Controls.Button.ClickEvent, pin))

    def _reopen(self, view, info, changed_view):
        self.output.window.Show()
        if self._same_document():
            self._send("view" if changed_view else "box", self._view_payload(view))
            self._send("guides", self._guides_payload())
            self._model_filter_changed(view)
            self._linked_changed()
            return
        self.origin = scene_origin(self.doc, info["box"] if info else None)
        self._loaded_doc = self.doc
        self._streams = []
        self._ready = False
        self._send("reset", self._mount_payload(view))

    def _same_document(self):
        try:
            return self.doc.Equals(self._loaded_doc) and self._loaded_doc.IsValidObject
        except Exception:
            return False

    def close(self):
        """Hide the preview window and pause streaming; ``open`` shows it again.

        The output window cannot be recreated once closed, so the user closing
        it only hides it. Hiding also applies to a window that something else
        showed again, such as a warning logged to the same output window.
        """
        if not self._mounted:
            return
        self.is_open = False
        self._generation += 1
        self.output.window.Hide()

    def shutdown(self):
        """Close the window for good, when the navigator closes."""
        self._shutting_down = True
        self.is_open = False
        self._generation += 1
        self._streams = []
        try:
            self.navigator.LocationChanged -= self._on_navigator_moved
            self.navigator.SizeChanged -= self._on_navigator_moved
        except Exception:
            logger.debug("Navigator events were not attached")
        if self._mounted:
            self.bridge.stop()
            try:
                self.output.window.Close()
            except Exception:
                logger.debug("Preview window was already closed")

    def _on_window_closing(self, sender, args):
        if self._shutting_down:
            return
        args.Cancel = True
        self.close()
        self.on_closed()

    def dock(self):
        """Place the preview against the navigator's right edge, or its left."""
        self._on_navigator_moved(None, None)

    def _on_navigator_moved(self, sender, args):
        if not self.is_open:
            return
        window = self.output.window
        navigator = self.navigator
        area = _work_area()
        right_edge = navigator.Left + navigator.ActualWidth
        if right_edge + window.Width <= area.Right:
            window.Left = right_edge
        else:
            window.Left = max(area.Left, navigator.Left - window.Width)
        window.Top = navigator.Top
        window.Height = max(navigator.ActualHeight, 480)

    def _mount_payload(self, view):
        return {
            "channel": self.bridge.channel,
            "strings": dict((name, self.get_string(name)) for name in PAGE_STRINGS),
            "units": units_payload(self.doc),
            "northAngle": north_angle(self.doc),
            "settings": self._load_settings(),
            "view": self._view_payload(view),
            "document": self.doc.Title,
        }

    def _view_payload(self, view):
        payload = view_payload(view, self.datafilename, self.origin)
        payload["generation"] = self._view_generation
        payload["theme"] = "dark" if forms.is_dark_theme() else "light"
        if self._applied_revision is not None:
            payload["revision"] = self._applied_revision
        payload["bookmarks"] = self._bookmark_entries(view, payload["kind"])
        return payload

    def _guides_payload(self):
        levels, grids = self.collect_guides()
        return {
            "levels": levels_payload(levels, self.origin),
            "grids": grids_payload(grids, self.origin),
            "scopeBoxes": scope_boxes_payload(self.doc, self.origin),
        }

    def _send(self, event, payload=None):
        self.bridge.send(event, payload)

    def _on_ready(self, payload, request_id):
        self._ready = True
        self._send("guides", self._guides_payload())
        self._linked = self.include_links()
        self._model_filter = SceneFilter.for_view(self._followed_view())
        self._streams = self._new_streams()
        self._stream_all()

    def _followed_view(self):
        return self.doc.GetElement(self.view_id) if self.view_id else None

    def _focus_bounds(self):
        view = self._followed_view()
        if view is None:
            return None
        return view_focus_bounds(view, self.datafilename)

    def _new_streams(self):
        focus = self._focus_bounds()
        streams = [
            ModelStream(
                self.doc,
                self.origin,
                False,
                focus=focus,
                scene_filter=self._model_filter,
            )
        ]
        if self._linked:
            streams.append(self._link_stream(focus))
        return streams

    def _link_stream(self, focus=None):
        return ModelStream(
            self.doc,
            self.origin,
            True,
            links_only=True,
            focus=focus,
            scene_filter=self._model_filter,
        )

    def _model_filter_changed(self, view):
        """Stream the model again when ``view`` reads it differently.

        That is another detail level, phase, phase filter or design option.
        """
        if not self._ready:
            return
        scene_filter = SceneFilter.for_view(view)
        if scene_filter.key == self._model_filter.key:
            return
        self._model_filter = scene_filter
        self._streams = self._new_streams()
        self._send("sources", {"dropAll": True, "loading": True})
        self._stream_all()

    def _load_settings(self):
        if self.config is None:
            return {}
        return parse_settings(self.config.get_option(SETTINGS_OPTION, ""))

    def _on_save_settings(self, payload, request_id):
        if self.config is None:
            return
        self.config.set_option(SETTINGS_OPTION, dump_settings(payload.get("settings")))
        script.save_config()

    def _on_load_group(self, payload, request_id):
        """Queue the elements of a category that are not loaded and stream them.

        A request that finds nothing to load still restarts a stream that an
        error interrupted: the elements it queued stay in the stream, so the
        retry after the error resumes them instead of reporting an empty
        category.
        """
        queued = 0
        for stream in self._streams:
            queued += stream.load_group(int(payload["source"]), payload["group"])
        unfinished = any(not stream.done for stream in self._streams)
        if not queued and not unfinished:
            self.bridge.reply(request_id, False, "Nothing to load")
            return
        self.bridge.reply(request_id, True)
        self._send("sources", {"loading": True})
        self._stream_all()

    def _stream_all(self):
        self._generation += 1
        self._stream_next(self._generation)

    def _resume_streams(self):
        if any(not stream.done for stream in self._streams):
            self._stream_all()

    def _stream_next(self, generation):
        if not self.is_open or generation != self._generation:
            return
        stream = next((s for s in self._streams if not s.done), None)
        if stream is None:
            truncated = sum(s.truncated for s in self._streams)
            dropped = [group for s in self._streams for group in s.dropped_groups()]
            self._send(
                "sources", {"done": True, "truncated": truncated, "dropped": dropped}
            )
            return
        try:
            chunk = stream.next_chunk(CHUNK_SECONDS)
        except Exception as ex:
            logger.exception("Streaming the model failed: {}".format(ex))
            self._send("error", {"message": str(ex)})
            return
        if chunk is not None:
            self.bridge.send("scene", raw_payload=scene_to_json(chunk))
        events.execute_in_revit_context(self._stream_next, generation)

    def sync_links(self):
        """Apply a changed "Include links" setting: guides and link geometry."""
        if self.is_open:
            self._linked_changed()

    def _linked_changed(self):
        if not self._ready or self._linked == self.include_links():
            return
        self._linked = self.include_links()
        self._send("guides", self._guides_payload())
        if self._linked:
            self._streams.append(self._link_stream(self._focus_bounds()))
            self._send("sources", {"loading": True})
        else:
            self._streams = [s for s in self._streams if not s.links_only]
            self._send("sources", {"dropLinks": True})
        self._stream_all()

    def sync_view(self, view):
        """Show another view's box, or rebuild everything for another document.

        The same view only gets its box refreshed: Revit reports a document
        change after every edit, and a ``view`` event would reset the page's
        camera each time the box is moved.
        """
        if not self.is_open:
            return
        try:
            same_document = view.Document.Equals(self.doc)
        except Exception:
            same_document = False
        if not same_document:
            self._follow(view)
            info = get_box_info(view, self.datafilename)
            self.origin = scene_origin(self.doc, info["box"] if info else None)
            self._loaded_doc = self.doc
            self._streams = []
            self._ready = False
            self._send("reset", self._mount_payload(view))
            return
        event = "box" if view.Id == self.view_id else "view"
        self._follow(view)
        self._send(event, self._view_payload(view))
        self._model_filter_changed(view)

    def sync_box(self, view):
        """Send the view's current box after the navigator's buttons changed it."""
        if self.is_open:
            self._send("box", self._view_payload(view))

    def _active_view(self, payload):
        if payload.get("generation") != self._view_generation:
            raise ValueError("view")
        uidoc = HOST_APP.uiapp.ActiveUIDocument
        if uidoc is None or not uidoc.Document.Equals(self.doc):
            raise ValueError("document")
        view = uidoc.ActiveView
        if view.Id != self.view_id:
            raise ValueError("view")
        return view

    def _write_box(self, view, box_data):
        if isinstance(view, DB.View3D):
            if abs(box_data["bz"][2] - 1.0) > 1e-6:
                raise ValueError("A section box must keep a vertical Z axis")
            new_box = box_from_payload(box_data, self.origin)
        else:
            if get_crop_edit_blocker(view):
                raise ValueError("The crop box cannot be edited")
            new_box = box_from_payload(box_data, self.origin, template=view.CropBox)
        extent = new_box.Max - new_box.Min
        if min(extent.X, extent.Y, extent.Z) <= MIN_EXTENT_FT:
            raise ValueError("The box would have no volume")
        if isinstance(view, DB.View3D):
            self._commit_edit("Adjust Section Box", lambda: view.SetSectionBox(new_box))
        else:
            self._commit_edit(
                "Adjust Crop Box", lambda: setattr(view, "CropBox", new_box)
            )

    def _commit_edit(self, name, edit):
        """Run ``edit`` in one transaction and raise unless Revit committed it.

        ``revit.Transaction`` rolls a failed commit back without telling the
        caller, which would report an edit that never happened as applied.
        """
        transaction = DB.Transaction(self.doc, name)
        transaction.Start()
        try:
            edit()
            status = transaction.Commit()
        except Exception:
            if transaction.GetStatus() == DB.TransactionStatus.Started:
                transaction.RollBack()
            raise
        finally:
            transaction.Dispose()
        if status != DB.TransactionStatus.Committed:
            raise ValueError("Revit did not commit the change")

    def _finish(self, view, request_id, ok, message=None):
        self.bridge.reply(request_id, ok, message)
        self._send("box", self._view_payload(view))
        if ok:
            self.on_box_changed()

    def _on_apply_box(self, payload, request_id):
        view = self._active_view(payload)
        self._applied_revision = payload.get("revision")
        try:
            self._write_box(view, payload["box"])
        except Exception as ex:
            self._finish(view, request_id, False, str(ex))
            return
        self._finish(view, request_id, True)

    def _on_apply_view_range(self, payload, request_id):
        view = self._active_view(payload)
        self._applied_revision = payload.get("revision")
        try:
            self._write_view_range(view, payload["planes"])
        except Exception as ex:
            self._finish(view, request_id, False, self._view_range_problem(ex))
            return
        self._finish(view, request_id, True)

    def _write_view_range(self, view, planes):
        if not has_view_range(view):
            raise ValueError("The view has no view range")
        template = controlling_template_name(view)
        if template:
            raise ValueError(self.get_string("PreviewRangeTemplate").format(template))
        changes = dict((plane, float(z) + self.origin.Z) for plane, z in planes.items())
        view_range = build_view_range(view, changes)
        self._commit_edit("Adjust View Range", lambda: view.SetViewRange(view_range))

    def _view_range_problem(self, error):
        if isinstance(error, ViewRangeError) and error.reason == "order":
            higher, lower = (
                self.get_string(RANGE_PLANE_STRINGS[plane]) for plane in error.planes
            )
            return self.get_string("PreviewRangeInvalid").format(higher, lower)
        return str(error)

    def _on_use_scope_box(self, payload, request_id):
        view = self._active_view(payload)
        scope_box = self.doc.GetElement(get_elementid_from_value(int(payload["id"])))
        if scope_box is None:
            self._finish(view, request_id, False, "The scope box no longer exists")
            return
        if isinstance(view, DB.View3D):
            box = scope_box_to_bounding_box(scope_box)
            if box is None:
                self._finish(view, request_id, False, "The scope box has no geometry")
                return

            def assign_section_box():
                view.SetSectionBox(box)
                view.IsSectionBoxActive = True

            try:
                self._commit_edit(
                    "Create Section Box from Scope Box", assign_section_box
                )
            except Exception as ex:
                self._finish(view, request_id, False, str(ex))
                return
        else:
            parameter = view.get_Parameter(
                DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP
            )
            if parameter is None or parameter.IsReadOnly:
                self._finish(view, request_id, False, "The view has no scope box slot")
                return

            def assign_scope_box():
                view.CropBoxActive = True
                parameter.Set(scope_box.Id)

            try:
                self._commit_edit("Assign Scope Box to View", assign_scope_box)
            except Exception as ex:
                self._finish(view, request_id, False, str(ex))
                return
        self._finish(view, request_id, True)

    def _on_fit_visible(self, payload, request_id):
        view = self._active_view(payload)
        info = get_box_info(view, self.datafilename)
        if info is None:
            self._finish(view, request_id, False, "The view has no box")
            return
        inverse = info["transform"].Inverse
        local = []
        for element in get_visible_model_elements(view):
            bbox = element.get_BoundingBox(None)
            if bbox is not None:
                local.extend(
                    inverse.OfPoint(corner)
                    for corner in box_corners(bbox.Min, bbox.Max)
                )
        if not local:
            self._finish(view, request_id, False, "No visible elements")
            return
        padding = float(payload.get("padding", 1.0))
        data = box_payload(info["box"], self.origin)
        data["min"] = [
            min(p.X for p in local) - padding,
            min(p.Y for p in local) - padding,
            min(p.Z for p in local) - padding,
        ]
        data["max"] = [
            max(p.X for p in local) + padding,
            max(p.Y for p in local) + padding,
            max(p.Z for p in local) + padding,
        ]
        try:
            self._write_box(view, data)
        except Exception as ex:
            self._finish(view, request_id, False, str(ex))
            return
        self._finish(view, request_id, True)

    def _store(self):
        try:
            data = script.load_data(BOOKMARK_SLOT)
        except Exception:
            data = None
        return data if isinstance(data, dict) else {"3d": [], "crop": {}}

    def _bookmark_list(self, data, view, kind):
        if kind == "3d":
            return data.setdefault("3d", [])
        return data.setdefault("crop", {}).setdefault(view.UniqueId, [])

    def _bookmark_entries(self, view, kind):
        data = self._store()
        entries = self._bookmark_list(data, view, kind)
        return [{"id": entry["id"], "name": entry["name"]} for entry in entries]

    def _kind(self, view):
        return "3d" if isinstance(view, DB.View3D) else "crop"

    def _on_bookmark_save(self, payload, request_id):
        view = self._active_view(payload)
        data = self._store()
        box = dict(payload["box"])
        box["origin"] = [
            box["origin"][0] + self.origin.X,
            box["origin"][1] + self.origin.Y,
            box["origin"][2] + self.origin.Z,
        ]
        self._bookmark_list(data, view, self._kind(view)).append(
            {"id": uuid.uuid4().hex, "name": payload["name"], "box": box}
        )
        script.store_data(BOOKMARK_SLOT, data)
        self._finish(view, request_id, True)

    def _find_bookmark(self, payload, view):
        data = self._store()
        for entry in self._bookmark_list(data, view, self._kind(view)):
            if entry["id"] == payload["id"]:
                return data, entry
        return data, None

    def _on_bookmark_apply(self, payload, request_id):
        view = self._active_view(payload)
        _, entry = self._find_bookmark(payload, view)
        if entry is None:
            self._finish(view, request_id, False, "Unknown bookmark")
            return
        box = dict(entry["box"])
        box["origin"] = [
            box["origin"][0] - self.origin.X,
            box["origin"][1] - self.origin.Y,
            box["origin"][2] - self.origin.Z,
        ]
        try:
            self._write_box(view, box)
        except Exception as ex:
            self._finish(view, request_id, False, str(ex))
            return
        self._finish(view, request_id, True)

    def _on_bookmark_rename(self, payload, request_id):
        view = self._active_view(payload)
        data, entry = self._find_bookmark(payload, view)
        if entry is not None:
            entry["name"] = payload["name"]
            script.store_data(BOOKMARK_SLOT, data)
        self._finish(view, request_id, entry is not None)

    def _on_bookmark_delete(self, payload, request_id):
        view = self._active_view(payload)
        data, entry = self._find_bookmark(payload, view)
        if entry is not None:
            self._bookmark_list(data, view, self._kind(view)).remove(entry)
            script.store_data(BOOKMARK_SLOT, data)
        self._finish(view, request_id, entry is not None)


def _work_area():
    return System.Windows.SystemParameters.WorkArea
