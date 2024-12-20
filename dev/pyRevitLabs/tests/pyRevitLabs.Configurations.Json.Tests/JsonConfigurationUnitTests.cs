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
    public void CreateJsonConfiguration_ShouldThrowException()
    {
        Assert.Throws<ArgumentNullException>(() => JsonConfiguration.Create(default!));
    }

    [Fact]
    public void CreateJsonConfigurationByBuilder_ShouldThrowException()
    {
        Assert.Throws<ArgumentException>(() =>
        {
            new ConfigurationBuilder()
                .AddJsonConfiguration(default!, default!)
                .Build();
        });
    }

    [Fact]
    public void CreateJsonConfigurationByNullBuilder_ShouldThrowException()
    {
        Assert.Throws<ArgumentNullException>(() =>
        {
            JsonConfigurationExtensions
                .AddJsonConfiguration(default!, default!, default!)
                .Build();
        });
    }
}