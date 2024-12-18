using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Json.Extensions;
using pyRevitLabs.Configurations.Tests;

namespace pyRevitLabs.Configurations.Json.Tests;

public class JsonConfigurationUnitTests : ConfigurationTests, IClassFixture<JsonCreateFixture>
{
    private readonly string _configPath;

    public JsonConfigurationUnitTests(JsonCreateFixture createFixture)
        : base(createFixture.Configuration)
    {
        _configPath = JsonCreateFixture.ConfigPath;
    }

    [Fact]
    public void CreateIniConfiguration_ShouldCreate()
    {
        Assert.NotNull(JsonConfiguration.Create(_configPath));
    }

    [Fact]
    public void CreateIniConfiguration_ShouldThrowsException()
    {
        Assert.Throws<ArgumentNullException>(() => JsonConfiguration.Create(default!));
    }

    [Fact]
    public void CreateIniConfigurationByBuilder_ShouldThrowsException()
    {
        Assert.Throws<ArgumentException>(() =>
        {
            new ConfigurationBuilder()
                .AddJsonConfiguration(default!, default!)
                .Build();
        });
    }

    [Fact]
    public void CreateIniConfigurationByNullBuilder_ShouldThrowsException()
    {
        Assert.Throws<ArgumentNullException>(() =>
        {
            JsonConfigurationExtensions
                .AddJsonConfiguration(default!, default!, default!)
                .Build();
        });
    }
}