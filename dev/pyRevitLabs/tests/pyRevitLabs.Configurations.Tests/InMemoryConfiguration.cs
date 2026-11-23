using System;
using System.Collections.Generic;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Tests;

/// <summary>
/// Minimal in-memory <see cref="IConfiguration"/> holding typed values, so the
/// section-materialization path can be exercised without the INI backend (and
/// its JSON round-trip, which is covered by the Ini tests).
/// </summary>
internal sealed class InMemoryConfiguration : ConfigurationBase {
    private readonly Dictionary<string, Dictionary<string, object?>> _data =
        new(StringComparer.OrdinalIgnoreCase);

    public InMemoryConfiguration() : base("memory", readOnly: false) { }

    private Dictionary<string, object?> Section(string sectionName) {
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

    protected override bool AddSectionImpl(string sectionName) {
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
