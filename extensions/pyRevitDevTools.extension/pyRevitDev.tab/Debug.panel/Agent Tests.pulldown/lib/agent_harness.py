"""Drive the pyRevit agent host from inside Revit for the Agent Tests buttons.

Requests go through ``AgentHost.HandleRequest``: the same JSON-RPC requests the
pipe carries, executed synchronously on the Revit main thread, so a command can
exercise the runtime end to end without an external client.

Tests run against scratch documents this module creates in the temp folder and
closes again, never against the user's model.
"""

import json
import os
import os.path as op
import platform
import shutil
import sys
import tempfile
from contextlib import contextmanager

import System

from pyrevit import DB, HOST_APP
from pyrevit.coreutils import assmutils
from pyrevit.labs import PyRevit
from pyrevit.runtime import RUNTIME_ASSM
from pyrevit.unittests.runner import run_module_tests

COMMENTS = "DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS"
CPYTHON_HOST = platform.python_implementation() == "CPython"
ENGINES = ("ironpython",) if CPYTHON_HOST else ("ironpython", "cpython")

_HOST_TYPE = assmutils.find_type_by_name(
    RUNTIME_ASSM, "PyRevitLabs.PyRevit.Runtime.Agent.AgentHost"
)
_session = None


class AgentRequestError(Exception):
    """A JSON-RPC error returned by the agent host; ``code`` is its ``data.type``."""

    def __init__(self, code, message):
        Exception.__init__(self, "{}: {}".format(code, message))
        self.code = code
        self.message = message


def request(method, **params):
    """Send one request to the agent host and return its ``result``.

    Raises:
        AgentRequestError: when the host answers with a JSON-RPC error.
    """
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    )
    saved = _save_interpreter_state()
    try:
        handle = _HOST_TYPE.GetMethod("HandleRequest")
        args = System.Array[System.Object]([HOST_APP.uiapp, payload])
        response = json.loads(str(handle.Invoke(None, args)))
    finally:
        _restore_interpreter_state(saved)
    if "error" in response:
        error = response["error"]
        raise AgentRequestError(
            (error.get("data") or {}).get("type", "unknown"), error.get("message")
        )
    return response["result"]


def run(script, mode="query", engine=None, inputs=None, timeout=None, **extra):
    """Run an agent script and return the run response."""
    params = dict(extra, script=script, mode=mode)
    if engine:
        params["engine"] = engine
    if inputs is not None:
        params["inputs"] = inputs
    if timeout is not None:
        params["timeout_s"] = timeout
    return request("run", **params)


def comment(element_id):
    """The Comments value of an element in the active document, read through a query run."""
    return run(
        "result = doc.GetElement(DB.ElementId(inputs['id']))"
        ".get_Parameter({}).AsString()".format(COMMENTS),
        inputs={"id": element_id},
    ).get("result")


def set_comment_script():
    """Agent script that sets the Comments of ``inputs['id']`` to ``inputs['text']``."""
    return (
        "t = DB.Transaction(doc, 'agent test comment')\n"
        "t.Start()\n"
        "doc.GetElement(DB.ElementId(inputs['id'])).get_Parameter({})"
        ".Set(inputs['text'])\n"
        "t.Commit()\n".format(COMMENTS)
    )


def session():
    """The scratch documents of the current button run."""
    if _session is None:
        raise RuntimeError("Run the tests through agent_harness.run_suites.")
    return _session


@contextmanager
def policy(name):
    """Set the agent policy for the block, restoring the previous value after."""
    previous = PyRevit.PyRevitConfigs.GetAgentPolicy()
    PyRevit.PyRevitConfigs.SetAgentPolicy(name)
    try:
        yield
    finally:
        PyRevit.PyRevitConfigs.SetAgentPolicy(previous)


def run_suites(modules):
    """Run test modules against fresh scratch documents and fail the button on any failure.

    Raises:
        AssertionError: when any module has failures or errors; the details are
            already in the output window.
    """
    global _session
    print("Host engine: {}".format(sys.version.split()[0]))
    _session = ScratchSession()
    problems = []
    try:
        _session.open()
        with policy("auto"):
            for module in modules:
                result = run_module_tests(module)
                if result.failures or result.errors:
                    problems.append(
                        "{} (failures={}, errors={})".format(
                            module.__name__, len(result.failures), len(result.errors)
                        )
                    )
    finally:
        _session.close()
        _session = None
    if problems:
        raise AssertionError("Agent test failures: " + "; ".join(problems))
    print("All agent test modules passed.")


class ScratchSession(object):
    """Two throwaway projects: the active one the tests change, and one more open beside it."""

    def __init__(self):
        self.uiapp = HOST_APP.uiapp
        self.app = self.uiapp.Application
        uidoc = self.uiapp.ActiveUIDocument
        self.original_path = uidoc.Document.PathName if uidoc else None
        self.folder = tempfile.mkdtemp(prefix="pyrevit-agent-tests-")
        self.project_path = op.join(self.folder, "agent-test-project.rvt")
        self.other_path = op.join(self.folder, "agent-test-other.rvt")
        self.project = None
        self.other = None
        self.wall_ids = []
        self.level_id = None

    @property
    def project_title(self):
        """Title of the active scratch project."""
        return op.splitext(op.basename(self.project_path))[0]

    @property
    def other_title(self):
        """Title of the scratch project open beside it."""
        return op.splitext(op.basename(self.other_path))[0]

    def open(self):
        """Create and save both projects, open them, and make the test project active."""
        self._create(self.other_path, with_walls=False)
        self._create(self.project_path, with_walls=True)
        self.other = self.uiapp.OpenAndActivateDocument(self.other_path).Document
        self.project = self.uiapp.OpenAndActivateDocument(self.project_path).Document
        self.level_id = (
            DB.FilteredElementCollector(self.project).OfClass(DB.Level).FirstElementId()
        )
        self.wall_ids = [
            _id_value(wall.Id)
            for wall in DB.FilteredElementCollector(self.project).OfClass(DB.Wall)
        ]

    def close(self):
        """Close both projects without saving, reactivating the original document first."""
        for document in (self.project, self.other):
            if document is None or not document.IsValidObject:
                continue
            if self._is_active(document) and not self._reactivate_original():
                print(
                    "Left {} open: Revit can't close the active document, and no saved "
                    "document was open before the tests. Close it without saving.".format(
                        document.Title
                    )
                )
                continue
            try:
                document.Close(False)
            except Exception as ex:
                print("Could not close {}: {}".format(document.Title, ex))
        shutil.rmtree(self.folder, ignore_errors=True)

    def _create(self, path, with_walls):
        template = self.app.DefaultProjectTemplate
        if template and op.exists(template):
            document = self.app.NewProjectDocument(template)
        else:
            document = self.app.NewProjectDocument(DB.UnitSystem.Metric)
        transaction = DB.Transaction(document, "agent test model")
        transaction.Start()
        level = DB.FilteredElementCollector(document).OfClass(DB.Level).FirstElement()
        if level is None:
            level = DB.Level.Create(document, 0.0)
        if with_walls:
            for start, end in (((0, 0, 0), (20, 0, 0)), ((20, 0, 0), (20, 15, 0))):
                line = DB.Line.CreateBound(DB.XYZ(*start), DB.XYZ(*end))
                DB.Wall.Create(document, line, level.Id, False)
        transaction.Commit()
        options = DB.SaveAsOptions()
        options.OverwriteExistingFile = True
        document.SaveAs(path, options)
        document.Close(False)

    def _is_active(self, document):
        uidoc = self.uiapp.ActiveUIDocument
        return uidoc is not None and uidoc.Document.Equals(document)

    def _reactivate_original(self):
        if not self.original_path or not op.exists(self.original_path):
            return False
        try:
            self.uiapp.OpenAndActivateDocument(self.original_path)
            return True
        except Exception:
            return False


def _id_value(element_id):
    """The numeric id as a Python int; ``ElementId.Value`` is an Int64 that ``json`` rejects."""
    value = getattr(element_id, "Value", None)
    return int(value if value is not None else element_id.IntegerValue)


def _save_interpreter_state():
    if not CPYTHON_HOST:
        return None
    return (sys.stdout, sys.stderr, list(sys.path), list(sys.argv), sys.gettrace())


def _restore_interpreter_state(saved):
    if saved is None:
        return
    sys.stdout, sys.stderr, path, argv, trace = saved
    sys.path[:] = path
    sys.argv[:] = argv
    sys.settrace(trace)


def write_module(folder, name, text):
    """Write ``name.py`` into ``folder``, creating the folder when needed."""
    if not op.isdir(folder):
        os.makedirs(folder)
    with open(op.join(folder, name + ".py"), "w") as handle:
        handle.write(text)
