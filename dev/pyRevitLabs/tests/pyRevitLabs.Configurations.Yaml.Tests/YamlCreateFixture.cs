using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Yaml.Tests
{
    public sealed class YamlCreateFixture : IDisposable
    {
        public const string ConfigPath = "pyRevit_config.yml";

        public YamlCreateFixture()
        {
            Configuration = YamlConfiguration.Create(ConfigPath);
        }
        
        public IConfiguration Configuration { get; }

        public void Dispose()
        {
            File.Delete(ConfigPath);
        }
    }
}