using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Abstractions;

/// <summary>
/// Typed access to one or more layered configurations. Named configurations are
/// layered so a per-Revit-version override resolves ahead of the default one;
/// the typed section properties read through that layering, while the write
/// methods target a single named configuration.
/// </summary>
public interface IConfigurationService
{
    /// <summary>
    /// True when the whole service was built read-only. A write method throws
    /// rather than accepting an edit that could not be persisted.
    /// </summary>
    bool ReadOnly { get; }

    /// <summary>Names of every configuration registered with this service.</summary>
    IEnumerable<string> ConfigurationNames { get; }

    /// <summary>
    /// The registered configurations, in the order they were added (the default
    /// configuration first, overrides after).
    /// </summary>
    IEnumerable<IConfiguration> Configurations { get; }

    /// <summary>Gets a registered configuration by name.</summary>
    /// <exception cref="ArgumentException"><paramref name="configurationName"/> is null or whitespace.</exception>
    /// <exception cref="InvalidOperationException">No configuration is registered under that name.</exception>
    IConfiguration this[string configurationName] { get; }

    /// <summary>
    /// Snapshot of the <c>[core]</c> section, resolved across all layers.
    /// Rebuilt automatically after any write, so a reader never sees state older
    /// than the last change.
    /// </summary>
    CoreSection Core { get; }

    /// <summary>Snapshot of the <c>[routes]</c> section, resolved across all layers.</summary>
    RoutesSection Routes { get; }

    /// <summary>Snapshot of the <c>[telemetry]</c> section, resolved across all layers.</summary>
    TelemetrySection Telemetry { get; }

    /// <summary>Snapshot of the <c>[environment]</c> section, resolved across all layers.</summary>
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
    /// made through this service or its configurations are picked up on their
    /// own, so this is only needed when a configuration is replaced wholesale.
    /// </summary>
    void ReloadLoadConfigurations();

    /// <summary>
    /// Materializes a section record of type <typeparamref name="T"/> from the
    /// layered configurations, filling any key absent from every layer with the
    /// property's declared default.
    /// </summary>
    T GetSection<T>();

    /// <summary>
    /// Writes a section's non-null properties into the named configuration and
    /// flushes to disk. Null properties are left untouched, so a sparsely
    /// populated record updates only the keys it sets; a property equal to its
    /// declared default is skipped unless the key is already stored.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="sectionValue"/> is null.</exception>
    /// <exception cref="ArgumentException">The configuration name is null, whitespace, or not registered.</exception>
    /// <exception cref="Exceptions.ConfigurationException">The target configuration is read-only.</exception>
    void SaveSection<T>(string configurationName, T sectionValue);

    /// <summary>
    /// Writes a section's non-null properties into the backing store using the
    /// same key-mapping and default-skip rules as <see cref="SaveSection{T}"/>,
    /// but does not flush to disk. Lets an in-process caller batch many edits
    /// behind a single <see cref="IConfiguration.SaveConfiguration()"/>. CLI-style
    /// callers that must persist per command should keep using SaveSection.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="sectionValue"/> is null.</exception>
    /// <exception cref="ArgumentException">The configuration name is null, whitespace, or not registered.</exception>
    /// <exception cref="Exceptions.ConfigurationException">The target configuration is read-only.</exception>
    void ApplySection<T>(string configurationName, T sectionValue);

    /// <summary>
    /// Writes a single key into an arbitrary section by name and flushes to disk.
    /// Use this for dynamic sections (per-extension, tab coloring) that no typed
    /// record covers.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="keyValue"/> is null.</exception>
    /// <exception cref="ArgumentException">A name argument is null or empty, or the configuration is not registered.</exception>
    /// <exception cref="Exceptions.ConfigurationException">The target configuration is read-only.</exception>
    void SetSectionKeyValue<T>(string configurationName, string sectionName, string keyName, T keyValue);

    /// <summary>
    /// Reads a single key from one named configuration, without layering,
    /// returning <paramref name="defaultValue"/> when it is absent or unreadable.
    /// </summary>
    /// <exception cref="ArgumentException">A name argument is null or empty, or the configuration is not registered.</exception>
    T? GetSectionKeyValueOrDefault<T>(string configurationName, string sectionName, string keyName, T? defaultValue = default);
}
