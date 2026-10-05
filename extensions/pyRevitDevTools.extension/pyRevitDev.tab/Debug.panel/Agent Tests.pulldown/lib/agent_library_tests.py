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
