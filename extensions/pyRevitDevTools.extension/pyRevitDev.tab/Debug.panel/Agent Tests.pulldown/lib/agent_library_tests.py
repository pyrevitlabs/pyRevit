"""Library integration: skills and library tools of the MCP server, and the automation operations.

Skills, ``lookup_pyrevit_api`` and ``list_automation`` run inside the CLI and never
call Revit, so they are reached through a short-lived ``pyrevit mcp`` process.
``run_automation`` and ``navigate_revit_link`` call back into Revit through the
pipe, which can't answer while a command runs; their pyrevitlib side is tested
in-process instead.
"""

import json
import os
import os.path as op
import shutil
from unittest import TestCase

import System
from System.Diagnostics import Process, ProcessStartInfo

from pyrevit import HOME_DIR
from pyrevit.labs import PyRevit

import agent_harness as harness
from agent_harness import ENGINES, request, run

SHIPPED_SKILLS = (
    "revit-scripting",
    "drawings",
    "extension-authoring",
    "family-editing",
    "family-geometry",
    "modeling",
    "pyrevit-library",
    "revit-files",
    "scheduling",
    "views",
)
CLI = op.join(HOME_DIR, "bin", "pyrevit.exe")


def _mcp(*calls):
    """Run tool calls through one ``pyrevit mcp`` process.

    Returns:
        tuple: the ``initialize`` result and the tool results, in call order.
    """
    lines = [
        {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "agent-tests", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ]
    for index, (tool, arguments) in enumerate(calls, 1):
        lines.append(
            {
                "jsonrpc": "2.0",
                "id": index,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            }
        )
    info = ProcessStartInfo(CLI, "mcp")
    info.UseShellExecute = False
    info.RedirectStandardInput = True
    info.RedirectStandardOutput = True
    info.CreateNoWindow = True
    info.StandardOutputEncoding = System.Text.Encoding.UTF8
    process = Process.Start(info)
    for line in lines:
        process.StandardInput.WriteLine(json.dumps(line))
    process.StandardInput.Close()
    reading = process.StandardOutput.ReadToEndAsync()
    if not reading.Wait(harness.CLI_TIMEOUT_MS):
        process.Kill()
        raise AssertionError(
            "pyrevit mcp did not finish within {} ms".format(harness.CLI_TIMEOUT_MS)
        )
    process.WaitForExit(harness.CLI_TIMEOUT_MS)
    output = str(reading.Result)
    responses = {}
    for line in output.splitlines():
        if line.strip().startswith("{"):
            message = json.loads(line)
            responses[message.get("id")] = message
    results = [responses[index]["result"] for index in range(1, len(calls) + 1)]
    return responses[0]["result"], [_tool_result(result) for result in results]


def _tool_result(result):
    text = result["content"][0]["text"]
    try:
        data = json.loads(text)
    except ValueError:
        data = text
    return result.get("isError", False), data


class SkillTests(TestCase):
    """Shipped skills served by the MCP server."""

    def test_every_shipped_skill_is_listed_named_and_readable(self):
        """All nine shipped skills are listed, named in the instructions, and readable."""
        calls = [("list_skills", {})] + [
            ("get_skill", {"name": name}) for name in SHIPPED_SKILLS
        ]
        initialized, results = _mcp(*calls)
        listed = [
            skill["name"] for skill in results[0][1] if skill["source"] == "pyrevit"
        ]
        for name, (is_error, text) in zip(SHIPPED_SKILLS, results[1:]):
            self.assertIn(name, listed)
            self.assertIn(name, initialized["instructions"])
            self.assertFalse(is_error, name)
            self.assertIn("name: " + name, text)

    def test_skill_files_outside_the_skill_or_not_markdown_are_rejected(self):
        """A skill file outside its folder, or not markdown, is rejected."""
        _, results = _mcp(
            ("get_skill", {"name": "revit-scripting", "file": "../INSTRUCTIONS.md"}),
            ("get_skill", {"name": "revit-scripting", "file": "SKILL.txt"}),
            ("get_skill", {"name": "no-such-skill"}),
        )
        self.assertEqual("invalid_params", results[0][1]["error"])
        self.assertEqual("invalid_params", results[1][1]["error"])
        self.assertEqual("skill_not_found", results[2][1]["error"])


class UserSkillTests(TestCase):
    """User skills from the user's skills folder."""

    def test_user_skills_are_bounded_and_cannot_replace_shipped_ones(self):
        """User skills are cut short, can't replace a shipped skill, and bad ones are skipped."""
        root = op.join(os.environ["APPDATA"], "pyRevit", "agent", "skills")
        owns_root = not op.isdir(root)
        enabled_before = PyRevit.PyRevitConfigs.GetAgentUserSkillsEnabled()
        created = []
        locked = None
        try:
            created.append(
                _write_skill(
                    root, "agent-test-standards", "D" * 300, "Agent test body."
                )
            )
            created.append(
                _write_skill(root, "agent-test-bad_name", "Invalid name.", "body")
            )
            locked_skill = _write_skill(root, "agent-test-locked", "Locked.", "body")
            created.append(locked_skill)
            locked = System.IO.File.Open(
                op.join(locked_skill, "SKILL.md"),
                System.IO.FileMode.Open,
                System.IO.FileAccess.ReadWrite,
                getattr(System.IO.FileShare, "None"),
            )
            if owns_root:
                created.append(
                    _write_skill(
                        root, "modeling", "User copy.", "AGENT-TEST-USER-MODELING"
                    )
                )
            PyRevit.PyRevitConfigs.SetAgentUserSkillsEnabled(True)

            _, results = _mcp(
                ("list_skills", {}),
                ("get_skill", {"name": "agent-test-standards"}),
                ("get_skill", {"name": "modeling"}),
            )
            skills = dict((skill["name"], skill) for skill in results[0][1])
            standards = skills["agent-test-standards"]
            self.assertEqual("user", standards["source"])
            self.assertEqual(240, len(standards["description"]))
            self.assertTrue(standards["description"].endswith("..."))
            self.assertIn("Agent test body.", results[1][1])
            self.assertNotIn("agent-test-bad_name", skills)
            self.assertNotIn("agent-test-locked", skills)
            self.assertEqual("pyrevit", skills["modeling"]["source"])
            self.assertNotIn("AGENT-TEST-USER-MODELING", results[2][1])
        finally:
            if locked is not None:
                locked.Dispose()
            PyRevit.PyRevitConfigs.SetAgentUserSkillsEnabled(enabled_before)
            for folder in created:
                shutil.rmtree(folder, ignore_errors=True)
            if owns_root and op.isdir(root) and not os.listdir(root):
                os.rmdir(root)


class LookupTests(TestCase):
    """The pyrevitlib lookup and the automation listing."""

    def test_lookup_finds_functions_and_reports_misses(self):
        """The lookup_pyrevit_api tool finds find_level and reports a miss."""
        _, results = _mcp(
            ("lookup_pyrevit_api", {"query": "find level by name"}),
            ("lookup_pyrevit_api", {"query": "zzqxwv"}),
        )
        names = [match["name"] for match in results[0][1]["matches"]]
        self.assertIn("pyrevit.revit.db.query.find_level", names)
        self.assertFalse(results[1][1]["found"])

    def test_automation_list_pages_without_overlap_and_rejects_bad_paging(self):
        """The list_automation tool pages without overlap and rejects a zero limit."""
        _, results = _mcp(
            ("list_automation", {"limit": 10}),
            ("list_automation", {"offset": 10, "limit": 10}),
            ("list_automation", {"limit": 0}),
        )
        first = [entry["automation"]["id"] for entry in results[0][1]["operations"]]
        second = [entry["automation"]["id"] for entry in results[1][1]["operations"]]
        self.assertEqual(10, results[0][1]["next_offset"])
        self.assertFalse(set(first) & set(second))
        self.assertEqual("invalid_params", results[2][1]["error"])


class LinkTests(TestCase):
    """The element navigation links that inspect_elements returns."""

    def test_inspect_returns_a_link_naming_the_document_and_element(self):
        """inspect_elements returns a link naming the active document and the element."""
        wall = harness.session().wall_ids[0]
        element = request("inspect_elements", ids=[wall], parameters=False)["elements"][
            0
        ]
        link = element["link"]
        self.assertEqual("element", link["destination"])
        self.assertEqual([wall], link["ids"])
        self.assertEqual(harness.session().project_title, link["document"]["title"])


class AutomationTests(TestCase):
    """The pyrevitlib side of the automation operations, run as agent scripts on both engines."""

    def test_markers_survive_on_every_engine(self):
        """The automation markers are readable on the marked functions."""
        script = (
            "from pyrevit.revit.db import query\nfrom pyrevit.revit import units\n"
            "result = [query.find_level.__pyrevit_automation__['id'],"
            " units.parse_slope.__pyrevit_automation__['id']]"
        )
        for engine in ENGINES:
            self.assertEqual(
                ["pyrevit.levels.resolve", "pyrevit.units.parse-slope"],
                run(script, engine=engine)["result"],
                engine,
            )

    def test_elements_by_category_slices_after_listing(self):
        """Elements by category can be listed and sliced the way the operation does."""
        script = (
            "from pyrevit.revit.db import query\n"
            "elements = list(query.get_elements_by_categories([DB.BuiltInCategory.OST_Walls], doc=doc))\n"
            "result = {'total': len(elements), 'page': len(elements[:1])}"
        )
        for engine in ENGINES:
            result = run(script, engine=engine)["result"]
            self.assertEqual(len(harness.session().wall_ids), result["total"], engine)
            self.assertEqual(1, result["page"], engine)

    def test_levels_resolve_by_name_and_list_names_when_missing(self):
        """The find_level function resolves a level by name and lists the names when it is missing."""
        name = run(
            "result = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement().Name"
        )["result"]
        script = "from pyrevit.revit.db import query\nresult = query.find_level(inputs['name'], doc=doc).Name"
        for engine in ENGINES:
            self.assertEqual(
                name,
                run(script, engine=engine, inputs={"name": name})["result"],
                engine,
            )
            missing = run(script, engine=engine, inputs={"name": "No Such Level"})
            self.assertIn(name, missing["error"]["message"], engine)

    def test_units_parse_common_notations(self):
        """The unit parsers read the common notations and reject a zero run."""
        script = (
            "from pyrevit.revit import units\n"
            "result = [units.parse_slope(v) for v in ('8:12', '8 in 12', '0.5', '45deg')]"
            ' + [units.parse_length("10\' 6\\"")]'
        )
        for engine in ENGINES:
            values = run(script, engine=engine)["result"]
            for expected, value in zip([8.0 / 12, 8.0 / 12, 0.5, 1.0, 10.5], values):
                self.assertAlmostEqual(expected, value, 6, engine)
            error = run(
                "from pyrevit.revit import units\nunits.parse_slope('8:0')",
                engine=engine,
            )["error"]
            self.assertEqual("PyRevitException", error["type"], engine)


FAMILY_HELPERS_SCRIPT = """
import os
from pyrevit import PyRevitException
from pyrevit.revit.db import create, query, update

ENGLISH_TEMPLATES = ("Metric Generic Model.rft", "Generic Model.rft")


def english_templates():
    return sorted(
        os.path.join(folder, name)
        for folder, _, files in os.walk(app.FamilyTemplatePath)
        for name in files
        if name in ENGLISH_TEMPLATES
    )


def is_unhosted_generic_model(path):
    scratch = app.NewFamilyDocument(path)
    try:
        family = scratch.OwnerFamily
        generic_model = DB.ElementId(DB.BuiltInCategory.OST_GenericModel)
        return (
            family.FamilyCategory.Id == generic_model
            and family.FamilyPlacementType == DB.FamilyPlacementType.OneLevelBased
        )
    finally:
        scratch.Close(False)


def localized_templates():
    language = str(app.Language)
    for folder, _, files in sorted(os.walk(app.FamilyTemplatePath)):
        folder_name = os.path.basename(folder.rstrip("/" + os.sep))
        if not folder_name or folder_name.split("-")[0] not in language:
            continue
        names = sorted(
            (n for n in files if n.lower().endswith(".rft")),
            key=lambda n: (len(n), n),
        )
        for name in names:
            if is_unhosted_generic_model(os.path.join(folder, name)):
                return [os.path.join(folder, name)]
    return []


def message_of(action):
    try:
        action()
    except PyRevitException as ex:
        return str(ex)
    return None


def add_length_parameter(fm, name):
    if hasattr(DB, "GroupTypeId"):
        return fm.AddParameter(name, DB.GroupTypeId.Geometry, DB.SpecTypeId.Length, False)
    return fm.AddParameter(name, DB.BuiltInParameterGroup.PG_GEOMETRY, DB.ParameterType.Length, False)


def floor_plan(fam_doc):
    return [
        v for v in DB.FilteredElementCollector(fam_doc).OfClass(DB.ViewPlan)
        if not v.IsTemplate and v.ViewType == DB.ViewType.FloorPlan
    ][0]


def reference_rules(fam_doc):
    plan = floor_plan(fam_doc)
    reference_of = lambda plane: plane.get_Parameter(DB.BuiltInParameter.ELEM_REFERENCE_NAME).AsInteger()
    t = DB.Transaction(fam_doc, "Reference rules")
    try:
        t.Start()
        first = create.create_reference_plane("First", (-1, -2), (-1, 2), plan, reference="left", doc=fam_doc)
        create.create_reference_plane("Second", (-3, -2), (-3, 2), plan, reference="left", doc=fam_doc)
        found = {
            "left_owner": query.get_reference_plane("left", doc=fam_doc).Name,
            "left_taken_from_first": reference_of(first),
        }
        create.create_reference_plane("Strong 1", (-4, -2), (-4, 2), plan, reference="strong", doc=fam_doc)
        create.create_reference_plane("Strong 2", (-5, -2), (-5, 2), plan, reference="strong", doc=fam_doc)
        found["ambiguous_reference"] = message_of(lambda: query.get_reference_plane("strong", doc=fam_doc))
        return found
    finally:
        if t.GetStatus() == DB.TransactionStatus.Started:
            t.RollBack()


def build_box(fam_doc):
    fm = fam_doc.FamilyManager
    plan = floor_plan(fam_doc)
    centre = query.get_reference_plane("center_left_right", doc=fam_doc)
    found = {}
    t = DB.Transaction(fam_doc, "Build box")
    try:
        t.Start()
        width = add_length_parameter(fm, "Width")
        fm.NewType("Default")
        fm.Set(width, 2.0)
        left = create.create_reference_plane("Left", (-1, -2), (-1, 2), plan, reference="left", doc=fam_doc)
        right = create.create_reference_plane("Right", (1, -2), (1, 2), plan, reference="right", doc=fam_doc)
        fam_doc.Regenerate()
        found["reference"] = left.get_Parameter(DB.BuiltInParameter.ELEM_REFERENCE_NAME).AsInteger()
        found["centre_reference"] = centre.get_Parameter(DB.BuiltInParameter.ELEM_REFERENCE_NAME).AsInteger()
        found["unknown_reference"] = message_of(lambda: query.get_reference_plane("middle", doc=fam_doc))
        found["missing_reference"] = message_of(lambda: query.get_reference_plane("top", doc=fam_doc))
        found["found_left"] = query.get_reference_plane("left", doc=fam_doc).Name
        found["three_plane_label"] = message_of(
            lambda: create.create_labelled_dimension(
                plan, [left, centre, right], (-1, -3), (1, -3), label=width, doc=fam_doc
            )
        )
        found["two_plane_equal"] = message_of(
            lambda: create.create_labelled_dimension(
                plan, [left, right], (-1, -3), (1, -3), equal_segments=True, doc=fam_doc
            )
        )
        create.create_labelled_dimension(plan, [left, right], (-1, -1.5), (1, -1.5), label=width, doc=fam_doc)
        create.create_labelled_dimension(
            plan, [left, centre, right], (-1, -2.5), (1, -2.5),
            equal_segments=True, doc=fam_doc,
        )
        level = DB.FilteredElementCollector(fam_doc).OfClass(DB.Level).FirstElement()
        sketch_plane = DB.SketchPlane.Create(fam_doc, level.GetPlaneReference())
        profile = DB.CurveArrArray()
        profile.Append(create.create_curve_array([(-1, -0.5), (1, -0.5), (1, 0.5), (-1, 0.5)]))
        extrusion = fam_doc.FamilyCreate.NewExtrusion(True, profile, sketch_plane, 3.0)
        fam_doc.Regenerate()
        found["aligned"] = sorted(create.align_faces_to_planes(extrusion, plan, [left, right], doc=fam_doc))
        found["formula_error"] = message_of(lambda: update.set_formula(fm, width, "Depth <= 5"))
        t.Commit()

        flex = DB.Transaction(fam_doc, "Flex")
        try:
            flex.Start()
            fm.Set(width, 4.0)
            fam_doc.Regenerate()
            flex.Commit()
        except Exception:
            if flex.GetStatus() == DB.TransactionStatus.Started:
                flex.RollBack()
            raise
        box = extrusion.get_BoundingBox(None)
        found["width_after_flex"] = round(box.Max.X - box.Min.X, 3)
    except Exception:
        if t.GetStatus() == DB.TransactionStatus.Started:
            t.RollBack()
        raise
    return found


def load_into_project(fam_doc, second_doc, project):
    out = {}
    family = create.load_family_document(fam_doc, doc=project, name="Helper Box")
    out["loaded_name"] = family.Name
    out["duplicate_name"] = message_of(
        lambda: create.load_family_document(second_doc, doc=project, name="Helper Box")
    )
    create.load_family_document(second_doc, doc=project)
    out["overwrite_refusal"] = message_of(
        lambda: create.load_family_document(second_doc, doc=project, name="Other Box")
    )
    family_names = sorted(
        f.Name for f in DB.FilteredElementCollector(project).OfClass(DB.Family)
    )
    out["existing_family_survived"] = second_doc.Title in family_names
    out["target_left_open_transaction"] = project.IsModifiable
    out["families_after_refusal"] = [
        name for name in family_names if name in ("Helper Box", "Other Box")
    ]
    return out


def run_template(template):
    units = DB.UnitSystem.Imperial if "Imperial" in template else DB.UnitSystem.Metric
    fam_doc = second_doc = project = None
    try:
        fam_doc = app.NewFamilyDocument(template)
        second_doc = app.NewFamilyDocument(template)
        project = app.NewProjectDocument(units)
        out = build_box(fam_doc)
        out.update(reference_rules(second_doc))
        out.update(load_into_project(fam_doc, second_doc, project))
        return out
    finally:
        for opened in (fam_doc, second_doc, project):
            if opened is not None:
                opened.Close(False)


templates = english_templates() or localized_templates()
result = dict(
    (os.path.basename(os.path.dirname(t)) + "/" + os.path.basename(t), run_template(t))
    for t in templates
)
"""


class FamilyHelperTests(TestCase):
    """The family authoring helpers, run in scratch family documents on both engines."""

    def test_family_box_follows_its_parameters_and_helpers_refuse_bad_input(self):
        """A family built with the helpers flexes, and the helpers refuse bad input cleanly.

        Runs for every Generic Model template it can find (metric and imperial in
        English Revit, the template of the Revit language otherwise), so units and
        language folders are covered by whatever the installation has.
        """
        for engine in ENGINES:
            runs = run(FAMILY_HELPERS_SCRIPT, engine=engine)["result"]
            if not runs:
                self.skipTest("No unhosted Generic Model family template found.")
            for template, result in runs.items():
                label = "{} {}".format(engine, template)
                self.assertEqual(0, result["reference"], label)
                self.assertEqual(1, result["centre_reference"], label)
                self.assertEqual("Left", result["found_left"], label)
                self.assertIn("one of", result["unknown_reference"], label)
                self.assertIn("found 0", result["missing_reference"], label)
                self.assertEqual("Second", result["left_owner"], label)
                self.assertEqual(12, result["left_taken_from_first"], label)
                self.assertIn("found 2", result["ambiguous_reference"], label)
                self.assertEqual(["Left", "Right"], result["aligned"], label)
                self.assertAlmostEqual(4.0, result["width_after_flex"], 3, label)
                self.assertIn("separate dimension", result["three_plane_label"], label)
                self.assertIn("at least three", result["two_plane_equal"], label)
                self.assertIn("'Width'", result["formula_error"], label)
                self.assertIn("not(a > b)", result["formula_error"], label)
                self.assertEqual("Helper Box", result["loaded_name"], label)
                self.assertIn("already exists", result["duplicate_name"], label)
                self.assertIn("would overwrite", result["overwrite_refusal"], label)
                self.assertTrue(result["existing_family_survived"], label)
                self.assertFalse(result["target_left_open_transaction"], label)
                self.assertEqual(
                    ["Helper Box"], result["families_after_refusal"], label
                )


def _write_skill(root, folder, description, body):
    path = op.join(root, folder)
    os.makedirs(path)
    with open(op.join(path, "SKILL.md"), "w") as handle:
        handle.write(
            "---\nname: {}\ndescription: {}\n---\n{}\n".format(
                folder, description, body
            )
        )
    return path
