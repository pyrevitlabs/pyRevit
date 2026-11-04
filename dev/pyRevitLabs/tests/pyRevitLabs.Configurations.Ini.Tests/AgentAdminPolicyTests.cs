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
    public void Load_AnUnreadableFile_FailsClosed()
    {
        string path = WriteConfig("[agent.admin]\r\nenabled = true\r\npolicy = auto\r\n");
        using (new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            var policy = AgentAdminPolicy.Load(path);

            Assert.True(policy.ReadFailed);
            Assert.Equal("false", policy.Enabled);
            Assert.Equal("readonly", policy.Policy);
            Assert.Equal("false", policy.UserSkills);
        }
    }

    [Fact]
    public void Current_DoesNotCacheAFailedRead()
    {
        string path = WriteConfig("[agent.admin]\r\nenabled = true\r\n");
        AgentAdminPolicy.OverrideMachineConfigPath(path);

        using (new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            Assert.True(AgentAdminPolicy.Current.ReadFailed);
        }

        var recovered = AgentAdminPolicy.Current;
        Assert.False(recovered.ReadFailed);
        Assert.Equal("true", recovered.Enabled);
    }

    [Fact]
    public void Load_ABlankPin_IsPresentRatherThanAbsent()
    {
        var policy = AgentAdminPolicy.Load(WriteConfig("[agent.admin]\r\nenabled =\r\npolicy = \"\"\r\n"));

        Assert.Equal(string.Empty, policy.Enabled);
        Assert.Equal(string.Empty, policy.Policy);
        Assert.Null(policy.Engine);
        Assert.False(policy.IsEmpty);
    }

    [Fact]
    public void Current_BlankPins_ReadAsTheStrictestValues()
    {
        AgentAdminPolicy.OverrideMachineConfigPath(WriteConfig(
            "[agent.admin]\r\nenabled =\r\npolicy =\r\nengine =\r\nuser_skills =\r\n"));

        var policy = AgentAdminPolicy.Current;

        Assert.Equal("false", policy.Enabled);
        Assert.Equal("readonly", policy.Policy);
        Assert.Equal("ironpython", policy.Engine);
        Assert.Equal("false", policy.UserSkills);
    }

    [Fact]
    public void Current_AnExtraConfigFileDoesNotHideTheRealOne()
    {
        File.WriteAllText(Path.Combine(tempRoot, "acme-config.ini"), "[agent.admin]\r\nenabled = false\r\n");
        File.WriteAllText(Path.Combine(tempRoot, "pyRevit_config.ini"), "[core]\r\nuserlocale = en_us\r\n");
        AgentAdminPolicy.OverrideMachineConfigDirectory(tempRoot);

        Assert.Equal("false", AgentAdminPolicy.Current.Enabled);
    }

    [Fact]
    public void Current_TheStrictestPinWinsAcrossFiles()
    {
        File.WriteAllText(
            Path.Combine(tempRoot, "a-config.ini"),
            "[agent.admin]\r\nenabled = false\r\npolicy = auto\r\nengine = cpython\r\nuser_skills = true\r\n");
        File.WriteAllText(
            Path.Combine(tempRoot, "b-config.ini"),
            "[agent.admin]\r\nenabled = true\r\npolicy = ask\r\nengine = ironpython\r\nuser_skills = true\r\n");
        AgentAdminPolicy.OverrideMachineConfigDirectory(tempRoot);

        var policy = AgentAdminPolicy.Current;

        Assert.Equal("false", policy.Enabled);
        Assert.Equal("ask", policy.Policy);
        Assert.Equal("ironpython", policy.Engine);
        Assert.Equal("true", policy.UserSkills);
    }

    [Fact]
    public void Current_AnUnparseableExtraFile_FailsClosed()
    {
        File.WriteAllText(Path.Combine(tempRoot, "pyRevit_config.ini"), "[agent.admin]\r\nenabled = true\r\n");
        File.WriteAllText(Path.Combine(tempRoot, "junk-config.ini"), "this line is not ini\r\n");
        AgentAdminPolicy.OverrideMachineConfigDirectory(tempRoot);

        var policy = AgentAdminPolicy.Current;

        Assert.True(policy.ReadFailed);
        Assert.Equal("false", policy.Enabled);
    }

    [Fact]
    public void SetPin_RemovesTheSamePinFromOtherFiles()
    {
        File.WriteAllText(Path.Combine(tempRoot, "pyRevit_config.ini"), "[core]\r\nuserlocale = en_us\r\n");
        string other = Path.Combine(tempRoot, "acme-config.ini");
        File.WriteAllText(other, "[agent.admin]\r\nenabled = false\r\npolicy = ask\r\n");
        AgentAdminPolicy.OverrideMachineConfigDirectory(tempRoot);

        AgentAdminPolicy.SetPin(AgentAdminPolicy.EnabledKey, "true");

        var policy = AgentAdminPolicy.Current;
        Assert.Equal("true", policy.Enabled);
        Assert.Equal("ask", policy.Policy);
        Assert.DoesNotContain("enabled", File.ReadAllText(other));
    }

    [Fact]
    public void ClearAllPins_ClearsEveryFile()
    {
        File.WriteAllText(Path.Combine(tempRoot, "pyRevit_config.ini"), "[agent.admin]\r\nenabled = false\r\n");
        File.WriteAllText(Path.Combine(tempRoot, "acme-config.ini"), "[agent.admin]\r\npolicy = ask\r\n");
        AgentAdminPolicy.OverrideMachineConfigDirectory(tempRoot);

        AgentAdminPolicy.ClearAllPins();

        Assert.True(AgentAdminPolicy.Current.IsEmpty);
    }

    [Fact]
    public void SetPin_OnAnUnparseableConfig_AbortsAndLeavesTheFileAlone()
    {
        const string content = "[core]\r\nuserlocale = en_us\r\nthis line is not ini\r\n";
        string path = WriteConfig(content);
        AgentAdminPolicy.OverrideMachineConfigPath(path);

        Assert.Throws<InvalidDataException>(() => AgentAdminPolicy.SetPin(AgentAdminPolicy.EnabledKey, "false"));

        Assert.Equal(content, File.ReadAllText(path));
        Assert.Single(Directory.GetFiles(tempRoot));
    }

    [Fact]
    public void ClearPin_OnAnUnparseableConfig_AbortsAndLeavesTheFileAlone()
    {
        const string content = "[agent.admin]\r\nenabled = false\r\nthis line is not ini\r\n";
        string path = WriteConfig(content);
        AgentAdminPolicy.OverrideMachineConfigPath(path);

        Assert.Throws<InvalidDataException>(() => AgentAdminPolicy.ClearPin(AgentAdminPolicy.EnabledKey));
        Assert.Throws<InvalidDataException>(() => AgentAdminPolicy.ClearAllPins());

        Assert.Equal(content, File.ReadAllText(path));
        Assert.Single(Directory.GetFiles(tempRoot));
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
