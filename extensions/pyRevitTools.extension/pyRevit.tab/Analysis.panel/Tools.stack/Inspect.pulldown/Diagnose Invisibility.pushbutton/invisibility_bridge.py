# -*- coding: utf-8 -*-
"""Two-way message channel between an output window page and Python.

The output window renders with WebView2, which exposes
``window.chrome.webview.postMessage`` to every page it hosts. pyRevit does not
listen to those messages yet, so this module subscribes to the control's
``WebMessageReceived`` event directly and routes JSON messages to Python
handlers. The reverse direction uses ``CoreWebView2.PostWebMessageAsJson``,
which the page receives as a ``message`` event without touching the DOM.

Warning:
    Locating the WebView2 control relies on the output window's visual tree,
    which is not a public runtime contract. ``WebViewBridge.attach`` returns
    False when the control cannot be found; callers must degrade to a
    read-only report in that case.
"""

import json

from pyrevit import script
from pyrevit.framework import Windows
from pyrevit.revit import events

logger = script.get_logger()

_WEBVIEW_TYPE = "Microsoft.Web.WebView2.Wpf.WebView2"


def _find_webview(root):
    """Depth-first search of the logical tree for the WebView2 control."""
    pending = [root]
    while pending:
        node = pending.pop()
        if node is None:
            continue
        if node.GetType().FullName == _WEBVIEW_TYPE:
            return node
        if isinstance(node, Windows.DependencyObject):
            pending.extend(
                child
                for child in Windows.LogicalTreeHelper.GetChildren(node)
                if isinstance(child, Windows.DependencyObject)
            )
    return None


class WebViewBridge(object):
    """Route page messages on one channel to Python handlers.

    Page side::

        chrome.webview.postMessage(JSON.stringify(
            {channel: "<channel>", action: "select", payload: {...}}))
        chrome.webview.addEventListener("message", e => e.data /* object */)

    Handlers run inside Revit API context through
    ``events.execute_in_revit_context``, one ExternalEvent per message, in
    arrival order. A handler's return value is ignored; it answers through
    ``send``.

    Lifecycle: ``attach`` subscribes to the window's WebView2 core and to the
    window's ``Closed`` event, which detaches automatically. Messages from
    other channels (e.g. a previous run printed into the same window) are
    ignored.

    Important:
        Handlers outlive the command, so the bundle must run on a persistent
        engine; a cleaned-up engine would leave dangling callbacks.
    """

    def __init__(self, output, channel):
        self._output = output
        self.channel = channel
        self._handlers = {}
        self._close_callbacks = []
        self._core = None
        self._window = None
        self._on_message_delegate = None
        self._on_closed_delegate = None

    @property
    def attached(self):
        """True while subscribed to a WebView2 core."""
        return self._core is not None

    def on(self, action, handler):
        """Register ``handler(payload, request_id)`` for messages with ``action``."""
        self._handlers[action] = handler

    def on_closed(self, callback):
        """Register ``callback()`` to run once the output window closes.

        Note:
            Runs on the UI thread outside Revit API context; schedule API work
            through ``events.execute_in_revit_context``.
        """
        self._close_callbacks.append(callback)

    def attach(self):
        """Subscribe to the output window's WebView2 messages.

        Blocks until the output document is ready, so call it from the
        command, not from a deferred callback.

        Returns:
            (bool): False when the window does not host a WebView2 control
            (e.g. the WebView2 runtime is missing).
        """
        if self.attached:
            return True
        try:
            window = self._output.window
            window.WaitReadyBrowser()
            control = _find_webview(window)
            core = control.CoreWebView2 if control is not None else None
        except Exception as ex:
            logger.debug("WebView2 bridge unavailable: %s", ex)
            return False
        if core is None or not core.Settings.IsWebMessageEnabled:
            return False

        self._core = core
        self._window = window
        self._on_message_delegate = self._on_message
        self._on_closed_delegate = self._on_window_closed
        core.WebMessageReceived += self._on_message_delegate
        window.Closed += self._on_closed_delegate
        return True

    def detach(self):
        """Unsubscribe from the WebView2 core and the window; idempotent."""
        if self._core is not None:
            try:
                self._core.WebMessageReceived -= self._on_message_delegate
            except Exception:
                pass
        if self._window is not None:
            try:
                self._window.Closed -= self._on_closed_delegate
            except Exception:
                pass
        self._core = None
        self._window = None

    def send(self, event, payload=None, raw_payload=None):
        """Post ``{channel, event, payload}`` to the page.

        Args:
            event (str): event name the page dispatches on.
            payload (object): JSON-serializable data.
            raw_payload (str): pre-encoded JSON used instead of ``payload``,
                for large bodies serialized by a faster custom encoder.

        Must run on the window's UI thread, which is Revit's main thread for
        output windows, so it is safe from handlers and ExternalEvents.
        """
        if self._core is None:
            return
        body = raw_payload if raw_payload is not None else json.dumps(payload)
        message = '{{"channel":{},"event":{},"payload":{}}}'.format(
            json.dumps(self.channel), json.dumps(event), body
        )
        try:
            self._core.PostWebMessageAsJson(message)
        except Exception as ex:
            logger.debug("WebView2 bridge send failed: %s", ex)

    def _on_window_closed(self, sender, args):
        self.detach()
        callbacks, self._close_callbacks = self._close_callbacks, []
        for callback in callbacks:
            try:
                callback()
            except Exception as ex:
                logger.debug("Bridge close callback failed: %s", ex)

    def _on_message(self, sender, args):
        try:
            message = json.loads(args.TryGetWebMessageAsString())
        except Exception:
            return
        if not isinstance(message, dict) or message.get("channel") != self.channel:
            return
        action = message.get("action")
        handler = self._handlers.get(action)
        if handler is None:
            logger.debug("No bridge handler for action '%s'", action)
            return
        events.execute_in_revit_context(
            _dispatch,
            self,
            handler,
            action,
            message.get("payload") or {},
            message.get("requestId"),
        )


def _dispatch(bridge, handler, action, payload, request_id):
    """Run one handler in API context; report failures back to the page."""
    try:
        handler(payload, request_id)
    except Exception as ex:
        logger.debug("Bridge handler '%s' failed: %s", action, ex)
        bridge.send(
            "error",
            {"action": action, "requestId": request_id, "message": str(ex)},
        )
