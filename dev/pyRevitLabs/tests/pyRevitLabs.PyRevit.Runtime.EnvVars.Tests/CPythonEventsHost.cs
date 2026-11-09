using Python.Runtime;

namespace PyRevitLabs.PyRevit.Runtime.EnvVars.Tests;

/// <summary>
/// One event shared by every wrapper, standing in for the native Revit application event.
/// </summary>
public sealed class SharedEventSource {
    private EventHandler<EventArgs>? _documentChanged;

    /// <summary>Number of delegates still subscribed to the shared event.</summary>
    public int SubscriberCount => _documentChanged?.GetInvocationList().Length ?? 0;

    /// <summary>
    /// Returns a new wrapper on every call, as Revit returns a new <c>Application</c> object on
    /// every <c>UIApplication.Application</c> access.
    /// </summary>
    public FreshAppWrapper NewWrapper() => new(this);

    /// <summary>Raises the shared event once.</summary>
    public void Raise() => _documentChanged?.Invoke(this, EventArgs.Empty);

    internal void Add(EventHandler<EventArgs> handler) => _documentChanged += handler;

    internal void Remove(EventHandler<EventArgs> handler) => _documentChanged -= handler;
}

/// <summary>
/// A per-access wrapper whose event forwards to the shared source, like Revit's
/// <c>Application.DocumentChanged</c>.
/// </summary>
public sealed class FreshAppWrapper {
    private readonly SharedEventSource _source;

    internal FreshAppWrapper(SharedEventSource source) => _source = source;

    /// <summary>Forwards subscriptions to the shared source.</summary>
    public event EventHandler<EventArgs> DocumentChanged {
        add => _source.Add(value);
        remove => _source.Remove(value);
    }
}

/// <summary>
/// Stands in for Revit's <c>IExternalEventHandler</c>, so the Python handler classes in
/// <c>events.py</c> make pythonnet emit derived CLR types as they do in Revit.
/// </summary>
public interface IExternalEventHandler {
    /// <summary>Runs the handler.</summary>
    void Execute(object app);

    /// <summary>Names the handler.</summary>
    string GetName();
}

/// <summary>
/// Loads <c>pyrevit/revit/events.py</c> into the CPython engine started by
/// <see cref="CPythonEnvVarsHost"/>, with a <c>HOST_APP</c> whose <c>app</c> is a fresh
/// <see cref="FreshAppWrapper"/> on every access.
/// </summary>
internal static class CPythonEventsHost {
    private static readonly Lazy<PyDict> _globals = new(Start, LazyThreadSafetyMode.ExecutionAndPublication);

    /// <summary>Gives the loaded module a new shared event source and returns it.</summary>
    public static SharedEventSource NewSource() {
        var source = new SharedEventSource();
        PyDict globals = _globals.Value;
        using Py.GILState gil = Py.GIL();
        globals["source"] = source.ToPython();
        return source;
    }

    /// <summary>Runs Python statements where <c>events</c> and <c>HOST_APP</c> are defined.</summary>
    public static void Exec(string code) {
        PyDict globals = _globals.Value;
        using Py.GILState gil = Py.GIL();
        PythonEngine.Exec(code, globals);
    }

    /// <summary>Evaluates a Python expression that yields an int.</summary>
    public static int EvalInt(string expression) {
        PyDict globals = _globals.Value;
        using Py.GILState gil = Py.GIL();
        using PyObject result = PythonEngine.Eval(expression, globals);
        return result.As<int>();
    }

    private static PyDict Start() {
        CPythonEnvVarsHost.EnsureStarted();
        string eventsPath = Path.Combine(AppContext.BaseDirectory, "Sources", "events.py");
        Assert.True(File.Exists(eventsPath), $"events.py fixture missing: {eventsPath}");

        using Py.GILState gil = Py.GIL();
        var globals = new PyDict();
        PythonEngine.Exec($$"""
            import sys, types, logging, importlib.util
            import clr
            from System import AppDomain, EventArgs, EventHandler
            clr.AddReference("{{typeof(IExternalEventHandler).Assembly.GetName().Name}}")
            from {{typeof(IExternalEventHandler).Namespace}} import IExternalEventHandler

            def _stub(name, **attrs):
                module = types.ModuleType(name)
                module.__dict__.update(attrs)
                sys.modules[name] = module
                return module

            class _HostApp(object):
                has_api_context = True

                @property
                def app(self):
                    return source.NewWrapper()

                @property
                def uiapp(self):
                    return source.NewWrapper()

                def is_older_than(self, version):
                    return False

            class _NoApiContextQueue(object):
                @staticmethod
                def Schedule(callback):
                    raise RuntimeError("no Revit API context")

            _args = dict(
                DocumentChangedEventArgs=EventArgs,
                DocumentClosedEventArgs=EventArgs,
                DocumentOpenedEventArgs=EventArgs,
                ViewActivatedEventArgs=EventArgs,
                SelectionChangedEventArgs=EventArgs,
            )
            HOST_APP = _HostApp()
            _stub(
                "pyrevit",
                HOST_APP=HOST_APP,
                EXEC_PARAMS=types.SimpleNamespace(exec_id="cpython-events-test"),
                DB=types.SimpleNamespace(Events=types.SimpleNamespace(**_args)),
                UI=types.SimpleNamespace(
                    Events=types.SimpleNamespace(**_args),
                    IExternalEventHandler=IExternalEventHandler,
                    ExternalEventRequest=types.SimpleNamespace(Denied="Denied", TimedOut="TimedOut"),
                ),
                framework=types.SimpleNamespace(AppDomain=AppDomain, EventHandler=EventHandler),
                compat=types.SimpleNamespace(IRONPY=False),
            )
            _envvars = _stub("pyrevit.coreutils.envvars", REGISTEREDEVENTHANDLERS_ENVVAR="PYREVIT_TEST_EVENTHANDLERS")
            _stub("pyrevit.coreutils", envvars=_envvars)
            _stub("pyrevit.coreutils.logger", get_logger=logging.getLogger)
            _runtime_types = _stub("pyrevit.runtime.types", ApiContextQueue=_NoApiContextQueue)
            _stub("pyrevit.runtime", types=_runtime_types)

            _spec = importlib.util.spec_from_file_location("events", r"{{eventsPath}}")
            events = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(events)
            """, globals);
        return globals;
    }
}
