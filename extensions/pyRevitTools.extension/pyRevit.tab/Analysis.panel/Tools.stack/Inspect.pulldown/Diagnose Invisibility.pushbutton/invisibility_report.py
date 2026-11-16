# -*- coding: utf-8 -*-
"""Interactive WebView2 report for the Diagnose Invisibility tool.

Renders the diagnosis as a single-page app inside the command's output window
(``report.js``, ``report.css``, ``viewer3d.js``) and keeps it live: buttons on
the page post messages through ``output.on_message``; handlers here run them
in Revit API context and push refreshed state back to the page.

Page -> Python messages are ``{channel, action, payload, requestId}``; messages
from other channels (e.g. a previous run printed into the same window) are
ignored.
Page -> Python actions: ``select``, ``zoom``, ``open_view``, ``fix``,
``fix_all``, ``recheck``, ``scene``, ``ghost``, ``add_selection``,
``add_pick``, ``add_views``, ``remove_element``, ``remove_view``,
``set_hidden``, ``add_ids``, ``reveal``, ``reveal_refresh``, ``reveal_filter``,
``reveal_select``, ``reveal_follow``, ``reveal_focus``, ``reveal_inspect``,
``reveal_add_selection``.
Python -> page events: ``view`` (refreshed view section), ``state`` (the
element and view lists changed), ``reveal`` (overlay built or removed),
``inspect`` (diagnosis of one overlay element), ``result`` (outcome of a
request), ``scene`` (3D preview data), ``error``.
"""

import io
import json
import os
import uuid

from pyrevit import DB, HOST_APP, forms, revit, script
from pyrevit.compat import IRONPY, get_elementid_from_value_func
from pyrevit.framework import List
from pyrevit.revit import events

import invisibility_fixes as fixes
import invisibility_scene as scene
from invisibility_ghost import GhostPreview, zoom_to
from invisibility_reveal import (
    REASON_COLORS,
    SUPPORTED_VIEW_TYPES,
    RevealPreview,
    color_hex,
)
from invisibility_checks import collect_visible_ids, diagnose, id_value, t

logger = script.get_logger()

get_elementid_from_value = get_elementid_from_value_func()

_WEBVIEW2_ENGINE = "WebView2/Chromium"
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
    "showContextHint": (
        "ui_show_context_hint",
        "Also list notes that may explain a hidden element but are not"
        " confirmed causes, such as an applied view template or a view"
        " discipline. Included in Copy as Markdown when shown.",
    ),
    "speculativeHint": (
        "ui_speculative_hint",
        "Possible cause only: Revit could not tell which subcategories this"
        " element draws with here. Not included in Fix all.",
    ),
    "ghost": ("ui_ghost", "Ghost in Revit"),
    "ghostHint": (
        "ui_ghost_hint",
        "Draw this element's geometry in Revit's views, even while it is"
        " hidden, and zoom the diagnosed view to it. Click again to remove.",
    ),
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
        " double-click to frame. Click an element to find its card, right-click"
        " it for more actions.",
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
    "addSelection": ("ui_add_selection", "Add selection"),
    "addSelectionHint": (
        "ui_add_selection_hint",
        "Add the elements currently selected in Revit to this report.",
    ),
    "pickElements": ("ui_pick_elements", "Pick elements"),
    "addViews": ("ui_add_views", "Add views"),
    "removeElement": ("ui_remove_element", "Remove this element from the report"),
    "removeView": ("ui_remove_view", "Remove this view from the report"),
    "selectAll": ("ui_select_all", "Select all"),
    "selectedCount": ("ui_selected_count", "{0} selected"),
    "clearSelection": ("ui_clear_selection", "Clear selection"),
    "selectForHide": (
        "ui_select_for_hide",
        "Select this element for hiding or unhiding",
    ),
    "hideInViews": ("ui_hide_in_views", "Hide in views..."),
    "unhideInViews": ("ui_unhide_in_views", "Unhide in views..."),
    "hideDialogTitle": ("ui_hide_dialog_title", "Hide {0} element(s) in:"),
    "unhideDialogTitle": ("ui_unhide_dialog_title", "Unhide {0} element(s) in:"),
    "apply": ("ui_apply", "Apply"),
    "cancel": ("ui_cancel", "Cancel"),
    "noViewTicked": ("ui_no_view_ticked", "Tick at least one view."),
    "emptyState": (
        "ui_empty_state",
        "Nothing to diagnose yet. Add elements and views.",
    ),
    "reloadBlocked": (
        "ui_reload_blocked",
        "Reloading would erase this report. Use Re-check instead.",
    ),
    "reveal": ("ui_reveal", "Reveal hidden"),
    "revealHint": (
        "ui_reveal_hint",
        "Draw every element that is hidden in this view's screen area in Revit,"
        " in one color per reason. Click again to remove.",
    ),
    "revealRefresh": ("ui_reveal_refresh", "Refresh overlay"),
    "revealFollow": ("ui_reveal_follow", "Follow viewport"),
    "revealSelect": ("ui_reveal_select", "Select"),
    "revealSummary": ("ui_reveal_summary", "{0} hidden element(s) drawn"),
    "revealLeftOut": (
        "ui_reveal_left_out",
        "{0} more not drawn. Zoom in to see them.",
    ),
    "revealSmallSkipped": (
        "ui_reveal_skipped",
        "{0} tiny element(s) skipped.",
    ),
    "revealNone": ("ui_reveal_none", "Nothing is hidden in the visible area."),
    "revealSearch": (
        "ui_reveal_search",
        "Filter by name, category, level, mark or id",
    ),
    "revealAllLevels": ("ui_reveal_all_levels", "All levels"),
    "revealClearFilter": ("ui_reveal_clear_filter", "Clear filter"),
    "revealSelectShown": ("ui_reveal_select_shown", "Select shown"),
    "revealFiltered": ("ui_reveal_filtered", "Drawing {0} of {1} in Revit"),
    "revealMoreRows": (
        "ui_reveal_more_rows",
        "{0} more. Narrow the filter to list them.",
    ),
    "revealRowHint": (
        "ui_reveal_row_hint",
        "Show this element in Revit and explain why it is not visible."
        " Ctrl-click or Shift-click to select several.",
    ),
    "revealAddSelection": ("ui_reveal_add_selection", "Add Revit selection"),
    "revealAddSelectionHint": (
        "ui_reveal_add_selection_hint",
        "Diagnose the elements selected in Revit in this view and draw them,"
        " whatever their size. Select the missing element where it is visible,"
        " for example in another view or a schedule.",
    ),
    "revealAddToReport": ("ui_reveal_add_to_report", "Add to report"),
    "menuShowCard": ("ui_menu_show_card", "Go to card"),
    "menuFrame": ("ui_menu_frame", "Frame in 3D"),
    "menuZoom": ("ui_menu_zoom", "Show in Revit"),
    "menuSelect": ("ui_menu_select", "Select in Revit"),
    "menuRemove": ("ui_menu_remove", "Remove from report"),
    "revealSearchAll": ("ui_reveal_search_all", "Evaluate matching elements"),
    "revealSearchAllHint": (
        "ui_reveal_search_all_hint",
        "Diagnose every element that matches the filter, not only the biggest"
        " ones the time budget reached. Searches category, type, level, mark"
        " and id.",
    ),
    "revealScoped": (
        "ui_reveal_scoped",
        "Only elements matching the filter were evaluated. Refresh the overlay"
        " to evaluate all.",
    ),
    "revealColumns": (
        "ui_reveal_columns",
        "Reason|Category|Type|Level|Mark|Id",
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
    "view_type": "View type",
    "detail_level": "Detail level",
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
    key = json.dumps(fix, sort_keys=True, ensure_ascii=False)
    if fix.get("action") in _ELEMENT_SCOPED_ACTIONS:
        key += "@{}".format(element_id)
    return key


class DiagnosisSession(object):
    """State behind one interactive report.

    Holds element and view ids, never API objects, and resolves them on every
    request: the user can delete elements, close views or undo fixes while
    the report stays open.

    Lifecycle: created and shown by the command; afterwards it lives only
    through its output window subscriptions and ends when the output window
    closes.

    Important:
        Handlers outlive the command, so the bundle must run on a persistent
        engine; a cleaned-up engine would leave dangling callbacks.
    """

    def __init__(self, output, doc, elements, views, reveal=False):
        self.output = output
        self.reveal_on_start = reveal
        self.doc = doc
        self.element_ids = [e.Id for e in elements]
        self.view_ids = [v.Id for v in views]
        self.channel = "invisibility-{}".format(uuid.uuid4().hex)
        self.root_id = "invisibility-app-{}".format(uuid.uuid4().hex[:8])
        self.interactive = False
        self._handlers = {}
        self.ghost = GhostPreview(doc)
        self.reveal = RevealPreview(doc)

    def _elements(self):
        resolved = []
        for element_id in self.element_ids:
            element = self.doc.GetElement(element_id)
            if element is not None:
                resolved.append(element)
        return resolved

    def _view(self, view_id_value):
        view_id = get_elementid_from_value(int(view_id_value))
        if view_id not in self.view_ids:
            raise fixes.FixError("Unknown view {}".format(view_id_value))
        view = self.doc.GetElement(view_id)
        if view is None:
            raise fixes.FixError(t("fix_error_missing", "The target no longer exists"))
        return view

    def _element(self, element_id_value):
        element = self.doc.GetElement(get_elementid_from_value(int(element_id_value)))
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

    def element_payload(self, element, view, visible_ids):
        """Diagnose ``element`` in ``view`` and describe it for the page."""
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
                "speculative": finding.speculative,
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
        return {
            "id": id_value(element.Id),
            "label": format_element_label(element),
            "category": category.Name if category else "",
            "visible": not any(not f.informational for f in findings),
            "findings": entries,
            "error": error,
        }

    def view_payload(self, view):
        """Diagnose every element in ``view`` and describe it for the page."""
        visible_ids = collect_visible_ids(view)
        template_id = view.ViewTemplateId
        template = (
            self.doc.GetElement(template_id)
            if template_id != DB.ElementId.InvalidElementId
            else None
        )
        elements = [
            self.element_payload(element, view, visible_ids)
            for element in self._elements()
        ]
        return {
            "id": id_value(view.Id),
            "name": view.Name,
            "type": str(view.ViewType),
            "template": template.Name if template else None,
            "elements": elements,
        }

    def state(self):
        """Return the element count and the diagnosis of every report view."""
        views = [self.doc.GetElement(view_id) for view_id in self.view_ids]
        return {
            "elementCount": len(self.element_ids),
            "elementIds": [id_value(element_id) for element_id in self.element_ids],
            "views": [self.view_payload(v) for v in views if v is not None],
        }

    def payload(self):
        """Return the complete report state passed to the page's ``mount``."""
        data = {
            "channel": self.channel,
            "bridge": self.interactive,
            "document": self.doc.Title,
            "revealColors": dict((code, color_hex(code)) for code in REASON_COLORS),
            "autoReveal": id_value(self.view_ids[0]) if self.reveal_on_start else None,
            "strings": dict(
                (name, t(key, default)) for name, (key, default) in _UI_STRINGS.items()
            ),
            "codes": dict(
                (code, t("code_" + code, default))
                for code, default in _CODE_LABELS.items()
            ),
        }
        data.update(self.state())
        return data

    def show(self):
        """Render the report and start listening for page messages.

        Must run in the command, in API context. Falls back to a read-only
        report when the output window cannot receive page messages.
        """
        if self.output.on_message(self._on_page_message):
            self.interactive = True
            for action, handler in (
                ("select", self._on_select),
                ("zoom", self._on_zoom),
                ("open_view", self._on_open_view),
                ("fix", self._on_fix),
                ("fix_all", self._on_fix_all),
                ("recheck", self._on_recheck),
                ("scene", self._on_scene),
                ("ghost", self._on_ghost),
                ("add_selection", self._on_add_selection),
                ("add_pick", self._on_add_pick),
                ("add_views", self._on_add_views),
                ("remove_element", self._on_remove_element),
                ("remove_view", self._on_remove_view),
                ("set_hidden", self._on_set_hidden),
                ("reveal", self._on_reveal),
                ("reveal_refresh", self._on_reveal_refresh),
                ("reveal_filter", self._on_reveal_filter),
                ("reveal_select", self._on_reveal_select),
                ("reveal_follow", self._on_reveal_follow),
                ("reveal_focus", self._on_reveal_focus),
                ("reveal_inspect", self._on_reveal_inspect),
                ("reveal_add_selection", self._on_reveal_add_selection),
                ("add_ids", self._on_add_ids),
            ):
                self._handlers[action] = handler
            self.output.window.Closed += self._on_window_closed
        self.output.set_title(t("report_title", "Visibility Diagnosis"))
        self.output.add_style(_read_asset(_STYLESHEET))
        for asset in _ASSETS:
            self.output.inject_script(_read_asset(asset))
        self.output.inject_to_body("div", "", {"id": self.root_id})
        self.output.inject_script(
            "window.pyRevitInvisibility.mount({}, {});".format(
                json.dumps(self.root_id),
                json.dumps(self.payload(), ensure_ascii=False),
            ),
            body=True,
        )

    def _on_page_message(self, message):
        if not isinstance(message, dict) or message.get("channel") != self.channel:
            return
        action = message.get("action")
        handler = self._handlers.get(action)
        if handler is None:
            logger.debug("No handler for action '%s'", action)
            return
        request_id = message.get("requestId")
        try:
            handler(message.get("payload") or {}, request_id)
        except Exception as ex:
            logger.debug("Handler '%s' failed: %s", action, ex)
            self._send(
                "error",
                {"action": action, "requestId": request_id, "message": str(ex)},
            )

    def _on_window_closed(self, sender, args):
        self.interactive = False
        self._close_ghosts()

    def _send(self, event, payload=None, raw_payload=None):
        """Post ``{channel, event, payload}`` to the page.

        ``raw_payload`` is pre-encoded JSON used instead of ``payload``, for
        large bodies serialized by a faster custom encoder than ``json.dumps``.
        """
        if raw_payload is None:
            self.output.post_message(
                {"channel": self.channel, "event": event, "payload": payload}
            )
            return
        self.output.window.PostWebMessage(
            '{{"channel":{},"event":{},"payload":{}}}'.format(
                json.dumps(self.channel), json.dumps(event), raw_payload
            )
        )

    def _reply(self, request_id, ok, message=None):
        self._send("result", {"requestId": request_id, "ok": ok, "message": message})

    def _push_views(self, view_ids=None):
        for view_id in view_ids or self.view_ids:
            view = self.doc.GetElement(view_id)
            if view is not None:
                self._send("view", self.view_payload(view))

    def _push_state(self):
        self._send("state", self.state())

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
        """Apply one fix, rebuilt from a fresh diagnosis of the element.

        The page only selects which fix to run; its id arguments are never
        trusted. Template-owned fixes ask for confirmation first.
        """
        view = self._view(payload["viewId"])
        element = self._element(payload["elementId"])
        requested_key = _fix_key(id_value(element.Id), payload["fix"])
        fix = next(
            (
                finding.fix
                for finding in diagnose(element, view, collect_visible_ids(view))
                if finding.fix
                and _fix_key(id_value(element.Id), finding.fix) == requested_key
            ),
            None,
        )
        if fix is None:
            self._reply(
                request_id,
                False,
                t("fix_stale", "This fix no longer applies. Recheck the view."),
            )
            return
        description, error = _try_describe_fix(view, fix)
        if error:
            self._reply(request_id, False, error)
            return
        template_name = description["template"]
        if template_name and not forms.alert(
            t(
                "confirm_template_fix",
                "This changes view template '{}' and every view using it.",
            ).format(template_name),
            yes=True,
            no=True,
        ):
            self._reply(request_id, False, t("fix_cancelled", "Cancelled."))
            return
        try:
            fixes.apply(self._uidoc(), view, element, fix)
        except fixes.FixError as ex:
            self._reply(request_id, False, str(ex))
            return
        self._push_views()
        self._reply(request_id, True, description["label"])

    def _on_fix_all(self, payload, request_id):
        """Apply every distinct confirmed fix in a view as one undo step.

        Skips informational, speculative and navigation findings. The
        transaction group is always closed, so fixes that succeeded stay
        committed even when a later one fails.
        """
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
                    or finding.speculative
                    or fix.get("action") in fixes.NAVIGATION_ACTIONS
                ):
                    continue
                key = _fix_key(id_value(element.Id), fix)
                if key not in seen:
                    seen.add(key)
                    pending.append((element, fix))
        errors = []
        described = []
        templates = set()
        for element, fix in pending:
            description, error = _try_describe_fix(view, fix)
            if error:
                errors.append(error)
                continue
            described.append((element, fix))
            if description["template"]:
                templates.add(description["template"])
        pending = described
        templates = sorted(templates)
        label = t("ui_fix_all", "Fix all ({0})").replace("{0}", str(len(pending)))
        message = (
            t("confirm_fix_all", "Apply {0} fixes to '{1}'?")
            .replace("{0}", str(len(pending)))
            .replace("{1}", view.Name)
        )
        if templates:
            message += "\n" + t(
                "confirm_fix_all_templates",
                "View templates changed for every view using them: {}",
            ).format(", ".join(templates))
        if pending and not forms.alert(message, yes=True, no=True):
            errors.append(t("fix_cancelled", "Cancelled."))
            self._reply(request_id, False, "; ".join(errors))
            return
        group = DB.TransactionGroup(
            self.doc, "{}: {}".format(t("report_title", "Visibility Diagnosis"), label)
        )
        group.Start()
        try:
            for element, fix in pending:
                try:
                    fixes.apply(uidoc, view, element, fix)
                except Exception as ex:
                    errors.append(str(ex))
        finally:
            if group.HasStarted() and not group.HasEnded():
                group.Assimilate()
        self._push_views()
        self._reply(request_id, not errors, "; ".join(errors) or label)

    def _on_recheck(self, payload, request_id):
        self._push_views()
        self._reply(request_id, True)

    def _on_ghost(self, payload, request_id):
        shown = self.ghost.toggle(
            self._uidoc(),
            self._view(payload["viewId"]),
            self._element(payload["elementId"]),
        )
        self._reply(request_id, True, "on" if shown else "off")

    def _add_elements(self, elements, request_id):
        known = set(id_value(element_id) for element_id in self.element_ids)
        added = 0
        for element in elements:
            if (
                element is None
                or element.Category is None
                or isinstance(element, DB.ElementType)
                or id_value(element.Id) in known
            ):
                continue
            known.add(id_value(element.Id))
            self.element_ids.append(element.Id)
            added += 1
        if not added:
            self._reply(
                request_id, True, t("add_nothing_new", "No new elements to add.")
            )
            return
        self._push_state()
        self._reply(
            request_id,
            True,
            t("added_elements", "Added {0} element(s).").format(added),
        )

    def _on_add_selection(self, payload, request_id):
        selected = self._uidoc().Selection.GetElementIds()
        if not selected.Count:
            self._reply(
                request_id,
                True,
                t("add_no_selection", "Nothing is selected in Revit."),
            )
            return
        self._add_elements([self.doc.GetElement(i) for i in selected], request_id)

    def _on_add_pick(self, payload, request_id):
        self._uidoc()
        picked = revit.pick_elements(
            message=t("pick_prompt", "Select element(s) to diagnose")
        )
        self._add_elements(picked or [], request_id)

    def _on_add_views(self, payload, request_id):
        views = forms.select_views(
            title=t("select_view_title", "Select View"),
            button_name=t("add_views_button", "Add to report"),
            doc=self.doc,
            filterfunc=lambda view: view.Id not in self.view_ids,
        )
        if not views:
            self._reply(request_id, True)
            return
        self.view_ids.extend(view.Id for view in views)
        self._push_state()
        self._reply(
            request_id,
            True,
            t("added_views", "Added {0} view(s).").format(len(views)),
        )

    def _on_remove_element(self, payload, request_id):
        value = int(payload["elementId"])
        self.element_ids = [i for i in self.element_ids if id_value(i) != value]
        self.ghost.forget(value)
        self._push_state()
        self._reply(request_id, True)

    def _on_remove_view(self, payload, request_id):
        value = int(payload["viewId"])
        self.view_ids = [i for i in self.view_ids if id_value(i) != value]
        if self.reveal.view_id is not None and id_value(self.reveal.view_id) == value:
            self.reveal.close()
        self._push_state()
        self._reply(request_id, True)

    def _on_set_hidden(self, payload, request_id):
        """Hide or unhide chosen elements in chosen report views.

        Asks for confirmation with the exact counts first. Hiding is by
        element only; elements Revit cannot hide in a view, and view-specific
        elements owned by another view, are skipped silently.
        """
        hide = bool(payload.get("hide"))
        elements = [
            self.doc.GetElement(get_elementid_from_value(int(value)))
            for value in payload.get("elementIds", [])
        ]
        views = [self._view(value) for value in payload.get("viewIds", [])]
        plan = fixes.plan_visibility_change(
            [element for element in elements if element is not None], views, hide
        )
        if not plan:
            self._reply(
                request_id,
                True,
                t(
                    "hide_nothing",
                    "Nothing to change: the elements are already in that state,"
                    " cannot be hidden in these views, or belong to another view.",
                ),
            )
            return
        element_count = len(set(id_value(i) for _, ids in plan for i in ids))
        confirm_key, confirm_default = (
            ("confirm_hide", "Hide {0} element(s) in {1} view(s)?")
            if hide
            else ("confirm_unhide", "Unhide {0} element(s) in {1} view(s)?")
        )
        if not forms.alert(
            t(confirm_key, confirm_default).format(element_count, len(plan)),
            yes=True,
            no=True,
        ):
            self._reply(request_id, True, t("fix_cancelled", "Cancelled."))
            return
        transaction_key, transaction_default = (
            ("transaction_hide", "Hide in views")
            if hide
            else ("transaction_unhide", "Unhide in views")
        )
        applied, errors = fixes.apply_visibility_change(
            self.doc,
            plan,
            hide,
            "{}: {}".format(
                t("report_title", "Visibility Diagnosis"),
                t(transaction_key, transaction_default),
            ),
        )
        self._push_views()
        if not applied:
            self._reply(request_id, False, "; ".join(errors))
            return
        done_key, done_default = (
            ("hidden_summary", "Hid {0} element(s) in {1} view(s).")
            if hide
            else ("unhidden_summary", "Unhid {0} element(s) in {1} view(s).")
        )
        message = t(done_key, done_default).format(
            len(set(id_value(i) for _, ids in applied for i in ids)), len(applied)
        )
        if errors:
            message += " " + "; ".join(errors)
        self._reply(request_id, True, message)

    def _on_reveal(self, payload, request_id):
        view = self._view(payload["viewId"])
        view_id = id_value(view.Id)
        previous = self.reveal.view_id
        if not payload.get("on", True):
            self.reveal.close()
            self._send("reveal", {"viewId": view_id, "active": False})
            self._reply(request_id, True)
            return
        uidoc = self._uidoc()
        if view.ViewType not in SUPPORTED_VIEW_TYPES:
            self._reply(
                request_id,
                False,
                t(
                    "reveal_unsupported",
                    "The reveal overlay is not available in {} views.",
                ).format(self._view_type_label(view)),
            )
            return
        if previous is not None and id_value(previous) != view_id:
            self._send("reveal", {"viewId": id_value(previous), "active": False})
        self.reveal.show(uidoc, view, self._send_reveal)
        self._reply(request_id, True)

    def _send_reveal(self, summary):
        self._send("reveal", summary)

    def _view_type_label(self, view):
        return str(view.ViewType)

    def _on_reveal_refresh(self, payload, request_id):
        """Rebuild the overlay, optionally evaluating only a filter's matches."""
        self.reveal.refresh(self._uidoc(), payload.get("filter"))
        self._reply(request_id, True)

    def _on_reveal_filter(self, payload, request_id):
        self.reveal.set_code_visible(
            self._uidoc(), payload["code"], bool(payload.get("visible"))
        )
        self._reply(request_id, True)

    def _on_reveal_select(self, payload, request_id):
        ids = List[DB.ElementId](
            [
                get_elementid_from_value(value)
                for value in self.reveal.ids_for(payload["code"])
            ]
        )
        self._uidoc().Selection.SetElementIds(ids)
        self._reply(request_id, True)

    def _on_reveal_follow(self, payload, request_id):
        self.reveal.follow(bool(payload.get("on")))
        self._reply(request_id, True)

    def _on_reveal_focus(self, payload, request_id):
        """Draw only the listed elements in the overlay; null draws all."""
        self.reveal.set_focus(self._uidoc(), payload.get("ids"))
        self._reply(request_id, True)

    def _on_reveal_inspect(self, payload, request_id):
        """Diagnose one overlay element and send its card to the page.

        Zooms the view to the element unless the page asks not to, which it
        does when it only refreshes a card after a fix.
        """
        self._send_inspect(
            self._view(payload["viewId"]),
            self._element(payload["elementId"]),
            payload.get("zoom", True),
        )
        self._reply(request_id, True)

    def _send_inspect(self, view, element, zoom):
        uidoc = self._uidoc()
        if zoom and uidoc.ActiveView.Id == view.Id:
            zoom_to(uidoc, view, element)
        self._send(
            "inspect",
            {
                "viewId": id_value(view.Id),
                "element": self.element_payload(
                    element, view, collect_visible_ids(view)
                ),
            },
        )

    def _on_reveal_add_selection(self, payload, request_id):
        uidoc = self._uidoc()
        selected = [self.doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
        if not selected:
            self._reply(
                request_id,
                True,
                t("add_no_selection", "Nothing is selected in Revit."),
            )
            return
        added, already_visible = self.reveal.add_elements(uidoc, selected)
        message = t("reveal_added", "Drew {0} selected element(s).").format(len(added))
        if already_visible:
            message += " " + t(
                "reveal_added_visible",
                "{0} already visible in this view.",
            ).format(already_visible)
        if added:
            self._send_inspect(
                self._view(payload["viewId"]), self._element(added[0]), True
            )
        self._reply(request_id, True, message)

    def _on_add_ids(self, payload, request_id):
        self._add_elements(
            [self._element(value) for value in payload.get("elementIds", [])],
            request_id,
        )

    def _close_ghosts(self):
        events.execute_in_revit_context(_close_previews, self.ghost, self.reveal)

    def _on_scene(self, payload, request_id):
        view = self._view(payload["viewId"])
        visible_ids = collect_visible_ids(view)
        states = []
        for element in self._elements():
            findings = diagnose(element, view, visible_ids)
            states.append((element, not any(not f.informational for f in findings)))
        data = scene.build_scene(view, states, format_element_label)
        if data is None:
            self._send("scene", {"viewId": id_value(view.Id), "meshes": []})
        else:
            self._send("scene", raw_payload=scene.scene_to_json(data))
        self._reply(request_id, True)


def _try_describe_fix(view, fix):
    """Describe ``fix`` in ``view``, returning ``(description, error)``.

    Fails closed: when the description cannot be built, the caller must not
    apply the fix, because its template ownership is unknown and a
    template-owned fix would otherwise skip confirmation.
    """
    try:
        return fixes.describe(view, fix), None
    except Exception as ex:
        logger.debug("Cannot describe fix: %s", ex)
        return None, t("fix_describe_failed", "Could not describe fix: {}").format(ex)


def _close_previews(ghost, reveal):
    """Unregister a report's ghost and reveal previews; runs through an ExternalEvent."""
    ghost.close()
    reveal.close()


def supports_interactive_report(output):
    """Return True when ``output`` can show the interactive report.

    It needs IronPython and the WebView2 output renderer.
    """
    try:
        return IRONPY and output.renderer_engine == _WEBVIEW2_ENGINE
    except Exception:
        return False


def show_report(output, elements, views, reveal=False):
    """Diagnose ``elements`` in ``views`` and show the interactive report.

    Args:
        output (PyRevitOutputWindow): the command's output window.
        elements (list[DB.Element]): elements to diagnose.
        views (list[DB.View]): views to diagnose them in; the first one is
            revealed when ``reveal`` is set.
        reveal (bool): also start the reveal-hidden overlay on the first view
            once the page is ready. ``elements`` may then be empty.

    Returns:
        (DiagnosisSession): the live session (kept alive by its output window
        subscriptions).
    """
    session = DiagnosisSession(
        output, views[0].Document, elements, views, reveal=reveal
    )
    session.show()
    return session
