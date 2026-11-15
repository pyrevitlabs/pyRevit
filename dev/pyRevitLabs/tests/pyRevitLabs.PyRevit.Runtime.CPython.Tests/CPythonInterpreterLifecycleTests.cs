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
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
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

    /// <summary>
    /// Regression for pyRevit#4074. CPython moves the process-wide CRT <c>LC_CTYPE</c> off
    /// <c>C</c> while initializing, and Revit then reports a healthy workshared central model as
    /// corrupt on Synchronize with Central. Bringing the interpreter up under a
    /// <see cref="CrtLocale"/> scope, as <c>CPythonEngine.Start</c> does, must leave the locale as
    /// it was.
    /// </summary>
    [Fact]
    public void Initializing_UnderACrtLocaleScope_LeavesLcCtypeUntouched() {
        InterpreterLifecycleRecord record = InterpreterLifecycleProbe.Record;

        Assert.NotNull(record.LcCtypeBeforeInitialize);
        Assert.Equal(record.LcCtypeBeforeInitialize, record.LcCtypeAfterInitialize);
    }

    /// <summary>
    /// The scope must undo a real CPython locale change, not just a no-op: the interpreter is
    /// told to adopt the user locale, which differs from <c>C</c> on any Windows machine that has
    /// a regional format, and disposing the scope has to put the captured value back.
    /// </summary>
    [Fact]
    public void CrtLocaleScope_RestoresLcCtypeThatCPythonChanged() {
        InterpreterLifecycleRecord record = InterpreterLifecycleProbe.Record;

        Assert.NotEqual(record.LcCtypeBeforeUserLocaleAdoption, record.LcCtypeWhileAdoptingUserLocale);
        Assert.Equal(record.LcCtypeBeforeUserLocaleAdoption, record.LcCtypeAfterScope);
    }
}
