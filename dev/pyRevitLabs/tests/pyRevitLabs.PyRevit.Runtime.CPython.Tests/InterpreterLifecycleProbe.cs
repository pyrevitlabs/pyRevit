using Python.Runtime;
using CpyRuntime = Python.Runtime.Runtime;

namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// What one pass over the interpreter lifecycle observed, recorded step by step so the facts
/// asserting on it do not depend on each other's execution order.
/// </summary>
internal sealed class InterpreterLifecycleRecord {
    public required bool BroughtUp { get; init; }
    public required IReadOnlyList<Exception> ReattachFailures { get; init; }
    public required int? MarkerAfterReattaches { get; init; }
    public required Exception? PythonDllReassignment { get; init; }
    public required Exception? Shutdown { get; init; }
    public required bool IsInitializedAfterShutdown { get; init; }
}

/// <summary>
/// Drives the vendored pythonnet through the interpreter lifecycle that <c>CPythonEngine</c> relies
/// on, recording what happened.
/// </summary>
/// <remarks>
/// pythonnet's runtime is a process-wide singleton, so the lifecycle can only be walked once per
/// process. The walk runs once, on first use, and in a fixed order: the re-attach phase must come
/// before the shutdown phase, because the shutdown phase is expected to damage the runtime.
/// </remarks>
internal static class InterpreterLifecycleProbe {
    public const int ReattachCount = 3;

    private const string MarkerName = "pyrevit_reload_probe";
    private static readonly string MarkerRead = $"__import__('sys').{MarkerName}";

    private static readonly Lazy<InterpreterLifecycleRecord> _record = new(
        Walk, LazyThreadSafetyMode.ExecutionAndPublication);

    public static InterpreterLifecycleRecord Record => _record.Value;

    private static InterpreterLifecycleRecord Walk() {
        string pythonDll = Path.Combine(AppContext.BaseDirectory, "CPY3123", "python312.dll");
        Assert.True(File.Exists(pythonDll), $"CPython engine fixture missing: {pythonDll}");

        CpyRuntime.PythonDLL = pythonDll;
        PythonEngine.Initialize();
        bool broughtUp = PythonEngine.IsInitialized;
        Exec("import clr");
        Exec($"import sys; sys.{MarkerName} = 1");

        var reattachFailures = new List<Exception>();
        for (int cycle = 0; cycle < ReattachCount; cycle++) {
            try {
                Assert.True(PythonEngine.IsInitialized, "interpreter reported as not initialized");
                PythonEngine.Initialize();
                Assert.True(PythonEngine.IsInitialized, "interpreter reported as not initialized after Initialize");
                Exec($"import sys; sys.{MarkerName} += 1");
                Exec("import clr");
            }
            catch (Exception ex) {
                reattachFailures.Add(new InvalidOperationException($"cycle {cycle}: {ex.Message}", ex));
            }
        }

        int? marker = reattachFailures.Count == 0 ? ReadMarker() : null;

        Exception pythonDllReassignment = Capture(() => CpyRuntime.PythonDLL = pythonDll);
        Exception shutdown = Capture(PythonEngine.Shutdown);
        bool isInitializedAfterShutdown = PythonEngine.IsInitialized;

        return new InterpreterLifecycleRecord {
            BroughtUp = broughtUp,
            ReattachFailures = reattachFailures,
            MarkerAfterReattaches = marker,
            PythonDllReassignment = pythonDllReassignment,
            Shutdown = shutdown,
            IsInitializedAfterShutdown = isInitializedAfterShutdown,
        };
    }

    private static int? ReadMarker() {
        using Py.GILState gil = Py.GIL();
        using PyObject? value = PythonEngine.Eval(MarkerRead);
        return value is null ? null : Convert.ToInt32(value);
    }

    private static void Exec(string code) {
        using Py.GILState gil = Py.GIL();
        PythonEngine.Exec(code);
    }

    private static Exception? Capture(Action action) {
        try {
            action();
            return null;
        }
        catch (Exception ex) {
            return ex;
        }
    }
}
