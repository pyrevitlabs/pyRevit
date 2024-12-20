using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Tests;

public abstract class ConfigurationTests
{
    protected readonly IConfiguration _configuration;

    public ConfigurationTests(IConfiguration configuration)
    {
        _configuration = configuration;
        StartUp();
    }
    
    private void StartUp()
    {
        // core
        _configuration.SetValue("core", "userextensions", new List<string>());
        _configuration.SetValue("core", "user_locale", "ru");
        _configuration.SetValue("core", "rocketmode", true);
        _configuration.SetValue("core", "autoupdate", true);
        _configuration.SetValue("core", "checkupdates", true);
        _configuration.SetValue("core", "usercanextend", true);
        _configuration.SetValue("core", "usercanconfig", true);

        // environment
        _configuration.SetValue("environment", "clones",
            new Dictionary<string, string>() {{"master", "C:\\Users\\user\\AppData\\Roaming\\pyRevit-Master"}});

        // pyRevitBundlesCreatorExtension.extension
        _configuration.SetValue("pyRevitBundlesCreatorExtension.extension", "disabled", true);
        _configuration.SetValue("pyRevitBundlesCreatorExtension.extension", "private_repo", true);
        _configuration.SetValue("pyRevitBundlesCreatorExtension.extension", "username", "");
        _configuration.SetValue("pyRevitBundlesCreatorExtension.extension", "password", "");

        // telemetry
        _configuration.SetValue("telemetry", "active", true);
        _configuration.SetValue("telemetry", "utc_timestamps", true);
        _configuration.SetValue("telemetry", "active_app", true);
        _configuration.SetValue("telemetry", "apptelemetry_event_flags", "0x4000400004003");
        _configuration.SetValue("telemetry", "apptelemetry_event_flags", "0x4000400004003");
        _configuration.SetValue("telemetry", "telemetry_server_url", "http://pyrevitlabs.io/api/v2/scripts");
        _configuration.SetValue("telemetry", "apptelemetry_server_url", "http://pyrevitlabs/api/v2/events");
    }

    [Fact]
    public void NewCreateValue_ShouldReturnSameValue()
    {
        _configuration.SetValue("new", "create", "value");

        string value = _configuration.GetValue<string>("new", "create");

        Assert.Equal("value", value);
    }

    [Fact]
    public void GetValueOrDefault_ShouldReturnSameValue()
    {
        _configuration.SetValue("create", "default", "value");

        string? value = _configuration.GetValueOrDefault<string>("create", "default");

        Assert.Equal("value", value);
    }

    [Fact]
    public void GetValueOrDefault_ShouldReturnDefaultValue()
    {
        string? value = _configuration.GetValueOrDefault<string>("not_exits", "key", "defaultValue");

        Assert.Equal("defaultValue", value);
    }

    [Fact]
    public void RemoveExitsValue_ShouldReturnTrue()
    {
        _configuration.SetValue("remove", "default", "value");

        bool result = _configuration.RemoveValue("remove", "default");

        Assert.True(result);
    }

    [Fact]
    public void RemoveNotExitsValue_ShouldReturnFalse()
    {
        bool result = _configuration.RemoveValue("remove", "not-exits");

        Assert.False(result);
    }
}