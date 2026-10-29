namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// Guards the two pyRevit-side halves of the interpreter lifecycle contract. The runtime assembly
/// cannot be loaded outside a Revit host, so these read the engine source instead of calling it.
/// </summary>
public class CPythonEngineSourceTests {
    /// <summary>
    /// Releasing the engine at Reload or Refresh Engine must not tear down the process-wide
    /// interpreter. Doing so either writes a <c>BinaryFormatter</c> state blob that Revit's
    /// duplicated assembly load context cannot read back, or throws partway through and wedges
    /// pythonnet; either way every later CPython command in the Revit session fails. See
    /// pyRevit#3510 and <see cref="CPythonInterpreterLifecycleTests.Shutdown_Failing_LeavesTheEngineFlagSetSoLaterInitializesNoOp"/>.
    /// </summary>
    [Fact]
    public void Shutdown_LeavesTheInterpreterRunning() {
        string body = CSharpSource.MemberBody(
            CSharpSource.CPythonEngine, "public override void Shutdown()");

        Assert.DoesNotContain("PythonEngine.Shutdown(", body, StringComparison.Ordinal);
    }

    /// <summary>
    /// <c>Runtime.PythonDLL</c> and <c>PythonEngine.ProgramName</c> only take effect before the
    /// interpreter comes up, and pythonnet throws on them afterwards, so they have to stay inside
    /// the bring-up guard. Moving them out would fail the first CPython command after every Reload
    /// even with the interpreter correctly left running.
    /// </summary>
    [Fact]
    public void InterpreterBringUp_StaysBehindTheNotInitializedGuard() {
        string body = CSharpSource.MemberBody(
            CSharpSource.CPythonEngine, "public override void Start(ref ScriptRuntime runtime)");

        const string guard = "if (!PythonEngine.IsInitialized)";
        Assert.True(
            CSharpSource.IsInBlockOf(body, guard, "CpyRuntime.PythonDLL ="),
            "Runtime.PythonDLL must be assigned inside the !PythonEngine.IsInitialized guard");
        Assert.True(
            CSharpSource.IsInBlockOf(body, guard, "PythonEngine.ProgramName ="),
            "PythonEngine.ProgramName must be assigned inside the !PythonEngine.IsInitialized guard");
    }

    /// <summary>
    /// The forms binding conversions, which decide how Python lists and objects reach CLR
    /// parameters, are installed when the engine starts rather than on the first
    /// <c>import pyrevit.forms</c>, so a script converts the same way in a fresh session as after a
    /// forms tool ran. The call sits outside the bring-up guard so it also runs when pyRevit
    /// attaches to an interpreter something else brought up.
    /// </summary>
    [Fact]
    public void Start_RegistersTheFormsBindingConversions() {
        string body = CSharpSource.MemberBody(
            CSharpSource.CPythonEngine, "public override void Start(ref ScriptRuntime runtime)");

        Assert.Contains("RegisterPythonConversions();", body, StringComparison.Ordinal);
        Assert.False(
            CSharpSource.IsInBlockOf(body, "if (!PythonEngine.IsInitialized)", "RegisterPythonConversions();"),
            "the conversions must be registered whoever brought the interpreter up");
        Assert.Contains("GetMethod(\"RegisterConversions\"", CSharpSource.CPythonEngine, StringComparison.Ordinal);
    }
}
