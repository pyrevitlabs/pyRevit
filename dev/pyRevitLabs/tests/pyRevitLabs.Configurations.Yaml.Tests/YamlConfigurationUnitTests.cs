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
    public void CreateYamlConfiguration_ShouldCreate()
    {
        Assert.NotNull(YamlConfiguration.Create(_configPath));
    }

    [Fact]
    public void CreateYamlConfiguration_ShouldThrowException()
    {
        Assert.Throws<ArgumentNullException>(() => YamlConfiguration.Create(default!));
    }

    [Fact]
    public void CreateYamlConfigurationByBuilder_ShouldThrowException()
    {
        Assert.Throws<ArgumentException>(() =>
        {
            new ConfigurationBuilder(false)
                .AddYamlConfiguration(default!, default!)
                .Build();
        });
    }

    [Fact]
    public void CreateYamlConfigurationByNullBuilder_ShouldThrowException()
    {
        Assert.Throws<ArgumentNullException>(() =>
        {
            YamlConfigurationExtensions
                .AddYamlConfiguration(default!, default!, default!)
                .Build();
        });
    }
}