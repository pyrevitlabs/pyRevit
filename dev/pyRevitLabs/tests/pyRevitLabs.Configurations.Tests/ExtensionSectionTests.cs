using System;
using System.Collections.Generic;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Tests;

/// <summary>
/// Covers <see cref="IConfigurationService.GetExtensionSection"/>: resolution of
/// the dynamic per-extension section, ".extension" precedence over ".lib",
/// declared defaults for absent keys, and the null result when no section exists.
/// </summary>
public class ExtensionSectionTests
{
    private static IConfigurationService BuildService(Action<InMemoryConfiguration> seed)
    {
        var configuration = new InMemoryConfiguration();
        seed(configuration);
        return new ConfigurationBuilder(false)
            .AddConfigurationSource(configuration)
            .Build();
    }

    [Fact]
    public void GetExtensionSection_ReadsExtensionSection()
    {
        var service = BuildService(config =>
        {
            config.SetValue("pyRevitCore.extension", "disabled", true);
            config.SetValue("pyRevitCore.extension", "private_repo", true);
            config.SetValue("pyRevitCore.extension", "username", "admin");
            config.SetValue("pyRevitCore.extension", "password", "secret");
        });

        ExtensionSection? section = service.GetExtensionSection("pyRevitCore");

        Assert.NotNull(section);
        Assert.True(section!.Disabled);
        Assert.True(section.PrivateRepo);
        Assert.Equal("admin", section.Username);
        Assert.Equal("secret", section.Password);
    }

    [Fact]
    public void GetExtensionSection_FallsBackToLibrarySection()
    {
        var service = BuildService(config =>
            config.SetValue("MyLibrary.lib", "disabled", true));

        ExtensionSection? section = service.GetExtensionSection("MyLibrary");

        Assert.NotNull(section);
        Assert.True(section!.Disabled);
    }

    [Fact]
    public void GetExtensionSection_PrefersExtensionOverLibrary()
    {
        var service = BuildService(config =>
        {
            config.SetValue("Shared.extension", "disabled", false);
            config.SetValue("Shared.lib", "disabled", true);
        });

        ExtensionSection? section = service.GetExtensionSection("Shared");

        Assert.NotNull(section);
        Assert.False(section!.Disabled);
    }

    [Fact]
    public void GetExtensionSection_AbsentSection_ReturnsNull()
    {
        var service = BuildService(_ => { });

        Assert.Null(service.GetExtensionSection("Missing"));
    }

    [Fact]
    public void GetExtensionSection_AppliesDeclaredDefaults_ForAbsentKeys()
    {
        // Section present but the flag keys are not stored: the declared defaults
        // apply on read, matching the loader adapter's ReadBool(..., false).
        var service = BuildService(config =>
            config.SetValue("Sparse.extension", "username", "someone"));

        ExtensionSection? section = service.GetExtensionSection("Sparse");

        Assert.NotNull(section);
        Assert.False(section!.Disabled);
        Assert.False(section.PrivateRepo);
        Assert.Equal("someone", section.Username);
        Assert.Null(section.Password);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void GetExtensionSection_NullOrWhitespaceName_Throws(string? name)
    {
        var service = BuildService(_ => { });

        Assert.Throws<ArgumentException>(() => service.GetExtensionSection(name!));
    }

    /// <summary>
    /// Minimal in-memory <see cref="IConfiguration"/> holding typed values, so the
    /// section-materialization path can be exercised without the INI backend (and
    /// its JSON round-trip, which is covered by the Ini tests).
    /// </summary>
    private sealed class InMemoryConfiguration : ConfigurationBase
    {
        private readonly Dictionary<string, Dictionary<string, object?>> _data =
            new(StringComparer.OrdinalIgnoreCase);

        public InMemoryConfiguration() : base("memory", readOnly: false) { }

        private Dictionary<string, object?> Section(string sectionName)
        {
            if (!_data.TryGetValue(sectionName, out var section))
                _data[sectionName] = section = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
            return section;
        }

        protected override void SaveConfigurationImpl() { }
        protected override void SaveConfigurationImpl(string configurationPath) { }

        protected override bool HasSectionImpl(string sectionName) => _data.ContainsKey(sectionName);

        protected override bool HasSectionKeyImpl(string sectionName, string keyName) =>
            _data.TryGetValue(sectionName, out var section) && section.ContainsKey(keyName);

        protected override IEnumerable<string> GetSectionNamesImpl() => _data.Keys;

        protected override IEnumerable<string> GetSectionOptionNamesImpl(string sectionName) => _data[sectionName].Keys;

        protected override bool AddSectionImpl(string sectionName)
        {
            Section(sectionName);
            return true;
        }

        protected override bool RemoveSectionImpl(string sectionName) => _data.Remove(sectionName);

        protected override bool RemoveOptionImpl(string sectionName, string keyName) =>
            _data.TryGetValue(sectionName, out var section) && section.Remove(keyName);

        protected override void SetValueImpl<T>(string sectionName, string keyName, T value) =>
            Section(sectionName)[keyName] = value;

        protected override object GetValueImpl(Type typeObject, string sectionName, string keyName) =>
            _data[sectionName][keyName]!;

        protected override string GetRawValueImpl(string sectionName, string keyName) =>
            _data[sectionName][keyName]?.ToString() ?? string.Empty;

        protected override void SetRawValueImpl(string sectionName, string keyName, string rawValue) =>
            Section(sectionName)[keyName] = rawValue;
    }
}
