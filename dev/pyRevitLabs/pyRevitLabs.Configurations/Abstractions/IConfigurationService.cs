using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Abstractions;

/// <summary>
/// Typed access to a configuration: attribute-bound section records over one
/// backing store, cached until a write advances it.
/// </summary>
public interface IConfigurationService
{
    /// <summary>
    /// True when the service was built read-only. A write method throws
    /// rather than accepting an edit that could not be persisted.
    /// </summary>
    bool ReadOnly { get; }

    /// <summary>The backing configuration this service reads and writes.</summary>
    IConfiguration Configuration { get; }

    /// <summary>
    /// Snapshot of the <c>[core]</c> section. Rebuilt automatically after any
    /// write, so a reader never sees state older than the last change.
    /// </summary>
    CoreSection Core { get; }

    /// <summary>Snapshot of the <c>[routes]</c> section.</summary>
    RoutesSection Routes { get; }

    /// <summary>Snapshot of the <c>[telemetry]</c> section.</summary>
    TelemetrySection Telemetry { get; }

    /// <summary>Snapshot of the <c>[environment]</c> section.</summary>
    EnvironmentSection Environment { get; }

    /// <summary>
    /// Reads the settings for a single extension from its dynamic
    /// "{name}.extension" or "{name}.lib" section, or null when neither section is
    /// present. Section names are resolved without the type suffix (e.g. pass
    /// "pyRevitCore", not "pyRevitCore.extension").
    /// </summary>
    /// <exception cref="ArgumentException"><paramref name="extensionName"/> is null or whitespace.</exception>
    ExtensionSection? GetExtensionSection(string extensionName);

    /// <summary>
    /// Forces the typed section snapshots to be rebuilt on next access. Writes
    /// made through this service or its configuration are picked up on their
    /// own, so this is only needed when the configuration is replaced wholesale.
    /// </summary>
    void ReloadLoadConfigurations();

    /// <summary>
    /// Materializes a section record of type <typeparamref name="T"/> from the
    /// configuration, filling any absent key with the property's declared
    /// default.
    /// </summary>
    T GetSection<T>();

    /// <summary>
    /// Writes a section's non-null properties into the configuration and
    /// flushes to disk. Null properties are left untouched, so a sparsely
    /// populated record updates only the keys it sets; a property equal to its
    /// declared default is skipped unless the key is already stored.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="sectionValue"/> is null.</exception>
    /// <exception cref="Exceptions.ConfigurationReadOnlyException">The configuration is read-only.</exception>
    void SaveSection<T>(T sectionValue);

    /// <summary>
    /// Writes a section's non-null properties into the backing store using the
    /// same key-mapping and default-skip rules as <see cref="SaveSection{T}"/>,
    /// but does not flush to disk. Lets an in-process caller batch many edits
    /// behind a single <see cref="IConfiguration.SaveConfiguration()"/>. CLI-style
    /// callers that must persist per command should keep using SaveSection.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="sectionValue"/> is null.</exception>
    /// <exception cref="Exceptions.ConfigurationReadOnlyException">The configuration is read-only.</exception>
    void ApplySection<T>(T sectionValue);

    /// <summary>
    /// Writes a single key into an arbitrary section by name and flushes to disk.
    /// Use this for dynamic sections (per-extension, tab coloring) that no typed
    /// record covers.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="keyValue"/> is null.</exception>
    /// <exception cref="ArgumentException">A name argument is null or empty.</exception>
    /// <exception cref="Exceptions.ConfigurationReadOnlyException">The configuration is read-only.</exception>
    void SetSectionKeyValue<T>(string sectionName, string keyName, T keyValue);

    /// <summary>
    /// Reads a single key, returning <paramref name="defaultValue"/> when it is
    /// absent or unreadable.
    /// </summary>
    /// <exception cref="ArgumentException">A name argument is null or empty.</exception>
    T? GetSectionKeyValueOrDefault<T>(string sectionName, string keyName, T? defaultValue = default);
}
