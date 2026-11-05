"""Parameter validation of the agent host requests: what each one refuses to run."""

import os.path as op

import agent_harness as harness
from agent_harness import AgentRequestError, TestCase, request

NOT_PRINTABLE_VIEW = (
    "views = [v for v in DB.FilteredElementCollector(doc).OfClass(DB.View)"
    " if not v.IsTemplate and not v.CanBePrinted]\n"
    "result = None\n"
    "if views:\n"
    "    result = views[0].Id.Value if hasattr(views[0].Id, 'Value') else views[0].Id.IntegerValue\n"
)

CLOSED_PLAN_VIEW = (
    "open_ids = [uv.ViewId for uv in uidoc.GetOpenUIViews()]\n"
    "plans = [v for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan)"
    " if not v.IsTemplate and not any(o.Equals(v.Id) for o in open_ids)]\n"
    "result = None\n"
    "if plans:\n"
    "    result = plans[0].Id.Value if hasattr(plans[0].Id, 'Value') else plans[0].Id.IntegerValue\n"
)


def _code(method, **params):
    try:
        request(method, **params)
    except AgentRequestError as error:
        return error.code
    return None


class RunValidationTests(TestCase):
    """The run request rejects what it can't execute faithfully."""

    def test_a_script_is_required(self):
        """A run without a script, or with a blank one, is rejected."""
        self.assertEqual("invalid_params", _code("run", mode="query"))
        self.assertEqual("invalid_params", _code("run", script="   ", mode="query"))

    def test_mode_and_engine_must_be_known(self):
        """An unknown mode or engine is rejected."""
        self.assertEqual(
            "invalid_params", _code("run", script="x = 1", mode="sideways")
        )
        self.assertEqual("invalid_params", _code("run", script="x = 1", engine="lua"))

    def test_timeout_must_be_positive_and_at_most_an_hour(self):
        """A timeout of zero, a negative one, or more than 3600 seconds is rejected."""
        for value in (0, -1, 3601, 99999):
            self.assertEqual(
                "invalid_params", _code("run", script="x = 1", timeout_s=value), value
            )

    def test_the_timeout_limits_themselves_are_accepted(self):
        """One second and 3600 seconds are valid timeouts."""
        for value in (1, 3600):
            self.assertEqual(
                "ok", harness.run("result = 1", timeout=value)["status"], value
            )

    def test_workspace_must_be_an_existing_absolute_folder(self):
        """A relative workspace and a missing folder are rejected."""
        missing = op.join(harness.session().folder, "no-such-folder")
        for value in ("relative folder", missing):
            self.assertEqual(
                "invalid_params", _code("run", script="x = 1", workspace=value), value
            )

    def test_start_timeout_is_validated_before_anything_runs(self):
        """A start timeout of zero, a negative one, or more than 3600 seconds is rejected."""
        for value in (0, -3, 3601):
            self.assertEqual(
                "invalid_params", _code("get_context", start_timeout_s=value), value
            )


class InspectValidationTests(TestCase):
    """The inspect_elements request validates its ids."""

    def test_ids_are_required_and_bounded(self):
        """No ids, an empty list, or more than 50 ids is rejected."""
        self.assertEqual("invalid_params", _code("inspect_elements"))
        self.assertEqual("invalid_params", _code("inspect_elements", ids=[]))
        self.assertEqual(
            "invalid_params", _code("inspect_elements", ids=list(range(1, 52)))
        )

    def test_ids_must_be_integers(self):
        """An id that is not an integer is rejected."""
        self.assertEqual("invalid_params", _code("inspect_elements", ids=["abc"]))

    def test_fifty_ids_are_accepted(self):
        """Exactly 50 ids are inspected."""
        elements = request(
            "inspect_elements", ids=list(range(1, 51)), parameters=False
        )["elements"]
        self.assertEqual(50, len(elements))


class ShowValidationTests(TestCase):
    """The show request validates its action and targets."""

    def test_the_action_must_be_known(self):
        """An unknown action is rejected."""
        self.assertEqual("invalid_params", _code("show", action="explode", ids=[1]))

    def test_something_to_show_is_required_except_for_reset(self):
        """Select, isolate and hide need ids or categories; reset needs neither."""
        for action in ("select", "isolate", "hide"):
            self.assertEqual("invalid_params", _code("show", action=action), action)
            self.assertEqual(
                "invalid_params", _code("show", action=action, ids=[]), action
            )
        self.assertIn("reset", request("show", action="reset"))

    def test_unknown_categories_and_non_integer_ids_are_rejected(self):
        """A category that does not exist, or a non-integer id, is rejected."""
        self.assertEqual(
            "invalid_params",
            _code("show", action="select", categories=["NotACategory"]),
        )
        self.assertEqual("invalid_params", _code("show", action="select", ids=["abc"]))

    def test_category_names_ignore_case_and_the_ost_prefix(self):
        """Walls, walls, OST_Walls and ost_walls all name the same category."""
        for name in ("Walls", "walls", "OST_Walls", "ost_walls"):
            result = request("show", action="isolate", categories=[name])
            self.assertGreater(result["count"], 0, name)
        request("show", action="reset")


class CaptureValidationTests(TestCase):
    """The capture request validates its parameters and the view it is asked for."""

    def test_mode_and_direction_must_be_known(self):
        """An unknown mode or direction is rejected."""
        self.assertEqual("invalid_params", _code("capture", mode="telepathy"))
        self.assertEqual(
            "invalid_params", _code("capture", view="3d", direction="sideways")
        )

    def test_width_is_clamped_to_the_supported_range(self):
        """A width below 320 or above 2400 is clamped instead of rejected."""
        narrow = request("capture", mode="export", width=1)
        wide = request("capture", mode="export", width=99999)
        self.assertGreater(narrow["width"], 100)
        self.assertLessEqual(narrow["width"], 320)
        self.assertLessEqual(wide["width"], 2400)

    def test_a_view_can_be_named_by_id_or_by_name_ignoring_case(self):
        """A view is found by its numeric id and by its name in any case."""
        active = request("get_context")["active_view"]
        by_id = request("capture", mode="export", view=str(active["id"]), width=320)
        by_name = request(
            "capture", mode="export", view=active["name"].lower(), width=320
        )
        self.assertEqual(active["id"], by_id["view"]["id"])
        self.assertEqual(active["id"], by_name["view"]["id"])

    def test_a_view_that_cannot_be_exported_is_not_supported(self):
        """A view Revit can't print is refused in export mode."""
        view_id = harness.run(NOT_PRINTABLE_VIEW)["result"]
        if view_id is None:
            self.skipTest("This Revit has no view that can't be printed.")
        self.assertEqual(
            "view_not_supported", _code("capture", mode="export", view=str(view_id))
        )

    def test_a_view_that_is_not_open_cannot_be_captured_as_a_viewport(self):
        """Viewport mode needs an open view."""
        view_id = harness.run(CLOSED_PLAN_VIEW)["result"]
        if view_id is None:
            self.skipTest("Every plan view is open.")
        self.assertEqual(
            "view_not_open", _code("capture", mode="viewport", view=str(view_id))
        )


class LookupValidationTests(TestCase):
    """The lookup_api request validates its name."""

    def test_a_name_is_required(self):
        """A missing or blank name is rejected."""
        self.assertEqual("invalid_params", _code("lookup_api"))
        self.assertEqual("invalid_params", _code("lookup_api", name="   "))

    def test_an_unknown_name_is_reported_as_not_found(self):
        """A name that matches nothing answers found=false instead of failing."""
        self.assertFalse(request("lookup_api", name="ThereIsNoSuchRevitType")["found"])
