namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// Pins the pythonnet behaviour <c>CPythonEngine</c> depends on, so a pythonnet upgrade that breaks
/// the interpreter-across-Reload contract fails here instead of in a Revit session.
/// </summary>
/// <remarks>
/// The engine only reaches the interpreter through the public pythonnet API, so these are the
/// strongest assertions available without a live Revit session. The pyRevit-side halves of the
/// contract are asserted in <see cref="CPythonEngineSourceTests"/>.
/// </remarks>
public class CPythonInterpreterLifecycleTests {
    /// <summary>
    /// A Reload drops the engine from the session cache and the next CPython command re-attaches:
    /// <c>CPythonEngine.Start</c> finds <c>PythonEngine.IsInitialized</c> already true, skips the
    /// guarded bring-up, and runs the script on the live interpreter. This walks that re-attach
    /// loop and requires the interpreter to keep its state, so a shutdown creeping back into the
    /// reload path would surface as lost state rather than as a silently broken engine.
    /// </summary>
    [Fact]
    public void ReattachingAcrossReloads_KeepsTheInterpreterUpAndItsState() {
        InterpreterLifecycleRecord record = InterpreterLifecycleProbe.Record;

        Assert.True(record.BroughtUp);
        Assert.Empty(record.ReattachFailures);
        Assert.Equal(InterpreterLifecycleProbe.ReattachCount + 1, record.MarkerAfterReattaches);
    }

    /// <summary>
    /// pythonnet caches the CLR type generated for a Python class that derives from a CLR type,
    /// so repeated commands reuse it instead of colliding. A redefinition with the same shape must
    /// reuse the cached type, while one that adds an explicit <c>clr.clrmethod</c> must get a fresh
    /// type that exposes it rather than the stale cached one.
    /// </summary>
    [Fact]
    public void RedefiningADerivedClass_ReusesItsTypeUnlessExplicitMembersChange() {
        string? record = InterpreterLifecycleProbe.Record.DerivedTypeRedefinition;

        Assert.Equal("True|False|True|False", record);
    }

    /// <summary>
    /// The generated CLR type keeps the Python class's visible name, so it stays importable from
    /// its <c>__namespace__</c> even when it derives from interfaces or generic types. Properties
    /// that differ only in having a setter, and classes placed in different <c>__assembly__</c>
    /// values, are different shapes and must not share a cached type.
    /// </summary>
    [Fact]
    public void DerivedClassTypes_KeepTheirNameAndSeparateEveryShape() {
        string? record = InterpreterLifecycleProbe.Record.DerivedTypeShapes;

        Assert.Equal(
            "pyrevit.tests.naming.NamedProbe|True|pyrevit.tests.naming.GenericProbe|False|True|pyrevit.tests.first|pyrevit.tests.second",
            record);
    }

    /// <summary>
    /// A Python class that only implements CLR interfaces needs no <c>__namespace__</c>, as under
    /// IronPython: pythonnet generates its CLR type, so CLR callers reach its Python methods, and
    /// redefining it with the same shape, as a re-run command does, reuses that type.
    /// </summary>
    [Fact]
    public void ImplementingAnInterface_WithoutANamespace_GeneratesAReusableType() {
        string? record = InterpreterLifecycleProbe.Record.ImplicitInterfaceTypes;

        Assert.Equal("True|7|7|3|False", record);
    }

    /// <summary>
    /// Like IronPython, a <see cref="bool"/> or <see cref="Nullable{Boolean}"/> property, field,
    /// parameter or delegate return accepts any Python value by truthiness, while <c>None</c> stays
    /// null for <see cref="Nullable{Boolean}"/>. A <see cref="bool"/> overload never wins over one
    /// that takes the value itself.
    /// </summary>
    [Fact]
    public void BooleanTargets_AcceptPythonTruthiness_WithoutStealingOverloads() {
        string? record = InterpreterLifecycleProbe.Record.TruthyBooleans;

        Assert.Equal("True|False|False|True|False|None|False|True|object|bool|True|False|True|False", record);
    }

    /// <summary>
    /// <c>CPythonEngine.Start</c> must only assign <c>Runtime.PythonDLL</c> while the runtime is
    /// down, because pythonnet rejects the assignment afterwards. Hoisting those initialize-only
    /// settings back out of the guard would make the first CPython command after a Reload fail with
    /// an <see cref="InvalidOperationException"/> instead of a real error.
    /// </summary>
    [Fact]
    public void AssigningPythonDll_OnceTheInterpreterIsUp_IsRejected() {
        Exception? failure = InterpreterLifecycleProbe.Record.PythonDllReassignment;

        Assert.NotNull(failure);
        Assert.IsType<InvalidOperationException>(failure);
    }

    /// <summary>
    /// Why the engine must never call <c>PythonEngine.Shutdown</c> at Reload time. Shutdown is a
    /// soft shutdown that stashes the CLR metatype state as a <c>BinaryFormatter</c> blob in the
    /// still-running interpreter, and on this target framework the stash itself throws because
    /// <c>BinaryFormatter</c> is gone. The teardown has already advanced past its own bookkeeping
    /// by then, so the engine keeps reporting itself initialized and every later
    /// <c>Initialize</c> silently no-ops: the permanent wedge reported in pyRevit#3510. On a
    /// framework where the stash does serialize, the same call instead leaves a blob that Revit's
    /// duplicated assembly load context cannot deserialize, which fails the same way.
    /// </summary>
    [Fact]
    public void Shutdown_Failing_LeavesTheEngineFlagSetSoLaterInitializesNoOp() {
        InterpreterLifecycleRecord record = InterpreterLifecycleProbe.Record;

        Assert.NotNull(record.Shutdown);
        Assert.Contains("BinaryFormatter", record.Shutdown.Message, StringComparison.Ordinal);
        Assert.True(
            record.IsInitializedAfterShutdown,
            "expected the engine to still report as initialized after Shutdown threw");
    }
}
