using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Tests;
using pyRevitLabs.Configurations.Yaml.Extensions;

namespace pyRevitLabs.Configurations.Yaml.Tests;

public class YamlConfigurationUnitTests : ConfigurationTests, IClassFixture<YamlCreateFixture>
{
    private readonly string _configPath;

    public YamlConfigurationUnitTests(YamlCreateFixture createFixture) 
        : base(createFixture.Configuration)
    {
        _configPath = YamlCreateFixture.ConfigPath;
    }

    [Fact]
    public void CreateIniConfiguration_ShouldCreate()
    {
        Assert.NotNull(YamlConfiguration.Create(_configPath));
    }

    [Fact]
    public void CreateIniConfiguration_ShouldThrowsException()
    {
        Assert.Throws<ArgumentNullException>(() => YamlConfiguration.Create(default!));
    }

    [Fact]
    public void CreateIniConfigurationByBuilder_ShouldThrowsException()
    {
        Assert.Throws<ArgumentException>(() =>
        {
            new ConfigurationBuilder()
                .AddYamlConfiguration(default!, default!)
                .Build();
        });
    }

    [Fact]
    public void CreateIniConfigurationByNullBuilder_ShouldThrowsException()
    {
        Assert.Throws<ArgumentNullException>(() =>
        {
            YamlConfigurationExtensions
                .AddYamlConfiguration(default!, default!, default!)
                .Build();
        });
    }
}