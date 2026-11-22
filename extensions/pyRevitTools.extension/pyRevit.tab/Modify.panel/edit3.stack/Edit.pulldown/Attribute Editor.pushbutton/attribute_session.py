# -*- coding: utf-8 -*-
"""One Attribute Editor page in the output window and the actions it can call.

Page actions: ``load`` (read a source into a grid), ``schedules``,
``categories``, ``available`` (columns that can be added), ``push`` (write
edits, or check them with ``dry``), ``layout`` (write the column set back to
the schedule), ``select`` (select or zoom to elements) and ``theme``.

Important:
    Handlers outlive the command, so the bundle must run on a persistent
    engine, and they run in Revit API context under IronPython only.
"""

import io
import json
import os
import uuid

from pyrevit import DB, HOST_APP, forms, framework, revit, script
from pyrevit.compat import IRONPY, get_elementid_from_value_func, safe_strtype
from pyrevit.output.bridge import PageBridge

from attribute_grid import build_grid
from attribute_sources import (
    ScheduleSource,
    list_categories,
    list_schedules,
    source_from_payload,
)
from attribute_strings import page_strings, t
from attribute_writer import apply_edits, apply_layout

logger = script.get_logger()

get_elementid_from_value = get_elementid_from_value_func()

_WEBVIEW2_ENGINE = "WebView2/Chromium"
_BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPT_ASSETS = ("attribute_grid_core.js", "attribute_grid.js")
_STYLE_ASSET = "attribute_grid.css"
THEME_PREFERENCES = ("auto", "light", "dark")


def _read_asset(name):
    with io.open(os.path.join(_BUNDLE_DIR, name), encoding="utf-8") as asset:
        return asset.read()


def supports_interactive_page(output):
    """Whether the output window is WebView2 on IronPython, which the page needs."""
    try:
        return IRONPY and output.renderer_engine == _WEBVIEW2_ENGINE
    except Exception as ex:
        logger.debug("Cannot tell the output renderer: %s", ex)
        return False


class AttributeSession(object):
    """The Attribute Editor page of one command run."""

    def __init__(self, output, doc, start_source):
        self.output = output
        self.doc = doc
        self.start_source = start_source
        self.config = script.get_config()
        self.bridge = PageBridge(output, "attribute-editor")
        self.root_id = "attribute-editor-{}".format(uuid.uuid4().hex[:8])

    def show(self):
        """Render the page and start listening; False when the page cannot receive."""
        if not self.bridge.start():
            return False
        for action, function in (
            ("load", self._load),
            ("schedules", self._schedules),
            ("categories", self._categories),
            ("available", self._available),
            ("push", self._push),
            ("layout", self._layout),
            ("select", self._select),
            ("theme", self._theme),
        ):
            self._register(action, function)
        self.output.set_title(t("ui_title"))
        self.output.resize(1320, 800)
        self.output.add_style(_read_asset(_STYLE_ASSET))
        for asset in _SCRIPT_ASSETS:
            self.output.inject_script(_read_asset(asset))
        self.output.inject_to_body("div", "", {"id": self.root_id})
        self.output.inject_script(
            "window.pyRevitAttributeGrid.mount("
            + json.dumps(self.root_id)
            + ", "
            + json.dumps(self._payload(), ensure_ascii=False)
            + ");",
            body=True,
        )
        return True

    def dispose(self):
        """Stop handling messages and remove the page of this session."""
        self.bridge.stop()
        try:
            self.bridge.send("dispose")
        except Exception as ex:
            logger.debug("Window already gone: %s", ex)

    def _payload(self):
        preference = self.config.get_option("theme", "auto")
        return {
            "channel": self.bridge.channel,
            "strings": page_strings(),
            "dark": bool(forms.is_dark_theme()),
            "themePreference": (
                preference if preference in THEME_PREFERENCES else "auto"
            ),
            "start": self.start_source,
            "scopeAvailable": {
                "view": bool(self.doc.ActiveView),
                "selection": True,
            },
        }

    def _register(self, action, function):
        def handler(payload, request_id):
            try:
                result = function(payload)
            except Exception as ex:
                logger.exception("Attribute Editor action '%s' failed", action)
                self.bridge.reply(request_id, False, safe_strtype(ex))
                return
            self.bridge.reply(request_id, True, result)

        self.bridge.handlers[action] = handler

    def _load(self, payload):
        source = source_from_payload(self.doc, payload)
        return build_grid(
            self.doc, source, payload.get("columns"), payload.get("unitMode")
        )

    def _schedules(self, payload):
        return list_schedules(self.doc)

    def _categories(self, payload):
        return list_categories(self.doc)

    def _available(self, payload):
        source = source_from_payload(self.doc, payload)
        return source.available(bool(payload.get("scanAll")))

    def _push(self, payload):
        results = apply_edits(
            self.doc,
            payload.get("edits") or [],
            payload.get("unitMode"),
            force=bool(payload.get("force")),
            dry=bool(payload.get("dry")),
        )
        return {"results": results}

    def _layout(self, payload):
        source = source_from_payload(self.doc, payload)
        if not isinstance(source, ScheduleSource):
            raise ValueError(t("err_not_schedulable"))
        return apply_layout(self.doc, source, payload.get("columns") or [])

    def _select(self, payload):
        ids = [get_elementid_from_value(int(value)) for value in payload["ids"]]
        revit.get_selection().set_to(ids)
        if payload.get("zoom"):
            HOST_APP.uidoc.ShowElements(framework.to_clr_list(DB.ElementId, ids))
        return {}

    def _theme(self, payload):
        preference = payload.get("preference")
        if preference in THEME_PREFERENCES:
            self.config.set_option("theme", preference)
            script.save_config()
        return {}
