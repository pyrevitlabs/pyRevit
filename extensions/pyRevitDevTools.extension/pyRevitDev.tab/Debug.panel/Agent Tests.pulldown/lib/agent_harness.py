"""Drive the pyRevit agent host from inside Revit for the Agent Tests buttons.

Requests go through ``AgentHost.HandleRequest``: the same JSON-RPC requests the
pipe carries, executed synchronously on the Revit main thread, so a command can
exercise the runtime end to end without an external client.

Tests run against scratch documents this module creates in the temp folder and
closes again, never against the user's model. Every suite runs with agent
sessions required and a session started on the scratch project, the way a user
would start one in Revit.
"""

import json
import os
import os.path as op
import platform
import shutil
import sys
import tempfile
from contextlib import contextmanager
from unittest import TestCase as _TestCase

import clr

for _assembly in (
    "System",
    "System.Core",
    "System.Diagnostics.Process",
    "System.IO.Pipes",
):
    try:
        clr.AddReference(_assembly)
    except Exception:
        pass

import System
from System.Diagnostics import Process, ProcessStartInfo

from pyrevit import DB, HOME_DIR, HOST_APP
from pyrevit.coreutils import assmutils
from pyrevit.labs import Common, PyRevit
from pyrevit.runtime import RUNTIME_ASSM
from pyrevit.unittests.runner import run_module_tests

COMMENTS = "DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS"
CPYTHON_HOST = platform.python_implementation() == "CPython"
ENGINES = ("ironpython",) if CPYTHON_HOST else ("ironpython", "cpython")

CLI = op.join(HOME_DIR, "bin", "pyrevit.exe")
CLI_TIMEOUT_MS = 60000
PROGRESS_LOG = op.join(tempfile.gettempdir(), "pyrevit-agent-tests.log")

_HOST_TYPE = assmutils.find_type_by_name(
    RUNTIME_ASSM, "PyRevitLabs.PyRevit.Runtime.Agent.AgentHost"
)
_SESSIONS_TYPE = assmutils.find_type_by_name(
    RUNTIME_ASSM, "PyRevitLabs.PyRevit.Runtime.Agent.AgentSessions"
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


def host_running():
    """Whether the agent host started its pipe in this Revit session."""
    return bool(_HOST_TYPE.GetProperty("IsRunning").GetValue(None))


def _sessions(name, *args):
    """Call a static method of ``AgentSessions``, the in-process session controls.

    Raises:
        AgentRequestError: when the host refuses with an ``AgentException``.
    """
    method = _SESSIONS_TYPE.GetMethod(name)
    try:
        return method.Invoke(None, System.Array[System.Object](list(args)))
    except System.Exception as error:
        refusal = getattr(error, "InnerException", None) or error
        code = getattr(refusal, "Code", None)
        if code is None:
            raise
        raise AgentRequestError(str(code), str(refusal.Message))


def start_session():
    """Start an agent session on the active document, as the user does in Revit."""
    return str(_sessions("Start", HOST_APP.uiapp))


def end_session():
    """End the agent session, if there is one."""
    _sessions("End")


def resume_session():
    """Resume a paused agent session."""
    _sessions("Resume")


def sessions_required():
    """Whether model requests need an active agent session."""
    return bool(_SESSIONS_TYPE.GetProperty("Required").GetValue(None))


def require_sessions(state):
    """Require an agent session for model requests, or stop requiring one."""
    _sessions("SetRequired", bool(state))


def session_status():
    """The host's description of the agent session."""
    return request("session_status")


def restore_session():
    """Leave sessions required and a session active on the scratch project.

    Tests that change the session call this afterwards, so the next test starts
    from the state ``run_suites`` set up.
    """
    require_sessions(True)
    scratch = session()
    if session_status()["document"] not in (None, scratch.project.Title):
        end_session()
    scratch.activate(scratch.project_path)
    state = session_status()["state"]
    if state == "paused":
        resume_session()
    elif state == "inactive":
        start_session()


def pipe_name():
    """The name of the host's named pipe."""
    return str(_HOST_TYPE.GetProperty("PipeName").GetValue(None))


def agent_dir():
    """The folder holding host registrations, run records and captures."""
    return op.join(str(Common.PyRevitLabsConsts.PyRevitPath), "agent")


def run_cli(*arguments):
    """Run the attached clone's ``pyrevit`` CLI and return its output text."""
    info = ProcessStartInfo(CLI, " ".join(arguments))
    info.UseShellExecute = False
    info.RedirectStandardOutput = True
    info.CreateNoWindow = True
    process = Process.Start(info)
    reading = process.StandardOutput.ReadToEndAsync()
    if not reading.Wait(CLI_TIMEOUT_MS):
        process.Kill()
        raise AssertionError(
            "pyrevit {} did not finish within {} ms".format(
                " ".join(arguments), CLI_TIMEOUT_MS
            )
        )
    process.WaitForExit(CLI_TIMEOUT_MS)
    return str(reading.Result)


def log_progress(text):
    """Append a line to the progress log, which survives a hung or killed Revit."""
    with open(PROGRESS_LOG, "a") as handle:
        handle.write(text + "\n")


class TestCase(_TestCase):
    """Base class of the agent tests: records each test before it starts.

    If Revit hangs, the last line of the progress log names the test that was
    running.
    """

    def run(self, result=None):
        """Log the test id, then run the test."""
        log_progress(self.id())
        return _TestCase.run(self, result)


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

    Important: the tests start and end their own session, so they refuse to run while
    the user has one open rather than end it.

    Raises:
        AssertionError: when an agent session is already open, or when any module has
            failures or errors; the details are already in the output window.
    """
    global _session
    print("Host engine: {}".format(sys.version.split()[0]))
    open_session = session_status()
    if open_session["state"] != "inactive":
        raise AssertionError(
            "End the agent session on '{}' in the agent panel first: the tests start "
            "their own session on scratch documents.".format(open_session["document"])
        )
    with open(PROGRESS_LOG, "w") as handle:
        handle.write("progress log of the last agent test run\n")
    _session = ScratchSession()
    problems = []
    required = sessions_required()
    try:
        _session.open()
        require_sessions(True)
        start_session()
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
        end_session()
        require_sessions(required)
        _session.close()
        _session = None
        log_progress("finished")
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
            id_value(wall.Id)
            for wall in DB.FilteredElementCollector(self.project).OfClass(DB.Wall)
        ]

    def activate(self, path):
        """Make the open project at ``path`` the active document."""
        if not self._is_active_path(path):
            self.uiapp.OpenAndActivateDocument(path)

    def create_extra(self, file_name):
        """Create and save one more empty project in the scratch folder; return its path."""
        path = op.join(self.folder, file_name)
        self._create(path, with_walls=False)
        return path

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

    def _is_active_path(self, path):
        uidoc = self.uiapp.ActiveUIDocument
        return uidoc is not None and op.normcase(
            str(uidoc.Document.PathName)
        ) == op.normcase(path)

    def _reactivate_original(self):
        if not self.original_path or not op.exists(self.original_path):
            return False
        try:
            self.uiapp.OpenAndActivateDocument(self.original_path)
            return True
        except Exception:
            return False


def id_value(element_id):
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
