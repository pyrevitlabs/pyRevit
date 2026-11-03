using pyRevitLabs.Common;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Verifies which machine-config content counts as an administrator lock on the agent host.
/// </summary>
public class AgentAdminPolicyTests : IDisposable
{
    private readonly string tempRoot = Path.Combine(Path.GetTempPath(), "agentAdmin_" + Guid.NewGuid().ToString("N"));

    public AgentAdminPolicyTests() => Directory.CreateDirectory(tempRoot);

    public void Dispose()
    {
        AgentAdminPolicy.OverrideMachineConfigPath(null);
        Directory.Delete(tempRoot, recursive: true);
    }

    private string WriteConfig(string content)
    {
        string path = Path.Combine(tempRoot, "pyRevit_config.ini");
        File.WriteAllText(path, content);
        return path;
    }

    [Fact]
    public void Load_MissingFile_PinsNothing()
    {
        Assert.True(AgentAdminPolicy.Load(Path.Combine(tempRoot, "absent.ini")).IsEmpty);
    }

    [Fact]
    public void Load_AdminSection_ReturnsEveryPinnedKey()
    {
        var policy = AgentAdminPolicy.Load(WriteConfig(
            "[agent.admin]\r\nenabled = false\r\npolicy = readonly\r\nengine = cpython\r\nuser_skills = false\r\n"));

        Assert.Equal("false", policy.Enabled);
        Assert.Equal("readonly", policy.Policy);
        Assert.Equal("cpython", policy.Engine);
        Assert.Equal("false", policy.UserSkills);
    }

    [Fact]
    public void Load_PlainAgentSectionInMachineConfig_IsNotALock()
    {
        var policy = AgentAdminPolicy.Load(WriteConfig(
            "[agent]\r\nenabled = true\r\npolicy = auto\r\nengine = cpython\r\n"));

        Assert.True(policy.IsEmpty);
    }

    [Fact]
    public void Load_OnlySomeKeysPinned_LeavesTheRestNull()
    {
        var policy = AgentAdminPolicy.Load(WriteConfig("[agent.admin]\r\npolicy = ask\r\n"));

        Assert.Equal("ask", policy.Policy);
        Assert.Null(policy.Enabled);
        Assert.Null(policy.Engine);
        Assert.Null(policy.UserSkills);
    }

    [Fact]
    public void Current_PicksUpAChangeToTheFile()
    {
        string path = WriteConfig("[agent.admin]\r\nenabled = false\r\n");
        AgentAdminPolicy.OverrideMachineConfigPath(path);
        Assert.Equal("false", AgentAdminPolicy.Current.Enabled);

        File.WriteAllText(path, "[core]\r\nuserlocale = en_us\r\n");
        File.SetLastWriteTimeUtc(path, DateTime.UtcNow.AddMinutes(1));

        Assert.True(AgentAdminPolicy.Current.IsEmpty);
    }

    [Fact]
    public void SetPin_CreatesTheFileAndRoundTrips()
    {
        string path = Path.Combine(tempRoot, "pyRevit_config.ini");
        AgentAdminPolicy.OverrideMachineConfigPath(path);

        AgentAdminPolicy.SetPin(AgentAdminPolicy.EnabledKey, "false");
        AgentAdminPolicy.SetPin(AgentAdminPolicy.PolicyKey, "ask");

        Assert.Equal("false", AgentAdminPolicy.Current.Enabled);
        Assert.Equal("ask", AgentAdminPolicy.Current.Policy);
        Assert.Null(AgentAdminPolicy.Current.Engine);
    }

    [Fact]
    public void SetPin_KeepsOtherSectionsIntact()
    {
        string path = WriteConfig("[core]\r\nuserlocale = en_us\r\n\r\n[agent]\r\nenabled = true\r\n");
        AgentAdminPolicy.OverrideMachineConfigPath(path);

        AgentAdminPolicy.SetPin(AgentAdminPolicy.EngineKey, "cpython");

        string text = File.ReadAllText(path);
        Assert.Contains("userlocale", text);
        Assert.Contains("[agent]", text);
        Assert.Equal("cpython", AgentAdminPolicy.Current.Engine);
    }

    [Fact]
    public void ClearPin_RemovesOnlyThatKey()
    {
        AgentAdminPolicy.OverrideMachineConfigPath(WriteConfig("[agent.admin]\r\nenabled = false\r\npolicy = ask\r\n"));

        AgentAdminPolicy.ClearPin(AgentAdminPolicy.EnabledKey);

        Assert.Null(AgentAdminPolicy.Current.Enabled);
        Assert.Equal("ask", AgentAdminPolicy.Current.Policy);
    }

    [Fact]
    public void ClearAllPins_LeavesNothingPinned()
    {
        AgentAdminPolicy.OverrideMachineConfigPath(WriteConfig("[agent.admin]\r\nenabled = false\r\npolicy = ask\r\n"));

        AgentAdminPolicy.ClearAllPins();

        Assert.True(AgentAdminPolicy.Current.IsEmpty);
    }

    [Fact]
    public void ClearPin_WhenTheFileIsMissing_DoesNotCreateIt()
    {
        string path = Path.Combine(tempRoot, "pyRevit_config.ini");
        AgentAdminPolicy.OverrideMachineConfigPath(path);

        AgentAdminPolicy.ClearPin(AgentAdminPolicy.EnabledKey);
        AgentAdminPolicy.ClearAllPins();

        Assert.False(File.Exists(path));
    }

    [Fact]
    public void SetPin_OnAReadOnlyConfig_WritesAndRestoresTheAttribute()
    {
        string path = WriteConfig("[core]\r\nuserlocale = en_us\r\n");
        File.SetAttributes(path, FileAttributes.ReadOnly);
        AgentAdminPolicy.OverrideMachineConfigPath(path);
        try
        {
            AgentAdminPolicy.SetPin(AgentAdminPolicy.EnabledKey, "false");

            Assert.Equal("false", AgentAdminPolicy.Current.Enabled);
            Assert.True((File.GetAttributes(path) & FileAttributes.ReadOnly) != 0);
        }
        finally
        {
            File.SetAttributes(path, FileAttributes.Normal);
        }
    }

    [Fact]
    public void SetPin_UnknownKey_Throws()
    {
        AgentAdminPolicy.OverrideMachineConfigPath(Path.Combine(tempRoot, "pyRevit_config.ini"));

        Assert.Throws<ArgumentException>(() => AgentAdminPolicy.SetPin("tab_highlight", "false"));
    }

    [Fact]
    public void ResolveMachineConfigPath_IgnoresTheProgramDataOverride()
    {
        string? previous = Environment.GetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar);
        try
        {
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, tempRoot);

            Assert.False(AgentAdminPolicy.ResolveMachineConfigPath().StartsWith(tempRoot, StringComparison.OrdinalIgnoreCase));
        }
        finally
        {
            Environment.SetEnvironmentVariable(PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar, previous);
        }
    }
}
