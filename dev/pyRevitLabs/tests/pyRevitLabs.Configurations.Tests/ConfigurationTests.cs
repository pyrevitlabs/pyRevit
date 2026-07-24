using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Tests;

public abstract class ConfigurationTests
{
    protected readonly IConfiguration _configuration;

    public ConfigurationTests(IConfiguration configuration)
    {
        _configuration = configuration;
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

        bool result = _configuration.RemoveOption("remove", "default");

        Assert.True(result);
    }

    [Fact]
    public void RemoveNotExitsValue_ShouldReturnFalse()
    {
        bool result = _configuration.RemoveOption("remove", "not-exits");

        Assert.False(result);
    }
}
