using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Tests
{
    public sealed class ConfigurationServiceUnitTests : IClassFixture<ConfigurationServiceFixture>
    {
        private readonly ConfigurationServiceFixture _configurationServiceFixture;

        public ConfigurationServiceUnitTests(ConfigurationServiceFixture configurationServiceFixture)
        {
            _configurationServiceFixture = configurationServiceFixture;
        }
    }
}