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
    public required string? DerivedTypeRedefinition { get; init; }
    public required string? DerivedTypeShapes { get; init; }
    public required string? ImplicitInterfaceTypes { get; init; }
    public required string? TruthyBooleans { get; init; }
    public required IReadOnlyDictionary<string, string> ScriptOutputConversions { get; init; }
}

/// <summary>Base of <see cref="IDerivedProbe"/>, whose members a Python implementer must also receive.</summary>
public interface IBaseProbe {
    string Base();
}

/// <summary>An interface whose members come partly from <see cref="IBaseProbe"/>, like Revit's server interfaces.</summary>
public interface IDerivedProbe : IBaseProbe {
    string Derived();
}

/// <summary>Calls a Python implementation through both interfaces, as Revit calls a registered server.</summary>
public static class InheritedInterfaceCaller {
    public static string Call(IDerivedProbe probe) => probe.Base() + "+" + probe.Derived();
}

/// <summary>CLR members that receive Python values where IronPython converts by truthiness.</summary>
public sealed class TruthinessTarget {
    public bool Flag { get; set; }

    public bool? Maybe { get; set; } = true;

    public bool Field;

    public static string Pick(bool value) => "bool";

    public static string Pick(object value) => "object";

    public static string OnlyBool(bool value) => value.ToString();

    public static bool Ask(Func<bool> predicate) => predicate();
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

    private const string RedefinitionProbe = """
        import clr
        import sys
        from System import IDisposable

        def define(extra):
            class RedefinedProbe(IDisposable):
                __namespace__ = "pyrevit.tests.redefinition"

                def Dispose(self):
                    pass

                if extra:
                    @clr.clrmethod(int, [])
                    def Extra(self):
                        return 1

            return clr.GetClrType(RedefinedProbe)

        plain = define(False)
        extended = define(True)
        plain_again = define(False)
        sys.pyrevit_redefinition = "|".join([
            str(plain.Equals(plain_again)),
            str(extended.Equals(plain)),
            str(extended.GetMethod("Extra") is not None),
            str(plain.GetMethod("Extra") is not None),
        ])
        """;
    private const string ShapesProbe = """
        import clr
        import sys
        from System import IComparable, IDisposable

        def named():
            class NamedProbe(IDisposable):
                __namespace__ = "pyrevit.tests.naming"

                def Dispose(self):
                    pass

            return clr.GetClrType(NamedProbe)

        def generic():
            class GenericProbe(IComparable[int]):
                __namespace__ = "pyrevit.tests.naming"

                def CompareTo(self, other):
                    return 0

            return clr.GetClrType(GenericProbe)

        def with_property(writable):
            class PropertyProbe(IDisposable):
                __namespace__ = "pyrevit.tests.properties"

                def Dispose(self):
                    pass

                def _get(self):
                    return 1

                def _set(self, value):
                    pass

                Value = clr.clrproperty(int, _get, _set if writable else None)

            return clr.GetClrType(PropertyProbe)

        def in_assembly(name):
            class AssemblyProbe(IDisposable):
                __namespace__ = "pyrevit.tests.assemblies"
                __assembly__ = name

                def Dispose(self):
                    pass

            return clr.GetClrType(AssemblyProbe)

        first = named()
        from pyrevit.tests.naming import NamedProbe as Imported
        read_only = with_property(False)
        writable = with_property(True)
        first_assembly = in_assembly("pyrevit.tests.first")
        second_assembly = in_assembly("pyrevit.tests.second")
        sys.pyrevit_shapes = "|".join([
            first.FullName,
            str(clr.GetClrType(Imported).Equals(first)),
            generic().FullName,
            str(read_only.GetProperty("Value").CanWrite),
            str(writable.GetProperty("Value").CanWrite),
            first_assembly.Assembly.GetName().Name,
            second_assembly.Assembly.GetName().Name,
        ])
        """;
    private const string ImplicitInterfaceProbe = """
        import clr
        import sys
        from System import IComparable
        from System.Collections import Comparer

        def define():
            class ImplicitProbe(IComparable):
                def CompareTo(self, other):
                    return 7

            return ImplicitProbe

        first = define()
        second = define()
        built = type("BuiltProbe", (IComparable,), {"CompareTo": lambda self, other: 3})
        clr.AddReference("pyRevitLabs.PyRevit.Runtime.CPython.Tests")
        from PyRevitLabs.PyRevit.Runtime.CPython.Tests import IDerivedProbe, InheritedInterfaceCaller

        class InheritedProbe(IDerivedProbe):
            def Base(self):
                return "base"

            def Derived(self):
                return "derived"

        sys.pyrevit_implicit = "|".join([
            str(clr.GetClrType(first).Equals(clr.GetClrType(second))),
            str(Comparer.Default.Compare(first(), 1)),
            str(Comparer.Default.Compare(second(), 1)),
            str(Comparer.Default.Compare(built(), 1)),
            str(clr.GetClrType(first).IsInterface),
            InheritedInterfaceCaller.Call(InheritedProbe()),
        ])
        """;
    private const string TruthyBooleanProbe = """
        import clr
        import re
        import sys
        clr.AddReference("pyRevitLabs.PyRevit.Runtime.CPython.Tests")
        from System import Func
        from PyRevitLabs.PyRevit.Runtime.CPython.Tests import TruthinessTarget

        target = TruthinessTarget()
        observed = []
        for value in (re.match("a", "a"), None, 0, "x", []):
            target.Flag = value
            observed.append(str(target.Flag))
        target.Maybe = None
        observed.append(str(target.Maybe))
        target.Maybe = []
        observed.append(str(target.Maybe))
        target.Field = 1
        observed.append(str(target.Field))
        observed.append(TruthinessTarget.Pick("x"))
        observed.append(TruthinessTarget.Pick(True))
        observed.append(TruthinessTarget.OnlyBool(re.match("a", "a")))
        observed.append(TruthinessTarget.OnlyBool(None))
        observed.append(str(TruthinessTarget.Ask(Func[bool](lambda: re.match("a", "a")))))
        observed.append(str(TruthinessTarget.Ask(Func[bool](lambda: None))))
        sys.pyrevit_truthy = "|".join(observed)
        """;
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
        string? redefinition = Run(RedefinitionProbe, "__import__('sys').pyrevit_redefinition");
        string? shapes = Run(ShapesProbe, "__import__('sys').pyrevit_shapes");
        string? implicitInterfaces = Run(ImplicitInterfaceProbe, "__import__('sys').pyrevit_implicit");
        string? truthyBooleans = Run(TruthyBooleanProbe, "__import__('sys').pyrevit_truthy");
        IReadOnlyDictionary<string, string> conversions = ScriptOutputConversionProbe.Observe();

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
            DerivedTypeRedefinition = redefinition,
            DerivedTypeShapes = shapes,
            ImplicitInterfaceTypes = implicitInterfaces,
            TruthyBooleans = truthyBooleans,
            ScriptOutputConversions = conversions,
        };
    }

    private static int? ReadMarker() {
        using Py.GILState gil = Py.GIL();
        using PyObject? value = PythonEngine.Eval(MarkerRead);
        return value is null ? null : Convert.ToInt32(value);
    }

    private static string? Run(string code, string result) {
        try {
            using Py.GILState gil = Py.GIL();
            PythonEngine.Exec(code);
            using PyObject? value = PythonEngine.Eval(result);
            return value?.ToString();
        }
        catch (Exception ex) {
            return "error: " + ex.Message;
        }
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
