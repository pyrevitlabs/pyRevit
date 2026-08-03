namespace pyRevitLabs.Configurations.Ini.Tests;

public class IniConfigurationUnitTests
{
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
}
