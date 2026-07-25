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
    public void CreateIniConfiguration_ShouldThrowException()
    {
        Assert.Throws<ArgumentNullException>(() => IniConfiguration.Create(default!));
    }

    /// <summary>
    /// A fresh install resolves its per-user config before %APPDATA%\pyRevit
    /// exists, so the first save has to create the directory rather than fail.
    /// </summary>
    [Fact]
    public void SaveConfiguration_CreatesMissingDirectory()
    {
        string dir = Path.Combine(Path.GetTempPath(), "cfgnew_" + Guid.NewGuid().ToString("N"));
        string path = Path.Combine(dir, "pyRevit_config.ini");
        try
        {
            var configuration = IniConfiguration.Create(path);
            configuration.SetValue("core", "checkupdates", true);
            configuration.SaveConfiguration();

            Assert.True(File.Exists(path));
        }
        finally
        {
            if (Directory.Exists(dir))
                Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void CreateIniConfigurationByBuilder_ShouldThrowException()
    {
        Assert.Throws<ArgumentException>(() =>
        {
            new ConfigurationBuilder(false)
                .AddIniConfiguration(default!, default!)
                .Build();
        });
    }

    [Fact]
    public void CreateIniConfigurationByNullBuilder_ShouldThrowException()
    {
        Assert.Throws<ArgumentNullException>(() =>
        {
            IniConfigurationExtensions
                .AddIniConfiguration(default!, default!, default!)
                .Build();
        });
    }
}
