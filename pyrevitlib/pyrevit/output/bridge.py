# -*- coding: utf-8 -*-
"""Message channel between an interactive page in the output window and Python.

Page -> Python messages are ``{channel, action, payload, requestId}``;
Python -> page messages are ``{channel, event, payload}``. Messages on other
channels, for example from a previous run printed into the same window, are
ignored.

Tools that render an interactive page (a report, a grid, a preview) create one
:class:`PageBridge` per page, register a handler per page action and
:meth:`PageBridge.start` it. The page side posts with
``window.chrome.webview.postMessage`` and listens with
``window.chrome.webview.addEventListener("message", ...)``.
"""

import json
import uuid

from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)


class PageBridge(object):
    """One named channel on an output window, with a handler per page action.

    Args:
        output (pyrevit.output.PyRevitOutputWindow): the output window.
        prefix (str): channel name prefix; a random suffix makes it unique.

    Attributes:
        channel (str): channel name the page must put on every message.
        handlers (dict): action name -> ``handler(payload, request_id)``,
            filled by the tool before :meth:`start`.

    Important:
        ``output.on_message`` handlers outlive the command, so the bundle must
        run on a persistent engine. Handlers run in Revit API context under
        IronPython only.
    """

    def __init__(self, output, prefix):
        self.output = output
        self.channel = "{}-{}".format(prefix, uuid.uuid4().hex)
        self.handlers = {}

    def start(self):
        """Subscribe to the output window; return False when it cannot receive."""
        return self.output.on_message(self._on_page_message)

    def stop(self):
        """Stop receiving page messages."""
        self.output.off_message(self._on_page_message)

    def _on_page_message(self, message):
        if not isinstance(message, dict) or message.get("channel") != self.channel:
            return
        action = message.get("action")
        handler = self.handlers.get(action)
        if handler is None:
            mlogger.debug("No handler for action '%s'", action)
            return
        request_id = message.get("requestId")
        try:
            handler(message.get("payload") or {}, request_id)
        except Exception as ex:
            mlogger.debug("Handler '%s' failed: %s", action, ex)
            self.send(
                "error",
                {"action": action, "requestId": request_id, "message": str(ex)},
            )

    def send(self, event, payload=None, raw_payload=None):
        """Post ``{channel, event, payload}`` to the page.

        ``raw_payload`` is pre-encoded JSON used instead of ``payload``, for
        large bodies serialized by a faster custom encoder than ``json.dumps``.

        Note:
            The envelope is joined with ``+``, not ``str.format``: on
            IronPython 2 formatting non-ASCII text into a byte string raises,
            while concatenation promotes the ASCII parts to unicode. ``ruff
            format`` strips ``u""`` prefixes, so a unicode template is not an
            option.
        """
        if raw_payload is None:
            self.output.post_message(
                {"channel": self.channel, "event": event, "payload": payload}
            )
            return
        self.output.window.PostWebMessage(
            '{"channel":'
            + json.dumps(self.channel)
            + ',"event":'
            + json.dumps(event)
            + ',"payload":'
            + raw_payload
            + "}"
        )

    def reply(self, request_id, ok, message=None):
        """Answer a request with a ``result`` event.

        Args:
            request_id (object): ``requestId`` of the page message.
            ok (bool): whether the request succeeded.
            message (object): JSON-serializable text or data for the page.
        """
        self.send("result", {"requestId": request_id, "ok": ok, "message": message})
