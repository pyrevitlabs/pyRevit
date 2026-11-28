# -*- coding: utf-8 -*-
"""Message channel between an interactive page in the output window and Python.

Page -> Python messages are ``{channel, action, payload, requestId}``;
Python -> page messages are ``{channel, event, payload}``. Messages on other
channels, for example from a previous run printed into the same window, are
ignored.

Tools that render an interactive page (a report, a grid, a preview) create one
:class:`PageBridge` per page, register a handler per page action
(:meth:`PageBridge.register`, or the lower-level ``handlers`` dict) and
:meth:`PageBridge.start` it. The page side posts with
``window.chrome.webview.postMessage`` and listens with
``window.chrome.webview.addEventListener("message", ...)``.

Warning:
    The channel routes messages; it does not authenticate them. Any script in
    the output window's document can read it and post to any registered
    action, including script that got there through unescaped text printed by
    this or an earlier command. Escape model data before printing it as HTML
    or Markdown, insert it in page scripts with ``textContent`` rather than
    ``innerHTML``, and treat each payload in a handler as untrusted input.
"""

import json
import uuid

from pyrevit.compat import safe_strtype
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
            filled by the tool before :meth:`start`. A handler owns its reply;
            :meth:`register` builds handlers that reply on their behalf.

    Important:
        ``output.on_message`` handlers outlive the command, so the bundle must
        run on a persistent engine. Handlers run in Revit API context.
    """

    def __init__(self, output, prefix):
        self.output = output
        self.channel = "{}-{}".format(prefix, uuid.uuid4().hex)
        self.handlers = {}

    def register(self, action, function, expected=()):
        """Serve ``action`` with ``function(payload)`` and reply with what it returns.

        A return value is answered as a successful ``result``. An exception is
        answered as a failed ``result`` carrying its text, so the page's
        request never stays pending.

        Args:
            action (str): action name the page posts.
            function (callable): ``function(payload)`` returning a
                JSON-serializable value.
            expected (tuple): exception classes that are routine refusals whose
                message is meant for the user. They are logged without a
                traceback; any other exception is logged with one.
        """

        def handler(payload, request_id):
            try:
                result = function(payload)
            except expected as ex:
                mlogger.info("Action '%s' refused: %s", action, safe_strtype(ex))
                self.reply(request_id, False, safe_strtype(ex))
                return
            except Exception as ex:
                mlogger.exception("Action '%s' failed", action)
                self.reply(request_id, False, safe_strtype(ex))
                return
            self.reply(request_id, True, result)

        self.handlers[action] = handler

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
        handler = (
            None if isinstance(action, (dict, list)) else self.handlers.get(action)
        )
        if handler is None:
            mlogger.debug("No handler for action '%s'", action)
            return
        request_id = message.get("requestId")
        payload = message.get("payload")
        if payload is None:
            payload = {}
        try:
            handler(payload, request_id)
        except Exception as ex:
            mlogger.debug("Handler '%s' failed: %s", action, ex)
            self.send(
                "error",
                {
                    "action": action,
                    "requestId": request_id,
                    "message": safe_strtype(ex),
                },
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
