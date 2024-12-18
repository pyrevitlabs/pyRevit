using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Json.Tests
{
    public sealed class JsonCreateFixture : IDisposable
    {
        public const string ConfigPath = "pyRevit_config.json";

        public JsonCreateFixture()
        {
            Configuration = JsonConfiguration.Create(ConfigPath);
        }
        
        public IConfiguration Configuration { get; }

        public void Dispose()
        {
            File.Delete(ConfigPath);
        }
    }
}