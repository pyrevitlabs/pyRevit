using Microsoft.VisualStudio.TestPlatform.ObjectModel.Client;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Tests
{
    public sealed class ConfigurationServiceFixture : IDisposable
    {
        public ConfigurationServiceFixture()
        {
            Configuration = new ConfigurationService(false, new List<ConfigurationName>(),
                new Dictionary<string, IConfiguration>()
                    {{"default", new TestRunConfiguration()}});
        }

        public ConfigurationService Configuration { get; }

        public void Dispose() { }

        private class TestRunConfiguration : IConfiguration
        {
            public string ConfigurationPath { get; }

            public bool HasSection(string sectionName)
            {
                throw new NotImplementedException();
            }

            public bool HasSectionKey(string sectionName, string keyName)
            {
                throw new NotImplementedException();
            }

            public T GetValue<T>(string sectionName, string keyName)
            {
                throw new NotImplementedException();
            }

            public T? GetValueOrDefault<T>(string sectionName, string keyName, T? defaultValue = default)
            {
                throw new NotImplementedException();
            }

            public object GetValue(Type typeObject, string sectionName, string keyName)
            {
                throw new NotImplementedException();
            }

            public object? GetValueOrDefault(Type typeObject, string sectionName, string keyName, object? defaultValue = default)
            {
                throw new NotImplementedException();
            }

            public bool RemoveValue(string sectionName, string keyName)
            {
                throw new NotImplementedException();
            }

            public void SetValue<T>(string sectionName, string keyName, T? value)
            {
                throw new NotImplementedException();
            }

            public void SaveConfiguration()
            {
                throw new NotImplementedException();
            }

            public void SaveConfiguration(string configurationPath)
            {
                throw new NotImplementedException();
            }
        }
    }
}