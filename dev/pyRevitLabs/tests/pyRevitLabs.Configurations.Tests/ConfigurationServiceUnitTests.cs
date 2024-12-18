using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Tests
{
    public sealed class ConfigurationServiceUnitTests : ConfigurationTests, IClassFixture<ConfigurationServiceFixture>
    {
        public ConfigurationServiceUnitTests(ConfigurationServiceFixture configurationServiceFixture)
            : base(configurationServiceFixture.Configuration)
        {
        }
    }
}