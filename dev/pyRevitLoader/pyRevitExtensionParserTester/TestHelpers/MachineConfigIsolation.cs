using System;
using System.IO;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitLabs.Common;
using pyRevitLabs.Configurations;

/// <summary>
/// Points the per-user and all-users pyRevit directories at a temp folder for the
/// whole test run, so the parser never reads the developer's or CI agent's real
/// <c>pyRevit_config.ini</c>. Without this, a machine setting such as
/// <c>read_script_metadata = false</c> silently changes what the parser returns.
/// Tests that need specific settings still install their own factory through
/// <see cref="PyRevitConfigStore.SetFactory"/>; <see cref="PyRevitConfigStore.Reset"/>
/// then falls back to this baseline config instead of the machine one.
/// </summary>
/// <remarks>
/// The baseline enables pyRevitDevTools, which ships with <c>default_enabled: False</c>
/// but is the fixture extension most tests parse from the repo.
/// </remarks>
[SetUpFixture]
public class MachineConfigIsolation
{
    private const string BaselineConfig =
        "[core]\n" +
        "\n" +
        "[pyRevitDevTools.extension]\n" +
        "disabled = false\n";

    private string _isolatedRoot;
    private string _previousAppDataOverride;
    private string _previousProgramDataOverride;

    [OneTimeSetUp]
    public void IsolateFromMachineConfig()
    {
        _isolatedRoot = Path.Combine(Path.GetTempPath(), $"pyRevitTestConfig_{Guid.NewGuid():N}");
        var appData = Directory.CreateDirectory(Path.Combine(_isolatedRoot, "AppData")).FullName;
        var programData = Directory.CreateDirectory(Path.Combine(_isolatedRoot, "ProgramData")).FullName;
        File.WriteAllText(Path.Combine(appData, PyRevitLabsConsts.DefaultConfigsFileName), BaselineConfig);

        _previousAppDataOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar);
        _previousProgramDataOverride = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, appData);
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, programData);

        ResetConfigState();
    }

    [OneTimeTearDown]
    public void RestoreMachineConfig()
    {
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitPathOverrideEnvVar, _previousAppDataOverride);
        Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, _previousProgramDataOverride);
        ResetConfigState();

        try
        {
            if (Directory.Exists(_isolatedRoot))
                Directory.Delete(_isolatedRoot, recursive: true);
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }

    private static void ResetConfigState()
    {
        PyRevitConfigStore.Reset();
        PyRevitConfig.ClearCache();
        ExtensionParser.ClearAllCaches();
    }
}
