using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Ini.Tests
{
    public sealed class IniCreateFixture : IDisposable
    {
        public const string ConfigPath = "pyRevit_config.ini";

        public IniCreateFixture()
        {
            Configuration = IniConfiguration.Create(ConfigPath);
        }
        
        public IConfiguration Configuration { get; }

        public void Dispose()
        {
            File.Delete(ConfigPath);
        }
    }
}