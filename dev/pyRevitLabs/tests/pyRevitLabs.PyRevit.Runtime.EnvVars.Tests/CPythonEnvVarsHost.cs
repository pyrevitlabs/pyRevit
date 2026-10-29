using System.Reflection;
using IronPython.Runtime;
using Python.Runtime;
using CpyRuntime = Python.Runtime.Runtime;

namespace PyRevitLabs.PyRevit.Runtime.EnvVars.Tests;

/// <summary>
/// Hosts the shipped CPython engine through the vendored pythonnet with
/// <c>pyrevit/coreutils/envvars.py</c> loaded, in a process where no IronPython engine has ever
/// been created: the state of a <c>pyrevit run</c> runner process executing a <c>#! python3</c>
/// script.
/// </summary>
/// <remarks>
/// pythonnet's runtime is a process-wide singleton and IronPython's default context is a
/// process-wide static, so nothing in this assembly may shut the interpreter down or create an
/// IronPython engine.
/// </remarks>
internal static class CPythonEnvVarsHost {
    public const string EnvVarsDictKey = "PYREVITEnvVarsDict";

    private static readonly Lazy<PyDict> _globals = new(Start, LazyThreadSafetyMode.ExecutionAndPublication);

    public static void EnsureStarted() => _ = _globals.Value;

    public static bool IronPythonDefaultContextInitialized {
        get {
            FieldInfo? defaultContext = typeof(PythonDictionary).Assembly
                .GetType("IronPython.Runtime.DefaultContext")
                ?.GetField("_default", BindingFlags.NonPublic | BindingFlags.Static);
            Assert.NotNull(defaultContext);
            return defaultContext.GetValue(null) is not null;
        }
    }

    /// <summary>
    /// Stores a fresh dictionary seeded with string keys only, as <c>EnvDictionary.Seed</c> and
    /// the runner's <c>SeedEnvDictionary</c> do.
    /// </summary>
    public static PythonDictionary SeedEnvDictionary() {
        var envData = new PythonDictionary {
            ["PYREVIT_UUID"] = "seeded-uuid",
            ["PYREVIT_APPVERSION"] = "2026",
            ["PYREVIT_HOOKS"] = new Dictionary<string, Dictionary<string, string>>(),
        };
        AppDomain.CurrentDomain.SetData(EnvVarsDictKey, envData);
        return envData;
    }

    public static void Exec(string code) {
        PyDict globals = _globals.Value;
        using Py.GILState gil = Py.GIL();
        PythonEngine.Exec(code, globals);
    }

    public static string? EvalString(string expression) {
        PyDict globals = _globals.Value;
        using Py.GILState gil = Py.GIL();
        using PyObject result = PythonEngine.Eval(expression, globals);
        return result.IsNone() ? null : result.As<string>();
    }

    private static PyDict Start() {
        string pythonDll = Path.Combine(AppContext.BaseDirectory, "CPY3123", "python312.dll");
        Assert.True(File.Exists(pythonDll), $"CPython engine fixture missing: {pythonDll}");
        string envVarsPath = Path.Combine(AppContext.BaseDirectory, "Sources", "envvars.py");
        Assert.True(File.Exists(envVarsPath), $"envvars.py fixture missing: {envVarsPath}");

        CpyRuntime.PythonDLL = pythonDll;
        PythonEngine.Initialize();
        using Py.GILState gil = Py.GIL();
        var globals = new PyDict();
        PythonEngine.Exec($$"""
            import sys, types, importlib.util
            import clr
            from System import AppDomain

            def _stub(name, **attrs):
                module = types.ModuleType(name)
                module.__dict__.update(attrs)
                sys.modules[name] = module
                return module

            class _Consts:
                ProductName = "pyRevit"

            _stub("pyrevit")
            _stub("pyrevit.compat", IRONPY=False)
            _stub("pyrevit.framework", AppDomain=AppDomain)
            _stub("pyrevit.labs", Common=types.SimpleNamespace(PyRevitLabsConsts=_Consts))

            _spec = importlib.util.spec_from_file_location("envvars", r"{{envVarsPath}}")
            envvars = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(envvars)
            """, globals);
        return globals;
    }
}
