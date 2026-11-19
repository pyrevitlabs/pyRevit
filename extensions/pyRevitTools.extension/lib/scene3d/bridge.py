# -*- coding: utf-8 -*-
"""Message channel between a page in the output window and Python.

Page -> Python messages are ``{channel, action, payload, requestId}``;
Python -> page messages are ``{channel, event, payload}``. Messages on other
channels, for example from a previous run printed into the same window, are
ignored.
"""

import json
import uuid

from pyrevit import script

logger = script.get_logger()


class PageBridge(object):
    """One named channel on an output window, with a handler per page action.

    Args:
        output (pyrevit.output.PyRevitOutputWindow): the output window.
        prefix (str): channel name prefix; a random suffix makes it unique.

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
            logger.debug("No handler for action '%s'", action)
            return
        request_id = message.get("requestId")
        try:
            handler(message.get("payload") or {}, request_id)
        except Exception as ex:
            logger.debug("Handler '%s' failed: %s", action, ex)
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
        """Answer a request with a ``result`` event."""
        self.send("result", {"requestId": request_id, "ok": ok, "message": message})
