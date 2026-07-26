using System.Collections.Specialized;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Assembles an <see cref="IConfigurationService"/> from one or more named
/// configurations. Sources are layered in the order they are added, so add the
/// default configuration first and any override after it.
/// </summary>
public sealed class ConfigurationBuilder
{
    private readonly bool _readOnly;
    private readonly List<ConfigurationName> _names = [];
    private readonly Dictionary<string, IConfiguration> _configurations = [];

    /// <summary>
    /// Starts a new builder.
    /// </summary>
    /// <param name="readOnly">
    /// True to make the built service refuse every write, regardless of whether
    /// the individual configurations are themselves writable.
    /// </param>
    public ConfigurationBuilder(bool readOnly)
    {
        _readOnly = readOnly;
    }

    /// <summary>
    /// Registers a configuration under a name and returns this builder for
    /// chaining.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="configuration"/> is null.</exception>
    /// <exception cref="ArgumentException"><paramref name="configurationName"/> is null or whitespace.</exception>
    /// <exception cref="ArgumentException">A configuration is already registered under that name.</exception>
    public ConfigurationBuilder AddConfigurationSource(string configurationName, IConfiguration configuration)
    {
        if (configuration == null)
            throw new ArgumentNullException(nameof(configuration));

        if (string.IsNullOrWhiteSpace(configurationName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(configurationName));

        _names.Add(new ConfigurationName() {Index = _configurations.Count, Name = configurationName});
        _configurations.Add(configurationName, configuration);

        return this;
    }

    /// <summary>
    /// Creates the service over the registered configurations. The builder can
    /// be reused, but the returned service does not observe later additions.
    /// </summary>
    public IConfigurationService Build()
    {
        return ConfigurationService.Create(_readOnly, _names, _configurations);
    }
}
