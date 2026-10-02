"""Agent host requests other than runs: context, inspection, presentation and capture."""

import os.path as op
from unittest import TestCase, skipUnless

import agent_harness as harness
from agent_harness import AgentRequestError, request

PNG_SIGNATURE = b"\x89PNG"


class ContextTests(TestCase):
    """The get_context request and request-level errors."""

    def test_context_names_the_scratch_documents(self):
        """get_context reports the active and the other open scratch document."""
        context = request("get_context")
        titles = [document["title"] for document in context["open_documents"]]
        self.assertEqual(harness.session().project_title, context["document"]["title"])
        self.assertIn(harness.session().other_title, titles)

    def test_context_reports_both_engines(self):
        """get_context reports IronPython and CPython as available."""
        engines = request("get_context")["scripting"]["engines"]
        for engine in harness.ENGINES:
            self.assertTrue(engines[engine]["available"], engine)

    @skipUnless(harness.CPYTHON_HOST, "only a CPython command can nest a CPython run")
    def test_cpython_run_from_a_cpython_command_is_refused(self):
        """A CPython run requested from a CPython command is refused instead of crashing Revit."""
        with self.assertRaises(AgentRequestError) as raised:
            harness.run("result = 1", engine="cpython")
        self.assertEqual("nested_cpython", raised.exception.code)

    def test_unknown_method_is_rejected(self):
        """An unknown method comes back as method_not_found."""
        with self.assertRaises(AgentRequestError) as raised:
            request("no_such_method")
        self.assertEqual("method_not_found", raised.exception.code)


class InspectTests(TestCase):
    """The inspect_elements request."""

    def test_inspect_describes_elements_and_missing_ids(self):
        """inspect_elements returns parameters, a navigation link, and found=false for a bad id."""
        wall = harness.session().wall_ids[0]
        elements = request("inspect_elements", ids=[wall, 999999999])["elements"]
        self.assertEqual("Wall", elements[0]["class"])
        self.assertTrue(elements[0]["parameters"])
        self.assertEqual([wall], elements[0]["link"]["ids"])
        self.assertFalse(elements[1]["found"])

    def test_inspect_can_skip_parameters(self):
        """inspect_elements with parameters=false leaves the parameters out."""
        wall = harness.session().wall_ids[0]
        element = request("inspect_elements", ids=[wall], parameters=False)["elements"][
            0
        ]
        self.assertNotIn("parameters", element)


class ShowTests(TestCase):
    """The show request."""

    def test_show_selects_isolates_hides_and_resets(self):
        """The show request runs every action, and a selection is visible in the context."""
        ids = harness.session().wall_ids[:1]
        self.assertEqual(1, request("show", action="select", ids=ids)["count"])
        self.assertIn(ids[0], request("get_context")["selection"]["ids"])
        for action in ("isolate", "hide"):
            request("show", action=action, ids=ids, zoom=False)
        self.assertTrue(request("show", action="reset")["reset"])

    def test_show_by_category(self):
        """The show request can isolate a whole category."""
        result = request("show", action="isolate", categories=["OST_Walls"])
        self.assertGreater(result["count"], 0)
        request("show", action="reset")


class CaptureTests(TestCase):
    """The capture request."""

    def test_capture_modes_write_pngs(self):
        """The capture request writes a PNG in export and viewport mode."""
        for mode in ("export", "viewport"):
            result = request("capture", mode=mode, width=400)
            with open(result["path"], "rb") as handle:
                self.assertEqual(PNG_SIGNATURE, handle.read(4), mode)

    def test_framed_capture_leaves_no_view_behind(self):
        """A framed 3D capture uses a temporary view and removes it."""
        count = "result = DB.FilteredElementCollector(doc).OfClass(DB.View3D).GetElementCount()"
        before = harness.run(count)["result"]
        result = request(
            "capture",
            view="3d",
            direction="northwest",
            elements=harness.session().wall_ids,
            width=300,
        )
        self.assertTrue(op.exists(result["path"]))
        self.assertEqual(before, harness.run(count)["result"])

    def test_unknown_view_is_reported(self):
        """The capture request for a missing view comes back as view_not_found."""
        with self.assertRaises(AgentRequestError) as raised:
            request("capture", view="No Such View")
        self.assertEqual("view_not_found", raised.exception.code)


class ApiLookupTests(TestCase):
    """The lookup_api request, which needs no Revit API thread."""

    def test_lookup_finds_nested_classes(self):
        """lookup_api resolves Room to DB.Architecture.Room."""
        found = request("lookup_api", name="Room")
        self.assertEqual("Autodesk.Revit.DB.Architecture.Room", found["full_name"])
