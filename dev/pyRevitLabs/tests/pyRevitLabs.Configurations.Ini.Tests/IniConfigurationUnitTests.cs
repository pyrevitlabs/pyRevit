using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.Configurations.Tests;

namespace pyRevitLabs.Configurations.Ini.Tests;

public class IniConfigurationUnitTests : ConfigurationTests, IClassFixture<IniCreateFixture>
{
    private readonly string _configPath;

    public IniConfigurationUnitTests(IniCreateFixture iniCreateFixture)
        : base(iniCreateFixture.Configuration)
    {
        _configPath = IniCreateFixture.ConfigPath;
    }

    [Fact]
    public void CreateIniConfiguration_ShouldCreate()
    {
        Assert.NotNull(IniConfiguration.Create(_configPath));
    }

    [Fact]
    public void CreateIniConfiguration_ShouldThrowsException()
    {
        Assert.Throws<ArgumentNullException>(() => IniConfiguration.Create(default!));
    }

    [Fact]
    public void CreateIniConfigurationByBuilder_ShouldThrowsException()
    {
        Assert.Throws<ArgumentException>(() =>
        {
            new ConfigurationBuilder()
                .AddIniConfiguration(default!, default!)
                .Build();
        });
    }

    [Fact]
    public void CreateIniConfigurationByNullBuilder_ShouldThrowsException()
    {
        Assert.Throws<ArgumentNullException>(() =>
        {
            IniConfigurationExtensions
                .AddIniConfiguration(default!, default!, default!)
                .Build();
        });
    }
}