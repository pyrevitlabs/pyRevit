# -*- coding: utf-8 -*-
"""Interactive WebView2 report for the Diagnose Invisibility tool.

Renders the diagnosis as a single-page app inside the command's output window
(``report.js``, ``report.css``, ``viewer3d.js``) and keeps it live: buttons on
the page post messages through ``invisibility_bridge``; handlers here run them
in Revit API context and push refreshed state back to the page.

Page -> Python actions: ``select``, ``zoom``, ``open_view``, ``fix``,
``fix_all``, ``recheck``, ``scene``.
Python -> page events: ``view`` (refreshed view section), ``result``
(outcome of a request), ``scene`` (3D preview data), ``error``.
"""

import io
import json
import os
import uuid

from pyrevit import DB, HOST_APP, script
from pyrevit.framework import List

import invisibility_fixes as fixes
import invisibility_scene as scene
from invisibility_bridge import WebViewBridge
from invisibility_checks import collect_visible_ids, diagnose, id_value, t

logger = script.get_logger()

_BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
_ASSETS = ("viewer3d.js", "report.js")
_STYLESHEET = "report.css"

_ELEMENT_SCOPED_ACTIONS = frozenset(
    ("unhide_element", "expand_section_box", "extend_view_range", "raise_cut_plane")
)

_UI_STRINGS = {
    "title": ("report_title", "Visibility Diagnosis"),
    "subtitle": ("ui_subtitle", "{0} element(s) in {1} view(s)"),
    "visible": ("ui_visible", "Visible"),
    "hidden": ("ui_hidden", "Not visible"),
    "search": ("ui_search", "Filter by name, category or id"),
    "showVisible": ("ui_show_visible", "Show visible elements"),
    "showContext": ("ui_show_context", "Show context notes"),
    "copyMarkdown": ("ui_copy_markdown", "Copy as Markdown"),
    "copied": ("ui_copied", "Report copied to clipboard"),
    "recheck": ("ui_recheck", "Re-check"),
    "rechecked": ("ui_rechecked", "Diagnosis refreshed"),
    "zoom": ("ui_zoom", "Show"),
    "openView": ("ui_open_view", "Open view"),
    "preview3d": ("ui_preview_3d", "3D preview"),
    "fixAll": ("ui_fix_all", "Fix all ({0})"),
    "fixed": ("ui_fixed", "Applied: {0}"),
    "fixFailed": ("ui_fix_failed", "Could not apply fix: {0}"),
    "context": ("ui_context", "Context"),
    "overview": ("ui_overview", "Overview"),
    "noMatch": ("ui_no_match", "No elements match the current filter."),
    "loadingScene": ("ui_loading_scene", "Building 3D preview..."),
    "sceneEmpty": ("ui_scene_empty", "None of these elements has geometry to preview."),
    "sceneHelp": (
        "ui_scene_help",
        "Drag to orbit, Shift+drag or right-drag to pan, wheel to zoom,"
        " double-click to frame. Click an element to find its card.",
    ),
    "layerHidden": ("ui_layer_hidden", "Not visible"),
    "layerVisible": ("ui_layer_visible", "Visible"),
    "layerClip": ("ui_layer_clip", "Crop / section box"),
    "layerPlanes": ("ui_layer_planes", "View range / cut planes"),
    "cameraView": ("ui_camera_view", "Revit view"),
    "cameraTop": ("ui_camera_top", "Top"),
    "cameraIso": ("ui_camera_iso", "Iso"),
    "approx": ("ui_approx", "shown as bounding box"),
    "template": ("ui_template", "Template: {0}"),
    "bridgeOffline": (
        "ui_bridge_offline",
        "Interactive actions are unavailable in this window.",
    ),
    "inTemplate": (
        "ui_in_template_hint",
        "Changes the view template, which affects every view using it.",
    ),
}


_CODE_LABELS = {
    "workset_hidden": "Workset",
    "workset_closed": "Workset closed",
    "workset_default_hidden": "Workset default",
    "phase_filter": "Phase",
    "design_option": "Design option",
    "category_hidden": "Category",
    "subcategory_hidden": "Subcategory",
    "element_hidden": "Hidden",
    "temporary_hidden": "Temporary",
    "view_filter": "Filter",
    "section_box": "Section box",
    "crop_box": "Crop",
    "behind_cut_plane": "Cut plane",
    "far_clip": "Far clip",
    "viewrange_above": "Above top",
    "viewrange_below": "Below range",
    "above_cut_plane": "Above cut",
    "view_specific": "View-specific",
    "view_template": "Template",
    "view_discipline": "Discipline",
    "unknown": "Unknown",
}


def _read_asset(name):
    with io.open(os.path.join(_BUNDLE_DIR, name), encoding="utf-8") as asset:
        return asset.read()


def format_element_label(element):
    """Return "Category - Name (id N)" for display."""
    try:
        category_name = element.Category.Name if element.Category else "?"
    except Exception:
        category_name = "?"
    try:
        name = element.Name
    except Exception:
        name = ""
    element_id = id_value(element.Id)
    if name:
        return "{} - {} (id {})".format(category_name, name, element_id)
    return "{} (id {})".format(category_name, element_id)


def _fix_key(element_id, fix):
    key = json.dumps(fix, sort_keys=True)
    if fix.get("action") in _ELEMENT_SCOPED_ACTIONS:
        key += "@{}".format(element_id)
    return key


class DiagnosisSession(object):
    """State behind one interactive report.

    Holds element and view ids, never API objects, and resolves them on every
    request: the user can delete elements, close views or undo fixes while
    the report stays open.

    Lifecycle: created and shown by the command; afterwards it lives only
    through the bridge's event subscriptions and ends when the output window
    closes.
    """

    def __init__(self, output, doc, elements, views):
        self.output = output
        self.doc = doc
        self.element_ids = [e.Id for e in elements]
        self.view_ids = [v.Id for v in views]
        self.channel = "invisibility-{}".format(uuid.uuid4().hex)
        self.root_id = "invisibility-app-{}".format(uuid.uuid4().hex[:8])
        self.bridge = WebViewBridge(output, self.channel)

    def _elements(self):
        resolved = []
        for element_id in self.element_ids:
            element = self.doc.GetElement(element_id)
            if element is not None:
                resolved.append(element)
        return resolved

    def _view(self, view_id_value):
        view_id = DB.ElementId(int(view_id_value))
        if view_id not in self.view_ids:
            raise fixes.FixError("Unknown view {}".format(view_id_value))
        view = self.doc.GetElement(view_id)
        if view is None:
            raise fixes.FixError(t("fix_error_missing", "The target no longer exists"))
        return view

    def _element(self, element_id_value):
        element = self.doc.GetElement(DB.ElementId(int(element_id_value)))
        if element is None:
            raise fixes.FixError(t("fix_error_missing", "The target no longer exists"))
        return element

    def _uidoc(self):
        uidoc = HOST_APP.uiapp.ActiveUIDocument
        if uidoc is None or not uidoc.Document.Equals(self.doc):
            raise fixes.FixError(
                t(
                    "error_document_inactive",
                    "Switch to the document '{}' first",
                ).format(self.doc.Title)
            )
        return uidoc

    def view_payload(self, view):
        """Diagnose every element in ``view`` and describe it for the page."""
        visible_ids = collect_visible_ids(view)
        template_id = view.ViewTemplateId
        template = (
            self.doc.GetElement(template_id)
            if template_id != DB.ElementId.InvalidElementId
            else None
        )
        elements = []
        for element in self._elements():
            try:
                findings = diagnose(element, view, visible_ids)
                error = None
            except Exception as ex:
                logger.debug("Diagnosis failed: %s", ex)
                findings, error = [], str(ex)
            entries = []
            for finding in findings:
                entry = {
                    "code": finding.code,
                    "message": finding.message,
                    "informational": finding.informational,
                    "fix": None,
                }
                if finding.fix:
                    try:
                        entry["fix"] = dict(fixes.describe(view, finding.fix))
                        entry["fix"]["descriptor"] = finding.fix
                    except Exception as ex:
                        logger.debug("Cannot describe fix: %s", ex)
                entries.append(entry)
            category = element.Category
            elements.append(
                {
                    "id": id_value(element.Id),
                    "label": format_element_label(element),
                    "category": category.Name if category else "",
                    "visible": not any(not f.informational for f in findings),
                    "findings": entries,
                    "error": error,
                }
            )
        return {
            "id": id_value(view.Id),
            "name": view.Name,
            "type": str(view.ViewType),
            "template": template.Name if template else None,
            "elements": elements,
        }

    def payload(self):
        """Return the complete report state passed to the page's ``mount``."""
        views = [self.doc.GetElement(view_id) for view_id in self.view_ids]
        return {
            "channel": self.channel,
            "bridge": self.bridge.attached,
            "document": self.doc.Title,
            "strings": dict(
                (name, t(key, default)) for name, (key, default) in _UI_STRINGS.items()
            ),
            "codes": dict(
                (code, t("code_" + code, default))
                for code, default in _CODE_LABELS.items()
            ),
            "views": [self.view_payload(v) for v in views if v is not None],
        }

    def show(self):
        """Render the report and start listening for page messages.

        Must run in the command, in API context; it blocks until the output
        document is ready.
        """
        if self.bridge.attach():
            for action, handler in (
                ("select", self._on_select),
                ("zoom", self._on_zoom),
                ("open_view", self._on_open_view),
                ("fix", self._on_fix),
                ("fix_all", self._on_fix_all),
                ("recheck", self._on_recheck),
                ("scene", self._on_scene),
            ):
                self.bridge.on(action, handler)
        self.output.set_title(t("report_title", "Visibility Diagnosis"))
        self.output.add_style(_read_asset(_STYLESHEET))
        for asset in _ASSETS:
            self.output.inject_script(_read_asset(asset))
        self.output.inject_to_body("div", "", {"id": self.root_id})
        self.output.inject_script(
            "window.pyRevitInvisibility.mount({}, {});".format(
                json.dumps(self.root_id), json.dumps(self.payload())
            ),
            body=True,
        )

    def _reply(self, request_id, ok, message=None):
        self.bridge.send(
            "result", {"requestId": request_id, "ok": ok, "message": message}
        )

    def _push_views(self, view_ids=None):
        for view_id in view_ids or self.view_ids:
            view = self.doc.GetElement(view_id)
            if view is not None:
                self.bridge.send("view", self.view_payload(view))

    def _ids(self, payload):
        return List[DB.ElementId](
            [self._element(value).Id for value in payload.get("elementIds", [])]
        )

    def _on_select(self, payload, request_id):
        self._uidoc().Selection.SetElementIds(self._ids(payload))
        self._reply(request_id, True)

    def _on_zoom(self, payload, request_id):
        uidoc = self._uidoc()
        ids = self._ids(payload)
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)
        self._reply(request_id, True)

    def _on_open_view(self, payload, request_id):
        fixes.open_view(self._uidoc(), self._view(payload["viewId"]))
        self._reply(request_id, True)

    def _on_fix(self, payload, request_id):
        view = self._view(payload["viewId"])
        element = self._element(payload["elementId"])
        fix = payload["fix"]
        try:
            fixes.apply(self._uidoc(), view, element, fix)
        except fixes.FixError as ex:
            self._reply(request_id, False, str(ex))
            return
        self._push_views()
        self._reply(request_id, True, fixes.describe(view, fix)["label"])

    def _on_fix_all(self, payload, request_id):
        """Apply every distinct non-navigation fix in a view as one undo step."""
        view = self._view(payload["viewId"])
        uidoc = self._uidoc()
        visible_ids = collect_visible_ids(view)
        pending = []
        seen = set()
        for element in self._elements():
            for finding in diagnose(element, view, visible_ids):
                fix = finding.fix
                if (
                    not fix
                    or finding.informational
                    or fix.get("action") in fixes.NAVIGATION_ACTIONS
                ):
                    continue
                key = _fix_key(id_value(element.Id), fix)
                if key not in seen:
                    seen.add(key)
                    pending.append((element, fix))
        label = t("ui_fix_all", "Fix all ({0})").replace("{0}", str(len(pending)))
        group = DB.TransactionGroup(
            self.doc, "{}: {}".format(t("report_title", "Visibility Diagnosis"), label)
        )
        group.Start()
        errors = []
        for element, fix in pending:
            try:
                fixes.apply(uidoc, view, element, fix)
            except fixes.FixError as ex:
                errors.append(str(ex))
        group.Assimilate()
        self._push_views()
        self._reply(request_id, not errors, "; ".join(errors) or label)

    def _on_recheck(self, payload, request_id):
        self._push_views()
        self._reply(request_id, True)

    def _on_scene(self, payload, request_id):
        view = self._view(payload["viewId"])
        visible_ids = collect_visible_ids(view)
        states = []
        for element in self._elements():
            findings = diagnose(element, view, visible_ids)
            states.append((element, not any(not f.informational for f in findings)))
        data = scene.build_scene(view, states, format_element_label)
        if data is None:
            self.bridge.send("scene", {"viewId": id_value(view.Id), "meshes": []})
        else:
            self.bridge.send("scene", raw_payload=scene.scene_to_json(data))
        self._reply(request_id, True)


def show_report(output, elements, views):
    """Diagnose ``elements`` in ``views`` and show the interactive report.

    Returns:
        (DiagnosisSession): the live session (kept alive by its bridge).
    """
    session = DiagnosisSession(output, elements[0].Document, elements, views)
    session.show()
    return session
