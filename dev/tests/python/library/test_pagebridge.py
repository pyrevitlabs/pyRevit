"""Host-free tests for ``pyrevit.output.bridge.PageBridge``.

Loads ``pyrevitlib/pyrevit/output/bridge.py`` with stubbed ``pyrevit`` modules
and a recording output window, and checks the channel filtering, the handler
dispatch, the error reply and the message envelopes.
"""

import importlib.util
import json
import logging
import pathlib
import sys
import types
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

BRIDGE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "pyrevitlib"
    / "pyrevit"
    / "output"
    / "bridge.py"
)


def load_bridge():
    names = (
        "pyrevit",
        "pyrevit.compat",
        "pyrevit.coreutils",
        "pyrevit.coreutils.logger",
    )
    previous = {name: sys.modules.get(name) for name in names}
    logger_module = types.ModuleType("pyrevit.coreutils.logger")
    logger_module.get_logger = lambda name: logging.getLogger(name)
    coreutils_module = types.ModuleType("pyrevit.coreutils")
    coreutils_module.logger = logger_module
    compat_module = types.ModuleType("pyrevit.compat")
    compat_module.safe_strtype = str
    pyrevit_module = types.ModuleType("pyrevit")
    pyrevit_module.coreutils = coreutils_module
    pyrevit_module.compat = compat_module
    sys.modules.update(
        {
            "pyrevit": pyrevit_module,
            "pyrevit.compat": compat_module,
            "pyrevit.coreutils": coreutils_module,
            "pyrevit.coreutils.logger": logger_module,
        }
    )
    try:
        spec = importlib.util.spec_from_file_location("bridge_under_test", BRIDGE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, module_before in previous.items():
            if module_before is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module_before
    return module


class RecordingWindow:
    def __init__(self):
        self.raw = []

    def PostWebMessage(self, text):
        self.raw.append(text)
        return True


class RecordingOutput:
    def __init__(self):
        self.window = RecordingWindow()
        self.posted = []
        self.listeners = []
        self.can_receive = True

    def on_message(self, handler):
        if not self.can_receive:
            return False
        self.listeners.append(handler)
        return True

    def off_message(self, handler):
        self.listeners.remove(handler)

    def post_message(self, data):
        json.dumps(data)
        self.posted.append(data)
        return True


class PageBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_bridge()

    def setUp(self):
        self.output = RecordingOutput()
        self.bridge = self.module.PageBridge(self.output, "grid")

    def page_says(self, action, payload=None, request_id=1, channel=None):
        self.output.listeners[0](
            {
                "channel": channel or self.bridge.channel,
                "action": action,
                "payload": payload,
                "requestId": request_id,
            }
        )

    def test_channel_is_prefixed_and_unique_per_bridge(self):
        other = self.module.PageBridge(self.output, "grid")
        self.assertTrue(self.bridge.channel.startswith("grid-"))
        self.assertNotEqual(self.bridge.channel, other.channel)

    def test_start_reports_whether_the_window_can_receive(self):
        self.assertTrue(self.bridge.start())
        self.output.can_receive = False
        self.assertFalse(self.module.PageBridge(self.output, "grid").start())

    def test_handler_receives_payload_and_request_id(self):
        seen = []
        self.bridge.handlers["push"] = lambda payload, request_id: seen.append(
            (payload, request_id)
        )
        self.bridge.start()
        self.page_says("push", {"edits": [1]}, request_id=7)
        self.assertEqual(seen, [({"edits": [1]}, 7)])

    def test_missing_payload_becomes_an_empty_dict(self):
        seen = []
        self.bridge.handlers["pull"] = lambda payload, request_id: seen.append(payload)
        self.bridge.start()
        self.page_says("pull", None)
        self.assertEqual(seen, [{}])

    def test_false_valued_payloads_reach_the_handler_unchanged(self):
        seen = []
        self.bridge.handlers["set"] = lambda payload, request_id: seen.append(payload)
        self.bridge.start()
        for payload in (False, 0, "", []):
            self.page_says("set", payload)
        self.assertEqual(
            [(type(value), value) for value in seen],
            [(bool, False), (int, 0), (str, ""), (list, [])],
        )

    def test_messages_on_other_channels_are_ignored(self):
        seen = []
        self.bridge.handlers["push"] = lambda payload, request_id: seen.append(1)
        self.bridge.start()
        self.page_says("push", channel="grid-previous-run")
        self.output.listeners[0]("not a dict")
        self.assertEqual(seen, [])
        self.assertEqual(self.output.posted, [])

    def test_unknown_action_is_ignored(self):
        self.bridge.start()
        self.page_says("nope")
        self.assertEqual(self.output.posted, [])

    def test_an_unhashable_action_is_ignored(self):
        self.bridge.start()
        for action in ([], ["push"], {}, {"name": "push"}):
            self.page_says(action)
        self.assertEqual(self.output.posted, [])

    def test_handler_failure_is_sent_back_as_an_error_event(self):
        def fail(payload, request_id):
            raise ValueError("bad cell")

        self.bridge.handlers["push"] = fail
        self.bridge.start()
        self.page_says("push", request_id=3)
        self.assertEqual(
            self.output.posted,
            [
                {
                    "channel": self.bridge.channel,
                    "event": "error",
                    "payload": {
                        "action": "push",
                        "requestId": 3,
                        "message": "bad cell",
                    },
                }
            ],
        )

    def test_reply_sends_a_result_event(self):
        self.bridge.reply(5, True, {"rows": 2})
        self.assertEqual(
            self.output.posted[0]["payload"],
            {"requestId": 5, "ok": True, "message": {"rows": 2}},
        )
        self.assertEqual(self.output.posted[0]["event"], "result")

    def test_raw_payload_is_embedded_without_reencoding(self):
        self.bridge.send("scene", raw_payload='{"a":[1,2]}')
        envelope = json.loads(self.output.window.raw[0])
        self.assertEqual(
            envelope,
            {
                "channel": self.bridge.channel,
                "event": "scene",
                "payload": {"a": [1, 2]},
            },
        )

    def test_a_registered_function_is_answered_with_its_return_value(self):
        self.bridge.register("push", lambda payload: {"written": payload["n"]})
        self.bridge.start()
        self.page_says("push", {"n": 4}, request_id=9)
        self.assertEqual(
            self.output.posted,
            [
                {
                    "channel": self.bridge.channel,
                    "event": "result",
                    "payload": {"requestId": 9, "ok": True, "message": {"written": 4}},
                }
            ],
        )

    def test_a_registered_function_that_raises_still_answers_the_request(self):
        def fail(payload):
            raise ValueError("boom")

        self.bridge.register("push", fail)
        self.bridge.start()
        with self.assertLogs("bridge_under_test", level="ERROR"):
            self.page_says("push", request_id=2)
        self.assertEqual(
            self.output.posted[0]["payload"],
            {"requestId": 2, "ok": False, "message": "boom"},
        )

    def test_an_unserializable_return_value_is_answered_with_an_error_event(self):
        self.bridge.register("push", lambda payload: object())
        self.bridge.start()
        self.page_says("push", request_id=4)
        self.assertEqual([sent["event"] for sent in self.output.posted], ["error"])
        self.assertEqual(self.output.posted[0]["payload"]["action"], "push")
        self.assertEqual(self.output.posted[0]["payload"]["requestId"], 4)

    def test_an_expected_refusal_is_answered_without_an_error_log(self):
        class Refusal(Exception):
            pass

        def refuse(payload):
            raise Refusal("not now")

        self.bridge.register("push", refuse, expected=(Refusal,))
        self.bridge.start()
        with self.assertLogs("bridge_under_test", level="INFO") as logs:
            self.page_says("push", request_id=6)
        self.assertEqual([record.levelname for record in logs.records], ["INFO"])
        self.assertEqual(
            self.output.posted[0]["payload"],
            {"requestId": 6, "ok": False, "message": "not now"},
        )

    def test_stop_unsubscribes(self):
        self.bridge.start()
        self.bridge.stop()
        self.assertEqual(self.output.listeners, [])


if __name__ == "__main__":
    unittest.main()
