using IronPython.Runtime;

namespace PyRevitLabs.PyRevit.Runtime.EnvVars.Tests;

/// <summary>
/// Pins that CPython scripts can write pyRevit environment variables into the C#-seeded
/// <see cref="PythonDictionary"/> without an IronPython context, which is what
/// <c>from pyrevit import revit</c> does through <c>output.set_stylesheet</c> under
/// <c>pyrevit run</c>.
/// </summary>
public class CPythonEnvVarsTests {
    public CPythonEnvVarsTests() {
        CPythonEnvVarsHost.EnsureStarted();
        Assert.False(
            CPythonEnvVarsHost.IronPythonDefaultContextInitialized,
            "an IronPython context exists, so these tests no longer model the CPython-only runner");
    }

    [Fact]
    public void SetEnvVar_StoresThePlainStringKey_WithoutAnIronPythonContext() {
        PythonDictionary envData = CPythonEnvVarsHost.SeedEnvDictionary();

        CPythonEnvVarsHost.Exec("envvars.set_pyrevit_env_var('PYREVIT_STYLESHEET', 'outputstyles.css')");

        Assert.Equal("outputstyles.css", envData["PYREVIT_STYLESHEET"]);
        Assert.All(envData.Keys, key => Assert.IsType<string>(key));
        Assert.Same(envData, AppDomain.CurrentDomain.GetData(CPythonEnvVarsHost.EnvVarsDictKey));
    }

    [Fact]
    public void SetEnvVar_ReplacesAnExistingEntry() {
        PythonDictionary envData = CPythonEnvVarsHost.SeedEnvDictionary();
        int seededCount = envData.Count;

        CPythonEnvVarsHost.Exec("envvars.set_pyrevit_env_var('PYREVIT_UUID', 'replaced-uuid')");

        Assert.Equal("replaced-uuid", envData["PYREVIT_UUID"]);
        Assert.Equal(seededCount, envData.Count);
    }

    [Fact]
    public void GetEnvVar_ReadsSeededAndCPythonWrittenValues() {
        CPythonEnvVarsHost.SeedEnvDictionary();

        CPythonEnvVarsHost.Exec("envvars.set_pyrevit_env_var('MY_SCRIPT_STATUS', 'done')");

        Assert.Equal("2026", CPythonEnvVarsHost.EvalString("envvars.get_pyrevit_env_var('PYREVIT_APPVERSION')"));
        Assert.Equal("done", CPythonEnvVarsHost.EvalString("envvars.get_pyrevit_env_var('MY_SCRIPT_STATUS')"));
        Assert.Null(CPythonEnvVarsHost.EvalString("envvars.get_pyrevit_env_var('PYREVIT_MISSING')"));
    }

    /// <summary>
    /// Why <c>set_pyrevit_env_var</c> must not use item assignment under CPython: pythonnet binds
    /// it to the <c>this[params object[]]</c> indexer, whose tuple key forces the storage onto
    /// IronPython's default context. If pythonnet starts binding the single-key indexer, this
    /// fails and the CPython branch can be dropped.
    /// </summary>
    [Fact]
    public void ItemAssignment_FromCPython_FailsWithoutAnIronPythonContext() {
        PythonDictionary envData = CPythonEnvVarsHost.SeedEnvDictionary();

        Exception? failure = Record.Exception(() => CPythonEnvVarsHost.Exec(
            "from System import AppDomain\n"
            + $"AppDomain.CurrentDomain.GetData('{CPythonEnvVarsHost.EnvVarsDictKey}')['PYREVIT_STYLESHEET'] = 'x.css'"));

        Assert.IsType<NullReferenceException>(failure);
        Assert.False(envData.ContainsKey("PYREVIT_STYLESHEET"));
    }
}
